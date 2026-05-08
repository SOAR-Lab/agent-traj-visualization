"""Annotation and viewer export helpers for parsed trajectories."""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from pathlib import Path

from traceview_app.shared.constants import (
    ACTIONS_CATEGORIES_CAT_COL,
    ACTIONS_CATEGORIES_FOLDER,
    ACTIONS_CATEGORIES_ITER_COL,
    LABELER_VIEWER_EXPORTS_PATH,
    LOGS_DIR,
    REL_LABEL_COL,
    REL_SPECS,
    ROOT,
)
from traceview_app.shared.models import ParsedTrajectory, RelationCandidate
from traceview_app.trajectory.common import (
    UNLABELED_ACTION_LABEL,
    UNLABELED_RELATION_LABEL,
    VIEWER_EXPORT_CATEGORY,
    coerce_text,
)
from traceview_app.trajectory.relationships import (
    action_label_for_step,
    build_relation_candidates,
    export_action_label_for_step,
    export_label_for_candidate,
    family_display_name,
    label_for_candidate,
)


def action_labeling_records(
    trajectory: ParsedTrajectory,
    action_labels: dict[str, str],
) -> list[dict[str, object]]:
    return [
        {
            "task_id": trajectory.task_id,
            "source_name": trajectory.source_name,
            "iteration": step.step_index,
            "action_label": action_label_for_step(
                trajectory,
                step.step_index,
                action_labels,
            ),
            "export_category": export_action_label_for_step(
                trajectory,
                step.step_index,
                action_labels,
            ),
            "action_text": step.action,
        }
        for step in sorted(trajectory.steps, key=lambda item: item.step_index)
    ]


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


def annotation_json_bytes(
    trajectory: ParsedTrajectory,
    relation_labels: dict[str, str],
    action_labels: dict[str, str] | None = None,
) -> bytes:
    payload = {
        "task_id": trajectory.task_id,
        "source_name": trajectory.source_name,
        "action_records": action_labeling_records(trajectory, action_labels or {}),
        "relationship_records": labeling_records(trajectory, relation_labels),
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


def action_categories_csv_text(
    trajectory: ParsedTrajectory,
    *,
    action_labels: dict[str, str] | None = None,
    category: str = VIEWER_EXPORT_CATEGORY,
) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[ACTIONS_CATEGORIES_ITER_COL, ACTIONS_CATEGORIES_CAT_COL],
        lineterminator="\n",
    )
    writer.writeheader()
    current_action_labels = action_labels or {}
    for step in sorted(trajectory.steps, key=lambda item: item.step_index):
        writer.writerow(
            {
                ACTIONS_CATEGORIES_ITER_COL: step.step_index,
                ACTIONS_CATEGORIES_CAT_COL: (
                    export_action_label_for_step(
                        trajectory,
                        step.step_index,
                        current_action_labels,
                    )
                    if current_action_labels
                    else category
                ),
            }
        )
    return buffer.getvalue()


def viewer_csv_zip_bytes(
    trajectory: ParsedTrajectory,
    relation_labels: dict[str, str],
    action_labels: dict[str, str] | None = None,
) -> bytes:
    candidates_by_family: dict[str, list[RelationCandidate]] = {
        family: [] for family in REL_SPECS
    }
    for candidate in build_relation_candidates(trajectory):
        candidates_by_family[candidate.family].append(candidate)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            f"{ACTIONS_CATEGORIES_FOLDER}/{trajectory.task_id}.csv",
            action_categories_csv_text(trajectory, action_labels=action_labels or {}),
        )
        for family, candidates in candidates_by_family.items():
            archive.writestr(
                f"{family}/{trajectory.task_id}.csv",
                relation_csv_text(candidates, relation_labels),
            )
        archive.writestr(
            f"{trajectory.task_id}.labels.json",
            annotation_json_bytes(
                trajectory,
                relation_labels,
                action_labels,
            ),
        )
    return buffer.getvalue()


def reconstructed_log_text(trajectory: ParsedTrajectory) -> str:
    blocks = []
    for step in sorted(trajectory.steps, key=lambda item: item.step_index):
        blocks.append(
            "\n".join(
                [
                    f"Iteration {step.step_index}",
                    "",
                    "Thought:",
                    step.thought,
                    "",
                    "Action:",
                    step.action,
                    "",
                    "Result:",
                    step.result,
                ]
            )
        )
    return "\n\n".join(blocks).rstrip() + "\n"


def safe_viewer_dataset_stem(task_id: str) -> str:
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", coerce_text(task_id))
    stem = re.sub(r"\s+", "-", stem).strip(".- ")
    return stem[:120] or "labeled-trajectory"


def _viewer_dataset_paths(filename: str) -> list[Path]:
    return [
        ROOT / ACTIONS_CATEGORIES_FOLDER / filename,
        LOGS_DIR / Path(filename).with_suffix(".txt").name,
        *[ROOT / family / filename for family in REL_SPECS],
    ]


def unique_viewer_dataset_filename(task_id: str) -> str:
    base_stem = safe_viewer_dataset_stem(task_id)
    candidate_stems = [base_stem, f"{base_stem}-labeled"]
    candidate_stems.extend(f"{base_stem}-labeled-{index}" for index in range(2, 10_000))

    for stem in candidate_stems:
        filename = f"{stem}.csv"
        if not any(path.exists() for path in _viewer_dataset_paths(filename)):
            return filename

    raise RuntimeError(f"Could not find an available filename for {task_id!r}.")


def record_labeler_viewer_export(filename: str, trajectory: ParsedTrajectory) -> None:
    LABELER_VIEWER_EXPORTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {"runs": {}}
    if LABELER_VIEWER_EXPORTS_PATH.exists():
        try:
            loaded = json.loads(LABELER_VIEWER_EXPORTS_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = {"runs": {}}

    runs = payload.get("runs")
    if not isinstance(runs, dict):
        runs = {}
    runs[filename] = {
        "agent_name": "uploaded",
        "scored": False,
        "source_name": trajectory.source_name,
        "task_id": trajectory.task_id,
    }
    payload["runs"] = runs
    payload["schema_version"] = 1
    LABELER_VIEWER_EXPORTS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_viewer_dataset_files(
    trajectory: ParsedTrajectory,
    labels: dict[str, str],
    action_labels: dict[str, str] | None = None,
) -> str:
    filename = unique_viewer_dataset_filename(trajectory.task_id)

    action_path = ROOT / ACTIONS_CATEGORIES_FOLDER / filename
    action_path.parent.mkdir(parents=True, exist_ok=True)
    action_path.write_text(
        action_categories_csv_text(trajectory, action_labels=action_labels or {}),
        encoding="utf-8",
    )

    log_path = LOGS_DIR / Path(filename).with_suffix(".txt").name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(reconstructed_log_text(trajectory), encoding="utf-8")

    candidates_by_family: dict[str, list[RelationCandidate]] = {
        family: [] for family in REL_SPECS
    }
    for candidate in build_relation_candidates(trajectory):
        candidates_by_family[candidate.family].append(candidate)

    for family, candidates in candidates_by_family.items():
        relation_path = ROOT / family / filename
        relation_path.parent.mkdir(parents=True, exist_ok=True)
        relation_path.write_text(
            relation_csv_text(candidates, labels),
            encoding="utf-8",
        )

    record_labeler_viewer_export(filename, trajectory)
    return filename
