#!/usr/bin/env python
import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ag_ui.core import (
    RunAgentInput,
    RunStartedEvent,
    RunFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    EventType,
)
from ag_ui.encoder import EventEncoder

from copilotkit_crewai_test.main import SimpleFlow

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/agent")
async def agent_endpoint(input_data: RunAgentInput):
    async def event_generator():
        encoder = EventEncoder()

        # Extract user message from the last user turn
        user_message = ""
        for msg in reversed(input_data.messages):
            if msg.role == "user":
                content = msg.content
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            user_message = part["text"]
                            break
                elif isinstance(content, str):
                    user_message = content
                break

        yield encoder.encode(
            RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )
        )

        message_id = str(uuid.uuid4())

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: SimpleFlow().kickoff(
                    inputs={"crewai_trigger_payload": {"message": user_message}}
                ),
            )
            final_text = str(result) if result else "I received your message but produced no output."

            yield encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=message_id,
                    role="assistant",
                )
            )

            chunk_size = 50
            for i in range(0, len(final_text), chunk_size):
                yield encoder.encode(
                    TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=message_id,
                        delta=final_text[i : i + chunk_size],
                    )
                )
                await asyncio.sleep(0.01)

            yield encoder.encode(
                TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=message_id,
                )
            )

        except Exception as exc:
            error_text = f"Error running flow: {exc}"
            yield encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=message_id,
                    role="assistant",
                )
            )
            yield encoder.encode(
                TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=error_text,
                )
            )
            yield encoder.encode(
                TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=message_id,
                )
            )

        # RunFinished MUST always be emitted — its absence is what causes
        # "finish/completion event not received" on the frontend.
        yield encoder.encode(
            RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("copilotkit_crewai_test.api:app", host="0.0.0.0", port=8000, reload=True)
