"""Quick AXE log probe used during initial schema discovery."""

import json
from pathlib import Path

import jsonlines

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = (
    PROJECT_ROOT
    / "AXE_logs"
    / "trace_CVE-2024-2359-gpt-4o-l6e15e15"
    / "trace_CVE-2024-2359-gpt-4o-l6e15e15.jsonl"
)

with jsonlines.open(INPUT_PATH) as reader:
    for obj in reader:
        print(obj.keys())

