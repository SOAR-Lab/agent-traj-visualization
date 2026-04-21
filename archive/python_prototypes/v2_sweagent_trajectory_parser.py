"""Second parser prototype for building agraph timelines from trajectories."""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_DATA_DIR = PROJECT_ROOT / "data" / "json"
INPUT_PATH = (
    PROJECT_ROOT
    / "sweagent_claude4_trajs"
    / "astropy__astropy-6938"
    / "astropy__astropy-6938.traj"
)
OUTPUT_PATH = JSON_DATA_DIR / "agraph_graph.json"

ERROR_PATTERNS = [
    r"Traceback",
    r"\bException\b",
    r"\bError\b",
    r"\bFAILED\b",
    r"\bAssertionError\b",
]

FILE_REGEX = re.compile(r"(/[A-Za-z0-9_\-./]+\.[A-Za-z0-9]+)")

def is_failure(text):
    if not text:
        return False
    text = str(text)
    for p in ERROR_PATTERNS:
        if re.search(p, text):
            return True
    return False

def shorten(text, n=80):
    if not text:
        return ""
    text = str(text).replace("\r\n", "\n").strip()
    return text[:n] + "..." if len(text) > n else text

def parse_trajectory(data):

    nodes = []
    edges = []

    trajectory = data["trajectory"]

    previous_result_id = None

    for i, step in enumerate(trajectory):

        thought = step.get("thought") or step.get("response")
        action = step.get("action")
        observation = step.get("observation")

        failure = is_failure(observation)
        success = not failure

        tid = f"t{i}"
        aid = f"a{i}"
        rid = f"r{i}"

        # THOUGHT NODE
        nodes.append({
            "id": tid,
            "label": shorten(thought),
            "full_text": thought,
            "type": "thought",
            "step_index": i
        })

        # ACTION NODE
        nodes.append({
            "id": aid,
            "label": shorten(action),
            "full_text": action,
            "type": "action",
            "step_index": i
        })

        # RESULT NODE
        nodes.append({
            "id": rid,
            "label": shorten(observation),
            "full_text": observation,
            "type": "result",
            "success": success,
            "step_index": i
        })

        # Internal edges
        edges.append({"source": tid, "target": aid})
        edges.append({"source": aid, "target": rid, "success": success})

        # Cross-step edge
        if previous_result_id:
            edges.append({"source": previous_result_id, "target": tid})

        previous_result_id = rid

    return {"nodes": nodes, "edges": edges}


def main():
    JSON_DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

    graph = parse_trajectory(data)

    OUTPUT_PATH.write_text(
        json.dumps(graph, indent=2),
        encoding="utf-8"
    )

    print(f"Saved {OUTPUT_PATH}")
    print("Nodes:", len(graph["nodes"]))
    print("Edges:", len(graph["edges"]))


if __name__ == "__main__":
    main()
