"""Session state and loading helpers for relationship labeling."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import streamlit as st

from relationship_viewer_app.constants import BAD_RELS
from relationship_viewer_app.models import ParsedTrajectory, RelationCandidate
from relationship_viewer_app.swebench import (
    LOCAL_SWEAGENT_TRAJECTORY_DIR,
    UNLABELED_RELATION_LABEL,
    build_relation_candidates,
    label_for_candidate,
    parse_trajectory_directory,
    parse_trajectory_sources,
)

LABELER_TRAJECTORIES_STATE_KEY = "relationship_labeler_trajectories"
LABELER_ERRORS_STATE_KEY = "relationship_labeler_errors"
LABELER_LABELS_STATE_KEY = "relationship_labeler_labels"
LABELER_UPLOAD_SIGNATURE_STATE_KEY = "relationship_labeler_upload_signature"
LABELER_STAGE_STATE_KEY = "relationship_labeler_stage"
LABELER_SOURCE_META_STATE_KEY = "relationship_labeler_source_meta"
LABELER_SELECTED_TRAJECTORY_STATE_KEY = "relationship_labeler_selected_trajectory"
LABELER_PASTE_STATE_KEY = "relationship_labeler_paste"
LABELER_PROGRESS_ADVANCED_STATE_KEY = "relationship_labeler_progress_advanced"
LABELER_WORKSPACE_TOAST_STATE_KEY = "relationship_labeler_workspace_toast"

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
TRACE_UPLOAD_TYPES = ["traj", "json", "jsonl", "log", "txt", "zip"]


@dataclass(frozen=True)
class AnnotationStats:
    candidates: list[RelationCandidate]
    candidate_count: int
    labeled_count: int
    label_counts: Counter[str]
    bad_pairs: list[tuple[RelationCandidate, str]]


def set_loaded_trajectories(
    trajectories: list[ParsedTrajectory],
    errors: list[str],
    *,
    reset_labels: bool = False,
) -> None:
    st.session_state[LABELER_TRAJECTORIES_STATE_KEY] = trajectories
    st.session_state[LABELER_ERRORS_STATE_KEY] = errors
    if reset_labels:
        st.session_state[LABELER_LABELS_STATE_KEY] = {}
    else:
        st.session_state.setdefault(LABELER_LABELS_STATE_KEY, {})


def loaded_trajectories() -> list[ParsedTrajectory]:
    value = st.session_state.get(LABELER_TRAJECTORIES_STATE_KEY, [])
    return value if isinstance(value, list) else []


def labels() -> dict[str, str]:
    value = st.session_state.setdefault(LABELER_LABELS_STATE_KEY, {})
    return value if isinstance(value, dict) else {}


def format_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return ""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def source_meta_from_sources(sources: list[tuple[str, bytes]]) -> dict[str, object]:
    total_bytes = sum(len(contents) for _, contents in sources)
    name = sources[0][0] if len(sources) == 1 else f"{len(sources)} trace files"
    return {"name": name, "bytes": total_bytes}


def active_source_meta() -> dict[str, object]:
    value = st.session_state.get(LABELER_SOURCE_META_STATE_KEY, {})
    return value if isinstance(value, dict) else {}


def reset_annotation_flow() -> None:
    for key in (
        LABELER_TRAJECTORIES_STATE_KEY,
        LABELER_ERRORS_STATE_KEY,
        LABELER_LABELS_STATE_KEY,
        LABELER_UPLOAD_SIGNATURE_STATE_KEY,
        LABELER_SOURCE_META_STATE_KEY,
        LABELER_SELECTED_TRAJECTORY_STATE_KEY,
        LABELER_PASTE_STATE_KEY,
        LABELER_PROGRESS_ADVANCED_STATE_KEY,
        LABELER_WORKSPACE_TOAST_STATE_KEY,
    ):
        st.session_state.pop(key, None)
    st.session_state[LABELER_STAGE_STATE_KEY] = "ingest"


def start_annotation_from_sources(sources: list[tuple[str, bytes]]) -> bool:
    oversized = [
        f"{name} exceeds the 25 MB upload limit."
        for name, contents in sources
        if len(contents) > MAX_UPLOAD_BYTES
    ]
    valid_sources = [
        (name, contents)
        for name, contents in sources
        if len(contents) <= MAX_UPLOAD_BYTES
    ]
    trajectories, errors = parse_trajectory_sources(valid_sources)
    errors = oversized + errors

    if not trajectories:
        if not errors:
            errors = ["No supported trace files were found."]
        set_loaded_trajectories([], errors, reset_labels=True)
        st.session_state[LABELER_STAGE_STATE_KEY] = "ingest"
        return False

    set_loaded_trajectories(trajectories, errors, reset_labels=True)
    st.session_state[LABELER_SOURCE_META_STATE_KEY] = source_meta_from_sources(sources)
    st.session_state[LABELER_SELECTED_TRAJECTORY_STATE_KEY] = trajectories[0].key
    st.session_state[LABELER_PROGRESS_ADVANCED_STATE_KEY] = False
    st.session_state[LABELER_STAGE_STATE_KEY] = "annotating"
    return True


def start_annotation_from_local_folder() -> bool:
    trajectories, errors = parse_trajectory_directory(LOCAL_SWEAGENT_TRAJECTORY_DIR)
    if not trajectories:
        if not errors:
            errors = [f"No .traj files found in {LOCAL_SWEAGENT_TRAJECTORY_DIR}."]
        set_loaded_trajectories([], errors, reset_labels=True)
        st.session_state[LABELER_STAGE_STATE_KEY] = "ingest"
        return False

    total_bytes = sum(
        path.stat().st_size
        for path in LOCAL_SWEAGENT_TRAJECTORY_DIR.rglob("*.traj")
        if path.is_file()
    )
    set_loaded_trajectories(trajectories, errors, reset_labels=True)
    st.session_state[LABELER_SOURCE_META_STATE_KEY] = {
        "name": LOCAL_SWEAGENT_TRAJECTORY_DIR.name,
        "bytes": total_bytes,
    }
    st.session_state[LABELER_SELECTED_TRAJECTORY_STATE_KEY] = trajectories[0].key
    st.session_state[LABELER_PROGRESS_ADVANCED_STATE_KEY] = False
    st.session_state[LABELER_STAGE_STATE_KEY] = "annotating"
    return True


def selected_trajectory() -> ParsedTrajectory | None:
    trajectories = loaded_trajectories()
    if not trajectories:
        return None
    selected_key = st.session_state.get(LABELER_SELECTED_TRAJECTORY_STATE_KEY)
    for trajectory in trajectories:
        if trajectory.key == selected_key:
            return trajectory
    st.session_state[LABELER_SELECTED_TRAJECTORY_STATE_KEY] = trajectories[0].key
    return trajectories[0]


def annotation_stats(trajectory: ParsedTrajectory, current_labels: dict[str, str]) -> AnnotationStats:
    candidates = build_relation_candidates(trajectory)
    labeled_pairs = [
        (candidate, label_for_candidate(candidate, current_labels))
        for candidate in candidates
        if label_for_candidate(candidate, current_labels) != UNLABELED_RELATION_LABEL
    ]
    bad_pairs = [
        (candidate, label)
        for candidate, label in labeled_pairs
        if label in BAD_RELS
    ]
    return AnnotationStats(
        candidates=candidates,
        candidate_count=len(candidates),
        labeled_count=len(labeled_pairs),
        label_counts=Counter(label for _, label in labeled_pairs),
        bad_pairs=bad_pairs,
    )
