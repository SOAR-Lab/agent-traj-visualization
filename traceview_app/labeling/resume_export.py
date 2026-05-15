"""Reload user viewer exports into the labeling workspace."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from traceview_app.labeling.state import (
    LABELER_ACTION_LABELS_STATE_KEY,
    LABELER_LABELS_STATE_KEY,
    LABELER_PROGRESS_ADVANCED_STATE_KEY,
    LABELER_SELECTED_TRAJECTORY_STATE_KEY,
    LABELER_SOURCE_META_STATE_KEY,
    LABELER_STAGE_STATE_KEY,
    LABELER_WORKSPACE_STEP_STATE_KEY,
    LABELER_WORKSPACE_TOAST_STATE_KEY,
    set_loaded_trajectories,
)
from traceview_app.labeling.workspace_shared import (
    WORKSPACE_STEP_ACTIONS,
    WORKSPACE_STEP_RELATIONSHIPS,
    count_action_labels,
    labels_ready,
)
from traceview_app.overview.data import (
    corresponding_log_path,
    is_user_viewer_export_filename,
    load_categories,
    load_labeler_export_metadata,
    load_relation_labels,
    normalize_rel,
    task_id_from_filename,
)
from traceview_app.shared.constants import (
    ACTIONS_CATEGORIES_CAT_COL,
    ACTIONS_CATEGORIES_ITER_COL,
    ACTION_LABEL_OPTIONS,
    LABELER_STAGE_WORKSPACE,
    REL_LABEL_COL,
    REL_SPECS,
)
from traceview_app.shared.models import ParsedTrajectory
from traceview_app.trajectory import (
    UNLABELED_ACTION_LABEL,
    UNLABELED_RELATION_LABEL,
    action_label_key,
    build_relation_candidates,
    parse_trajectory_sources,
    relation_label_options_for_family,
)


@dataclass(frozen=True)
class ResumedViewerExport:
    trajectory: ParsedTrajectory
    action_labels: dict[str, str]
    relationship_labels: dict[str, str]
    source_bytes: int


def _canonical_action_label(value: object) -> str:
    label = str(value or "").strip()
    option_by_key = {option.lower(): option for option in ACTION_LABEL_OPTIONS}
    return option_by_key.get(label.lower(), "")


def _canonical_relation_label(value: object, family: str) -> str:
    label = str(value or "").strip()
    if not label:
        return ""

    options = relation_label_options_for_family(family)
    if label in options:
        return label

    normalized_options = {
        normalize_rel(option): option
        for option in (*options, UNLABELED_RELATION_LABEL)
    }
    return normalized_options.get(normalize_rel(label), "")


def _parse_exported_log(filename: str) -> ResumedViewerExport:
    metadata = load_labeler_export_metadata().get(filename, {})
    if not metadata and not is_user_viewer_export_filename(filename):
        raise ValueError("Only user-uploaded TraceView exports can be reopened for labeling.")

    log_path = corresponding_log_path(filename)
    if not log_path.exists():
        raise ValueError(f"Cannot reopen {filename}: reconstructed log file is missing.")

    contents = log_path.read_bytes()
    trajectories, errors = parse_trajectory_sources([(log_path.name, contents)])
    if not trajectories:
        detail = f" {' '.join(errors)}" if errors else ""
        raise ValueError(f"Cannot reopen {filename}: reconstructed log could not be parsed.{detail}")

    parsed = trajectories[0]
    task_id = str(metadata.get("task_id") or task_id_from_filename(filename))
    source_name = str(metadata.get("source_name") or parsed.source_name)
    trajectory = ParsedTrajectory(
        task_id=task_id,
        source_name=source_name,
        steps=parsed.steps,
    )
    return ResumedViewerExport(
        trajectory=trajectory,
        action_labels={},
        relationship_labels={},
        source_bytes=len(contents),
    )


def load_viewer_export_for_labeling(filename: str) -> ResumedViewerExport:
    resumed = _parse_exported_log(filename)
    trajectory = resumed.trajectory

    action_labels: dict[str, str] = {}
    categories = load_categories(filename)
    for _, row in categories.iterrows():
        label = _canonical_action_label(row[ACTIONS_CATEGORIES_CAT_COL])
        if label and label != UNLABELED_ACTION_LABEL:
            action_labels[
                action_label_key(trajectory, int(row[ACTIONS_CATEGORIES_ITER_COL]))
            ] = label

    relationship_labels: dict[str, str] = {}
    candidates_by_family = {family: [] for family in REL_SPECS}
    for candidate in build_relation_candidates(trajectory):
        candidates_by_family[candidate.family].append(candidate)

    for family, candidates in candidates_by_family.items():
        if not candidates:
            continue

        frame = load_relation_labels(family, filename)
        if frame.empty:
            continue

        ordered_candidates = sorted(
            candidates,
            key=lambda candidate: (
                candidate.source_step,
                candidate.target_step,
                candidate.source_node,
                candidate.target_node,
            ),
        )
        for candidate, (_, row) in zip(ordered_candidates, frame.iterrows()):
            label = _canonical_relation_label(row[REL_LABEL_COL], family)
            if label and label != UNLABELED_RELATION_LABEL:
                relationship_labels[candidate.key] = label

    return ResumedViewerExport(
        trajectory=trajectory,
        action_labels=action_labels,
        relationship_labels=relationship_labels,
        source_bytes=resumed.source_bytes,
    )


def resume_viewer_export_in_workspace(filename: str) -> ParsedTrajectory:
    resumed = load_viewer_export_for_labeling(filename)
    trajectory = resumed.trajectory

    set_loaded_trajectories([trajectory], [], reset_labels=True)
    st.session_state[LABELER_ACTION_LABELS_STATE_KEY] = resumed.action_labels
    st.session_state[LABELER_LABELS_STATE_KEY] = resumed.relationship_labels
    st.session_state[LABELER_SOURCE_META_STATE_KEY] = {
        "name": trajectory.source_name,
        "bytes": resumed.source_bytes,
    }
    st.session_state[LABELER_SELECTED_TRAJECTORY_STATE_KEY] = trajectory.key
    st.session_state[LABELER_PROGRESS_ADVANCED_STATE_KEY] = True
    st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_WORKSPACE
    st.session_state[LABELER_WORKSPACE_TOAST_STATE_KEY] = True

    action_labeled_count = count_action_labels(trajectory, resumed.action_labels)
    st.session_state[LABELER_WORKSPACE_STEP_STATE_KEY] = (
        WORKSPACE_STEP_RELATIONSHIPS
        if labels_ready(action_labeled_count, len(trajectory.steps))
        else WORKSPACE_STEP_ACTIONS
    )
    return trajectory
