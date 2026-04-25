#!/usr/bin/env python
from pathlib import Path
from typing import Any, Dict, Optional
import json
import sys

from crewai.flow.flow import Flow, start, listen


class SimpleFlow(Flow):
    @start()
    def plan_content(self, crewai_trigger_payload: Optional[Dict[str, Any]] = None):
        """
        Entry point for the flow.
        CopilotKit Cloud / CrewAI deployment can pass payloads with keys like:
        - topic
        - message
        - input
        - query
        """
        topic = "Hello from CrewAI"

        # When called locally via kickoff(inputs={...}), the platform does not
        # pass inputs as method kwargs — they land in self.state instead.
        if crewai_trigger_payload is None and isinstance(self.state, dict):
            crewai_trigger_payload = self.state.get("crewai_trigger_payload")

        if crewai_trigger_payload is not None:
            if isinstance(crewai_trigger_payload, dict):
                topic = (
                    crewai_trigger_payload.get("topic")
                    or crewai_trigger_payload.get("message")
                    or crewai_trigger_payload.get("input")
                    or crewai_trigger_payload.get("query")
                    or str(crewai_trigger_payload)
                )
            else:
                topic = str(crewai_trigger_payload)

        self.state["topic"] = topic
        return topic

    @listen(plan_content)
    def generate_content(self, topic: str):
        """
        Generate the final response content for the agent.
        """
        from copilotkit_crewai_test.crews.content_crew.content_crew import ContentCrew

        result = ContentCrew().crew().kickoff(inputs={"topic": topic})
        final_post = result.raw
        self.state["final_post"] = final_post
        return final_post

    @listen(generate_content)
    def save_content(self, final_post: str):
        """
        Persist a copy locally for debugging / verification.
        """
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        out_file = output_dir / "post.md"
        out_file.write_text(final_post, encoding="utf-8")

        return final_post


def kickoff():
    """
    Local manual test without trigger payload.
    """
    result = SimpleFlow().kickoff()
    print(result)
    return result


def plot():
    return SimpleFlow().plot()


def run_with_trigger():
    """
    Local manual test with JSON trigger payload passed as argv[1].
    Example:
      python main.py '{"message":"hello"}'
    """
    if len(sys.argv) < 2:
        raise Exception(
            "No trigger payload provided. Please provide JSON payload as argument."
        )

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        raise Exception("Invalid JSON payload provided as argument") from e

    result = SimpleFlow().kickoff(
        inputs={"crewai_trigger_payload": trigger_payload}
    )
    print(result)
    return result


if __name__ == "__main__":
    # Supports both local plain testing and local trigger-based testing
    if len(sys.argv) > 1:
        run_with_trigger()
    else:
        kickoff()