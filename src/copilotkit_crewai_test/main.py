#!/usr/bin/env python
from pathlib import Path
import json
import sys

from crewai.flow.flow import Flow, start, listen


class SimpleFlow(Flow):
    @start()
    def plan_content(self, crewai_trigger_payload: dict = None):
        if crewai_trigger_payload:
            self.state["topic"] = crewai_trigger_payload.get("topic", "Hello from CrewAI")
        else:
            self.state["topic"] = "Hello from CrewAI"

        return self.state["topic"]

    @listen(plan_content)
    def generate_content(self, topic):
        self.state["final_post"] = f"# Test Output\n\nTopic received: {topic}\n"
        return self.state["final_post"]

    @listen(generate_content)
    def save_content(self, final_post):
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        out_file = output_dir / "post.md"
        out_file.write_text(final_post)
        print(f"Wrote: {out_file.resolve()}")
        return final_post


def kickoff():
    result = SimpleFlow().kickoff()
    print(result)
    return result


def plot():
    return SimpleFlow().plot()


def run_with_trigger():
    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    result = SimpleFlow().kickoff({"crewai_trigger_payload": trigger_payload})
    print(result)
    return result


if __name__ == "__main__":
    kickoff()