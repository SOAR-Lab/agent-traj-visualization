"""Normalizer prototype for AXE JSONL traces."""

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_DATA_DIR = PROJECT_ROOT / "data" / "json"
INPUT_FILE = (
    PROJECT_ROOT
    / "AXE_logs"
    / "trace_CVE-2024-2359-gpt-4o-l6e15e15"
    / "trace_CVE-2024-2359-gpt-4o-l6e15e15.jsonl"
)

OUTPUT_NORMALIZED = JSON_DATA_DIR / "normalized_trace.json"
OUTPUT_GRAPH = JSON_DATA_DIR / "graph_trace.json"
OUTPUT_FILE_CONTEXT = JSON_DATA_DIR / "file_context.json"

# DATA MODEL
@dataclass
class NormalizedStep:
    id: int
    ts: float
    node: str
    kind: str

    step_type: str   # THINK or ACT

    success: Optional[bool] = None

    decision: Optional[str] = None
    thought: Optional[List[str]] = None

    file_read: Optional[str] = None

    tool_name: Optional[str] = None
    tool_input: Optional[Any] = None
    tool_output: Optional[Any] = None

    error: Optional[str] = None

    raw: Optional[Dict] = None


# FILE LOADING
def load_jsonl(path):

    with open(path, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            yield json.loads(line)


# HELPERS
def step_type_from_kind(kind):

    if kind == "completion":
        return "THINK"

    elif kind == "exec":
        return "ACT"

    return "OTHER"


def to_string_list(x):

    if x is None:
        return None

    if isinstance(x, str):
        return [x]

    if isinstance(x, list):
        return [str(i) for i in x]

    return [str(x)]


def detect_error(outputs):

    if isinstance(outputs, dict):

        for key in ["error", "exception", "traceback", "stderr"]:

            if key in outputs and outputs[key]:
                return str(outputs[key])

    return None


def detect_success(outputs):

    err = detect_error(outputs)

    if err:
        return False

    if isinstance(outputs, dict):

        if "status" in outputs and isinstance(outputs["status"], bool):
            return outputs["status"]

    return True


def extract_tool_name(inputs, outputs):

    if isinstance(inputs, dict):

        for key in ["tool", "tool_name", "command", "action", "endpoint"]:

            if key in inputs and inputs[key]:
                return str(inputs[key])

    if isinstance(outputs, dict):

        for key in ["tool", "tool_name", "command", "action", "endpoint"]:

            if key in outputs and outputs[key]:
                return str(outputs[key])

    return None


# FILE READ EXTRACTION
FILE_PATTERN = re.compile(
    r"[a-zA-Z0-9_\-/]+\.(py|js|ts|java|cpp|c|txt|json|yaml|yml)"
)

def extract_file_read(inputs, outputs):

    # Check structured fields first
    if isinstance(inputs, dict):
        for key in ["file", "path", "filepath", "filename", "target_component"]:
            if key in inputs and inputs[key]:
                return str(inputs[key])

    if isinstance(outputs, dict):
        for key in ["file", "path", "filepath", "filename", "target_component"]:
            if key in outputs and outputs[key]:
                return str(outputs[key])

    # Check exploration requests

    if isinstance(outputs, dict):
        if "exploration_requests" in outputs:
            reqs = outputs["exploration_requests"]
            if isinstance(reqs, list) and len(reqs) > 0:
                req = reqs[0]

                if isinstance(req, dict):
                    if "target_component" in req:
                        return str(req["target_component"])

    # Regex search fallback

    for blob in [inputs, outputs]:
        if isinstance(blob, str):
            match = FILE_PATTERN.search(blob)
            if match:
                return match.group()

    return None


# NORMALIZATION
def normalize_entry(entry, idx):

    ts = entry.get("ts", idx)

    node = entry.get("node", "unknown")

    kind = entry.get("kind", "unknown")

    inputs = entry.get("inputs")

    outputs = entry.get("outputs")

    step_type = step_type_from_kind(kind)

    success = detect_success(outputs)

    error = detect_error(outputs)

    decision = None
    thought = None

    tool_name = None
    tool_input = inputs
    tool_output = outputs

    file_read = None

    # THINK step
    if kind == "completion":
        if isinstance(outputs, dict):
            decision = outputs.get("decision")
            thought = to_string_list(outputs.get("thought"))
            file_read = extract_file_read(inputs, outputs)

    # ACT step
    elif kind == "exec":
        tool_name = extract_tool_name(inputs, outputs)
        file_read = extract_file_read(inputs, outputs)

    step = NormalizedStep(
        id=idx,
        ts=float(ts),
        node=str(node),
        kind=str(kind),
        step_type=step_type,
        success=success,
        decision=decision,
        thought=thought,
        file_read=file_read,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        error=error,
        raw=entry
    )

    return step


# BUILD FILE CONTEXT TIMELINE
def build_file_context(steps):

    seen_files: Set[str] = set()

    context = []

    for step in steps:
        if step.file_read:
            seen_files.add(step.file_read)

        context.append({
            "step_id": step.id,
            "file_read": step.file_read,
            "files_seen_so_far": list(sorted(seen_files))
        })

    return context


# BUILD GRAPH
def build_graph(steps):

    nodes = []
    edges = []

    for step in steps:

        nodes.append({
            "id": str(step.id),
            "label": f"{step.node} • {step.step_type}",
            "timestamp": step.ts,
            "node": step.node,
            "kind": step.kind,
            "step_type": step.step_type,
            "success": step.success,
            "decision": step.decision,
            "thought": step.thought,
            "file_read": step.file_read,
            "tool": step.tool_name,
            "error": step.error
        })

    for i in range(1, len(steps)):
        edges.append({
            "source": str(steps[i-1].id),
            "target": str(steps[i].id),
            "type": "sequence",
            "success": steps[i].success
        })

    return {
        "nodes": nodes,
        "edges": edges
    }


# MAIN
def main():
    JSON_DATA_DIR.mkdir(parents=True, exist_ok=True)
    steps = []

    for idx, entry in enumerate(load_jsonl(INPUT_FILE)):

        step = normalize_entry(entry, idx)

        steps.append(step)

    print(f"Total steps: {len(steps)}")

    # Sort by timestamp
    steps.sort(key=lambda s: s.ts)

    # Reassign IDs
    for i, step in enumerate(steps):
        step.id = i

    with open(OUTPUT_NORMALIZED, "w", encoding="utf-8") as f:

        json.dump(

            [asdict(step) for step in steps],

            f,

            indent=2

        )

    graph = build_graph(steps)

    with open(OUTPUT_GRAPH, "w", encoding="utf-8") as f:

        json.dump(graph, f, indent=2)

    file_context = build_file_context(steps)

    with open(OUTPUT_FILE_CONTEXT, "w", encoding="utf-8") as f:

        json.dump(file_context, f, indent=2)

    print("Created files:")

    print(OUTPUT_NORMALIZED)
    print(OUTPUT_GRAPH)
    print(OUTPUT_FILE_CONTEXT)


if __name__ == "__main__":

    main()
