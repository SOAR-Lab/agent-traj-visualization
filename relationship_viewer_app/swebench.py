"""SWE-agent trajectory parsing and relationship-label export helpers."""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Iterable

from relationship_viewer_app.constants import (
    PROJECT_ROOT,
    REL_LABEL_COL,
    REL_SPECS,
    RELATION_LABEL_OPTIONS,
    RELATION_LABEL_OPTIONS_BY_FAMILY,
)
from relationship_viewer_app.models import ParsedTrajectory, RelationCandidate, TrajectoryStep
from relationship_viewer_app.node_ids import (
    ACTION_NODE_KIND,
    RESULT_NODE_KIND,
    THOUGHT_NODE_KIND,
    node_kind_name,
    step_node_id,
)

UNLABELED_RELATION_LABEL = "Unlabeled"
LOCAL_SWEAGENT_TRAJECTORY_DIR = PROJECT_ROOT / "sweagent_claude4_trajs"
SUPPORTED_TRAJECTORY_SUFFIXES = {".traj", ".json", ".jsonl", ".log", ".txt"}


def coerce_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, indent=2).strip()


def coerce_field_text(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(coerce_text(item) for item in value if item not in (None, "", []))
    return coerce_text(value)


def short_preview(value: str, limit: int = 140) -> str:
    normalized = " ".join(coerce_text(value).split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def parse_sweagent_trajectory_payload(data: dict, source_name: str) -> ParsedTrajectory:
    trajectory = data.get("trajectory")
    if not isinstance(trajectory, list):
        raise ValueError(f"{source_name} does not contain a list field named 'trajectory'.")

    path_stem = Path(source_name).stem
    task_id = coerce_text(data.get("instance_id")) or path_stem
    steps: list[TrajectoryStep] = []

    for index, raw_step in enumerate(trajectory):
        if not isinstance(raw_step, dict):
            continue
        thought = raw_step.get("thought") or raw_step.get("response")
        result = raw_step.get("observation") or raw_step.get("result")
        steps.append(
            TrajectoryStep(
                step_index=index,
                thought=coerce_text(thought),
                action=coerce_text(raw_step.get("action")),
                result=coerce_text(result),
            )
        )

    if not steps:
        raise ValueError(f"{source_name} does not contain any parseable trajectory steps.")

    return ParsedTrajectory(
        task_id=task_id,
        source_name=source_name.replace("\\", "/"),
        steps=tuple(steps),
    )


def parse_sweagent_trajectory_bytes(contents: bytes, source_name: str) -> ParsedTrajectory:
    try:
        data = json.loads(contents.decode("utf-8"))
    except UnicodeDecodeError:
        data = json.loads(contents.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source_name} is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{source_name} must contain a JSON object.")
    return parse_sweagent_trajectory_payload(data, source_name)


def _text_from_preferred_fields(
    value: object,
    keys: tuple[str, ...],
    *,
    fallback: bool = True,
) -> str:
    if isinstance(value, dict):
        parts = [
            coerce_field_text(value.get(key))
            for key in keys
            if value.get(key) not in (None, "", [])
        ]
        if parts:
            return "\n".join(parts)
        if not fallback:
            return ""
    return coerce_text(value)


def parse_jsonl_trace_bytes(contents: bytes, source_name: str) -> ParsedTrajectory:
    text = contents.decode("utf-8", errors="replace")
    entries: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source_name}:{line_number} is not valid JSONL: {exc}") from exc
        if isinstance(entry, dict):
            entries.append(entry)

    if not entries:
        raise ValueError(f"{source_name} does not contain any JSONL trace entries.")

    pending_thoughts: list[str] = []
    steps: list[TrajectoryStep] = []

    for entry in entries:
        kind = coerce_text(entry.get("kind")).lower()
        inputs = entry.get("inputs")
        outputs = entry.get("outputs")

        if kind == "completion":
            thought = _text_from_preferred_fields(
                outputs,
                ("thought", "summary", "decision", "message", "content"),
            )
            if not thought:
                thought = _text_from_preferred_fields(
                    inputs,
                    ("messages", "prompt", "command", "original_command"),
                )
            if thought:
                pending_thoughts.append(thought)
            continue

        if kind == "exec":
            action = _text_from_preferred_fields(
                outputs,
                ("effective_command", "command", "original_command", "actions"),
                fallback=False,
            )
            if not action:
                action = _text_from_preferred_fields(
                    inputs,
                    ("command", "original_command", "tool", "action"),
                )
            result = _text_from_preferred_fields(
                outputs,
                ("summary", "stdout", "stderr", "error", "exit_code", "done"),
            )
            steps.append(
                TrajectoryStep(
                    step_index=len(steps),
                    thought="\n\n".join(pending_thoughts),
                    action=action,
                    result=result,
                )
            )
            pending_thoughts = []

    if not steps and pending_thoughts:
        for thought in pending_thoughts:
            steps.append(
                TrajectoryStep(
                    step_index=len(steps),
                    thought=thought,
                    action="",
                    result="",
                )
            )

    if not steps:
        raise ValueError(f"{source_name} does not contain any parseable trace steps.")

    return ParsedTrajectory(
        task_id=Path(source_name).stem,
        source_name=source_name.replace("\\", "/"),
        steps=tuple(steps),
    )


def parse_text_trace_bytes(contents: bytes, source_name: str) -> ParsedTrajectory:
    text = contents.decode("utf-8", errors="replace").replace("\r\n", "\n")
    parts = re.split(r"\b(?:Iteration|Step)\s+(\d+)\b", text, flags=re.IGNORECASE)
    steps: list[TrajectoryStep] = []

    def extract_section(chunk: str, name_pattern: str, next_patterns: tuple[str, ...]) -> str:
        match = re.search(
            rf"(?:{name_pattern}):\s*(.*)",
            chunk,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return ""
        remaining = match.group(1)
        cut_positions = []
        for next_pattern in next_patterns:
            next_match = re.search(
                rf"\n\s*{next_pattern}:\s*",
                remaining,
                flags=re.IGNORECASE,
            )
            if next_match:
                cut_positions.append(next_match.start())
        if cut_positions:
            remaining = remaining[: min(cut_positions)]
        lines = remaining.splitlines()
        while lines and (not lines[-1].strip() or re.fullmatch(r"\s*[-=_]{3,}\s*", lines[-1])):
            lines.pop()
        return "\n".join(lines).strip()

    if len(parts) >= 3:
        for index in range(1, len(parts) - 1, 2):
            chunk = parts[index + 1]
            thought = extract_section(chunk, "Thought", ("Action", "Result|Observation"))
            action = extract_section(chunk, "Action", ("Result|Observation", "Thought"))
            result = extract_section(chunk, "Result|Observation", ("Thought", "Action"))
            if thought or action or result:
                steps.append(
                    TrajectoryStep(
                        step_index=len(steps),
                        thought=thought,
                        action=action,
                        result=result,
                    )
                )
    else:
        thought = extract_section(text, "Thought", ("Action", "Result|Observation"))
        action = extract_section(text, "Action", ("Result|Observation", "Thought"))
        result = extract_section(text, "Result|Observation", ("Thought", "Action"))
        if thought or action or result:
            steps.append(
                TrajectoryStep(
                    step_index=0,
                    thought=thought,
                    action=action,
                    result=result,
                )
            )
        elif text.strip():
            steps.append(
                TrajectoryStep(
                    step_index=0,
                    thought=text.strip(),
                    action="",
                    result="",
                )
            )

    if not steps:
        raise ValueError(f"{source_name} does not contain any parseable trace steps.")

    return ParsedTrajectory(
        task_id=Path(source_name).stem,
        source_name=source_name.replace("\\", "/"),
        steps=tuple(steps),
    )


def parse_trajectory_bytes(contents: bytes, source_name: str) -> ParsedTrajectory:
    suffix = Path(source_name).suffix.lower()
    if suffix == ".jsonl":
        return parse_jsonl_trace_bytes(contents, source_name)
    if suffix in {".log", ".txt"}:
        return parse_text_trace_bytes(contents, source_name)
    return parse_sweagent_trajectory_bytes(contents, source_name)


def parse_trajectory_sources(
    sources: Iterable[tuple[str, bytes]],
) -> tuple[list[ParsedTrajectory], list[str]]:
    trajectories: list[ParsedTrajectory] = []
    errors: list[str] = []

    for source_name, contents in sources:
        suffix = Path(source_name).suffix.lower()
        if suffix == ".zip":
            parsed, zip_errors = parse_trajectory_zip(contents, source_name)
            trajectories.extend(parsed)
            errors.extend(zip_errors)
            continue
        if suffix not in SUPPORTED_TRAJECTORY_SUFFIXES:
            continue
        try:
            trajectories.append(parse_trajectory_bytes(contents, source_name))
        except ValueError as exc:
            errors.append(str(exc))

    deduped: dict[str, ParsedTrajectory] = {}
    for trajectory in trajectories:
        deduped[trajectory.key] = trajectory
    return list(deduped.values()), errors


def parse_trajectory_zip(
    contents: bytes,
    source_name: str,
) -> tuple[list[ParsedTrajectory], list[str]]:
    trajectories: list[ParsedTrajectory] = []
    errors: list[str] = []

    try:
        archive = zipfile.ZipFile(io.BytesIO(contents))
    except zipfile.BadZipFile as exc:
        return [], [f"{source_name} is not a valid zip file: {exc}"]

    with archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            member_suffix = Path(member.filename).suffix.lower()
            if member_suffix not in SUPPORTED_TRAJECTORY_SUFFIXES:
                continue
            try:
                trajectories.append(
                    parse_trajectory_bytes(
                        archive.read(member),
                        member.filename,
                    )
                )
            except ValueError as exc:
                errors.append(str(exc))

    return trajectories, errors


def parse_trajectory_directory(root: Path) -> tuple[list[ParsedTrajectory], list[str]]:
    if not root.exists():
        return [], [f"Directory not found: {root}"]

    sources = [
        (str(path.relative_to(root)), path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() == ".traj"
    ]
    return parse_trajectory_sources(sources)


def node_text(step: TrajectoryStep, node_kind: str) -> str:
    if node_kind == THOUGHT_NODE_KIND:
        return step.thought
    if node_kind == ACTION_NODE_KIND:
        return step.action
    if node_kind == RESULT_NODE_KIND:
        return step.result
    return ""


def build_relation_candidates(trajectory: ParsedTrajectory) -> list[RelationCandidate]:
    candidates: list[RelationCandidate] = []
    steps_by_index = {step.step_index: step for step in trajectory.steps}

    for family, spec in REL_SPECS.items():
        for step in trajectory.steps:
            source_step = step.step_index
            target_step = source_step + int(spec["offset"])
            target = steps_by_index.get(target_step)
            if target is None:
                continue

            source_node = step_node_id(spec["src"], source_step)
            target_node = step_node_id(spec["dst"], target_step)
            candidates.append(
                RelationCandidate(
                    key=f"{trajectory.key}|{family}|{source_step}",
                    task_id=trajectory.task_id,
                    family=family,
                    source_node=source_node,
                    target_node=target_node,
                    source_step=source_step,
                    target_step=target_step,
                    source_text=node_text(step, spec["src"]),
                    target_text=node_text(target, spec["dst"]),
                )
            )

    return candidates


def family_display_name(family: str) -> str:
    spec = REL_SPECS[family]
    return f"{node_kind_name(spec['src'])} -> {node_kind_name(spec['dst'])}"


def relation_label_options_for_family(family: str) -> tuple[str, ...]:
    return RELATION_LABEL_OPTIONS_BY_FAMILY.get(family, RELATION_LABEL_OPTIONS)


def ui_label_options_for_family(family: str) -> tuple[str, ...]:
    return (UNLABELED_RELATION_LABEL, *relation_label_options_for_family(family))


def label_for_candidate(candidate: RelationCandidate, labels: dict[str, str]) -> str:
    label = labels.get(candidate.key, UNLABELED_RELATION_LABEL)
    if label not in relation_label_options_for_family(candidate.family):
        return UNLABELED_RELATION_LABEL
    return label


def export_label_for_candidate(candidate: RelationCandidate, labels: dict[str, str]) -> str:
    label = label_for_candidate(candidate, labels)
    return "" if label == UNLABELED_RELATION_LABEL else label


def labeling_records(
    trajectory: ParsedTrajectory,
    labels: dict[str, str],
) -> list[dict[str, object]]:
    records = []
    for candidate in build_relation_candidates(trajectory):
        records.append(
            {
                "task_id": trajectory.task_id,
                "source_name": trajectory.source_name,
                "family": candidate.family,
                "family_display": family_display_name(candidate.family),
                "source_step": candidate.source_step,
                "target_step": candidate.target_step,
                "source_node": candidate.source_node,
                "target_node": candidate.target_node,
                REL_LABEL_COL: export_label_for_candidate(candidate, labels),
                "label_status": (
                    "unlabeled"
                    if label_for_candidate(candidate, labels) == UNLABELED_RELATION_LABEL
                    else "labeled"
                ),
                "source_text": candidate.source_text,
                "target_text": candidate.target_text,
            }
        )
    return records


def labels_json_bytes(trajectory: ParsedTrajectory, labels: dict[str, str]) -> bytes:
    payload = {
        "task_id": trajectory.task_id,
        "source_name": trajectory.source_name,
        "records": labeling_records(trajectory, labels),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def relation_csv_text(candidates: list[RelationCandidate], labels: dict[str, str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[REL_LABEL_COL], lineterminator="\n")
    writer.writeheader()
    for candidate in sorted(candidates, key=lambda item: item.source_step):
        writer.writerow({REL_LABEL_COL: export_label_for_candidate(candidate, labels)})
    return buffer.getvalue()


def relation_csv_zip_bytes(trajectory: ParsedTrajectory, labels: dict[str, str]) -> bytes:
    candidates_by_family: dict[str, list[RelationCandidate]] = {
        family: [] for family in REL_SPECS
    }
    for candidate in build_relation_candidates(trajectory):
        candidates_by_family[candidate.family].append(candidate)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for family, candidates in candidates_by_family.items():
            archive.writestr(
                f"{family}/{trajectory.task_id}.csv",
                relation_csv_text(candidates, labels),
            )
        archive.writestr(
            f"{trajectory.task_id}.labels.json",
            labels_json_bytes(trajectory, labels),
        )
    return buffer.getvalue()
