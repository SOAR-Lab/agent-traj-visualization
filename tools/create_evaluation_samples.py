"""Create short TraceView evaluation samples from local SWE-agent trajectories."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

SOURCE_DIR = Path("sweagent_claude4_trajs")
OUTPUT_DIR = Path("evaluation_samples")
WINDOW_SIZE = 8
WINDOW_STEP = 2
MAX_SAMPLES = 5
MAX_TEXT_CHARS = 3500

EDIT_RE = re.compile(
    r"\b(str_replace|create|insert|apply_patch|write|edit)\b",
    re.IGNORECASE,
)
VIEW_RE = re.compile(r"\b(view|grep|find|ls|search|sed|cat)\b", re.IGNORECASE)
TEST_RE = re.compile(
    r"\b(pytest|unittest|tox|mypy|ruff|flake8)\b"
    r"|manage\.py\s+test\b"
    r"|python(?:3)?\s+(?:-m\s+pytest|[^\n]*(?:test|reproduce)[^\n]*\.py)",
    re.IGNORECASE,
)
FAIL_RE = re.compile(
    r"\b(traceback|assertionerror|failed|failure|error|exception|importerror)\b",
    re.IGNORECASE,
)
PATH_RE = re.compile(
    r"(?<![\w./-])(?:[A-Za-z0-9_.-]+[/\\])+[A-Za-z0-9_.-]+\.[A-Za-z0-9_]+"
)


@dataclass(frozen=True)
class CandidateWindow:
    task_id: str
    source_path: Path
    start: int
    end: int
    score: int
    kind: str
    edits: int
    tests: int
    failures: int
    exploration: int
    files: int
    action_variety: int


def _load_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _task_id(path: Path, data: dict) -> str:
    instance_id = data.get("instance_id")
    if isinstance(instance_id, str) and instance_id.strip():
        return instance_id.strip()
    return path.stem


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _truncate(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    if len(normalized) <= MAX_TEXT_CHARS:
        return normalized
    return (
        normalized[:MAX_TEXT_CHARS].rstrip()
        + "\n\n[... truncated for evaluation sample ...]"
    )


def _action_token(action: str) -> str:
    normalized = action.strip().split()
    if not normalized:
        return ""
    if normalized[0] == "str_replace_editor" and len(normalized) > 1:
        return f"{normalized[0]} {normalized[1]}"
    return normalized[0]


def _classify_window(
    *,
    task_id: str,
    source_path: Path,
    steps: list[dict],
    start: int,
    end: int,
) -> CandidateWindow:
    window = steps[start:end]
    actions = [_text(step.get("action")) for step in window]
    observations = [
        _text(step.get("observation") or step.get("result"))
        for step in window
    ]
    combined_actions = "\n".join(actions)
    combined_observations = "\n".join(observations)
    combined_text = f"{combined_actions}\n{combined_observations}"

    edits = sum(
        1
        for action in actions
        if EDIT_RE.search(action) and " view " not in f" {action.lower()} "
    )
    tests = sum(1 for action in actions if TEST_RE.search(action))
    failures = sum(1 for observation in observations if FAIL_RE.search(observation))
    exploration = sum(1 for action in actions if VIEW_RE.search(action))
    files = len(set(PATH_RE.findall(combined_text)))
    action_variety = len({_action_token(action) for action in actions if action.strip()})

    score = (
        edits * 8
        + tests * 7
        + failures * 5
        + min(exploration, 6) * 2
        + min(files, 8)
        + action_variety * 2
    )

    if exploration >= 4 and not edits and not tests and failures <= 2:
        kind = "localization"
    elif edits and tests and failures:
        kind = "failure-recovery"
    elif edits and tests:
        kind = "fix-and-test"
    elif edits:
        kind = "fix"
    else:
        kind = "mixed"

    return CandidateWindow(
        task_id=task_id,
        source_path=source_path,
        start=start,
        end=end,
        score=score,
        kind=kind,
        edits=edits,
        tests=tests,
        failures=failures,
        exploration=exploration,
        files=files,
        action_variety=action_variety,
    )


def _candidate_windows() -> list[CandidateWindow]:
    candidates: list[CandidateWindow] = []
    for path in sorted(SOURCE_DIR.rglob("*.traj")):
        data = _load_json(path)
        if not data:
            continue
        steps = data.get("trajectory")
        if not isinstance(steps, list) or len(steps) < 12:
            continue

        task_id = _task_id(path, data)
        window_size = min(WINDOW_SIZE, len(steps))
        starts = list(range(0, max(len(steps) - window_size + 1, 1), WINDOW_STEP))
        final_start = max(len(steps) - window_size, 0)
        if final_start not in starts:
            starts.append(final_start)

        for start in starts:
            candidates.append(
                _classify_window(
                    task_id=task_id,
                    source_path=path,
                    steps=steps,
                    start=start,
                    end=start + window_size,
                )
            )
    return candidates


def _choose_windows(candidates: list[CandidateWindow]) -> list[CandidateWindow]:
    preferred_kinds = [
        "localization",
        "fix-and-test",
        "failure-recovery",
        "fix",
        "mixed",
    ]
    selected: list[CandidateWindow] = []
    used_tasks: set[str] = set()

    for kind in preferred_kinds:
        kind_candidates = sorted(
            [candidate for candidate in candidates if candidate.kind == kind],
            key=lambda candidate: candidate.score,
            reverse=True,
        )
        for candidate in kind_candidates:
            if candidate.task_id in used_tasks:
                continue
            selected.append(candidate)
            used_tasks.add(candidate.task_id)
            break

    for candidate in sorted(candidates, key=lambda item: item.score, reverse=True):
        if len(selected) >= MAX_SAMPLES:
            break
        if candidate.task_id in used_tasks:
            continue
        selected.append(candidate)
        used_tasks.add(candidate.task_id)

    return selected[:MAX_SAMPLES]


def _sample_step(raw_step: dict, original_index: int) -> dict:
    return {
        "thought": _truncate(_text(raw_step.get("thought") or raw_step.get("response"))),
        "response": _truncate(_text(raw_step.get("response") or raw_step.get("thought"))),
        "action": _truncate(_text(raw_step.get("action"))),
        "observation": _truncate(_text(raw_step.get("observation") or raw_step.get("result"))),
        "extra_info": {
            "original_step_index": original_index,
        },
    }


def _write_sample(index: int, candidate: CandidateWindow) -> dict[str, object]:
    data = _load_json(candidate.source_path)
    if not data:
        raise ValueError(f"Could not read {candidate.source_path}")
    steps = data["trajectory"][candidate.start:candidate.end]
    sample_id = f"{candidate.task_id}__eval_{index:02d}_{candidate.kind}"
    output_path = OUTPUT_DIR / f"{sample_id}.traj"

    sample = {
        "instance_id": sample_id,
        "sample_metadata": {
            "source_task_id": candidate.task_id,
            "source_path": str(candidate.source_path).replace("\\", "/"),
            "original_start_step": candidate.start,
            "original_end_step_exclusive": candidate.end,
            "selection_kind": candidate.kind,
            "selection_score": candidate.score,
            "signals": {
                "edits": candidate.edits,
                "tests": candidate.tests,
                "failures": candidate.failures,
                "exploration": candidate.exploration,
                "files": candidate.files,
                "action_variety": candidate.action_variety,
            },
            "note": f"{WINDOW_SIZE}-step evaluation fixture generated from a local SWE-agent trajectory.",
        },
        "trajectory": [
            _sample_step(step, original_index)
            for original_index, step in enumerate(
                data["trajectory"][candidate.start:candidate.end],
                start=candidate.start,
            )
        ],
    }

    output_path.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "sample": output_path.name,
        "kind": candidate.kind,
        "source_task_id": candidate.task_id,
        "source_path": str(candidate.source_path).replace("\\", "/"),
        "original_steps": f"{candidate.start}-{candidate.end - 1}",
        "step_count": len(steps),
        "score": candidate.score,
        "signals": {
            "edits": candidate.edits,
            "tests": candidate.tests,
            "failures": candidate.failures,
            "exploration": candidate.exploration,
            "files": candidate.files,
            "action_variety": candidate.action_variety,
        },
    }


def _write_manifest(rows: list[dict[str, object]]) -> None:
    lines = [
        "# Evaluation Samples",
        "",
        f"These `.traj` files are {WINDOW_SIZE}-step SWE-agent trajectory windows selected for TraceView evaluation.",
        "They are meant to keep labeling work reasonable while preserving realistic trajectory structure.",
        "",
        "Selection signals are heuristic counts over each sampled window.",
        "",
        "| Sample | Kind | Source task | Original steps | Signals |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        signals = row["signals"]
        signal_text = ", ".join(
            f"{key}: {value}"
            for key, value in signals.items()
        )
        lines.append(
            "| {sample} | {kind} | {source_task_id} | {original_steps} | {signals} |".format(
                sample=row["sample"],
                kind=row["kind"],
                source_task_id=row["source_task_id"],
                original_steps=row["original_steps"],
                signals=signal_text,
            )
        )

    lines.extend(
        [
            "",
            "Use these files from the TraceView `Labeling` page by uploading one `.traj` file.",
            "The original SWE-agent step index is preserved in each step's `extra_info.original_step_index`.",
        ]
    )
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not SOURCE_DIR.exists():
        raise SystemExit(f"Source directory not found: {SOURCE_DIR}")
    OUTPUT_DIR.mkdir(exist_ok=True)

    for existing in OUTPUT_DIR.glob("*.traj"):
        existing.unlink()

    candidates = _candidate_windows()
    selected = _choose_windows(candidates)
    rows = [_write_sample(index, candidate) for index, candidate in enumerate(selected, start=1)]
    _write_manifest(rows)

    print(f"Wrote {len(rows)} samples to {OUTPUT_DIR}")
    for row in rows:
        print(
            f"- {row['sample']}: {row['kind']} from {row['source_task_id']} "
            f"steps {row['original_steps']}"
        )


if __name__ == "__main__":
    main()
