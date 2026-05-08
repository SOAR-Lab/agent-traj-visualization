"""Editable single-run workspace for relationship labeling."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from traceview_app.constants import (
    APP_ROUTE_STATE_KEY,
    DETAIL_FILENAME_STATE_KEY,
    LABELER_STAGE_COMPLETE,
    LABELER_STAGE_INGEST,
    OVERVIEW_NOTICE_STATE_KEY,
    OVERVIEW_SELECTED_FILE_KEY,
    REL_SPECS,
    ROUTE_OVERVIEW,
    TASK_FILE_SELECT_STATE_KEY,
)
from traceview_app.labeling_common_ui import (
    render_labeling_header,
    render_labeling_notice,
    render_parser_warnings,
    render_relationship_label_legend,
)
from traceview_app.labeling_state import (
    LABELER_ERRORS_STATE_KEY,
    LABELER_SELECTED_TRAJECTORY_STATE_KEY,
    LABELER_STAGE_STATE_KEY,
    LABELER_WORKSPACE_TOAST_STATE_KEY,
    active_source_meta,
    labels,
    loaded_trajectories,
)
from traceview_app.models import ParsedTrajectory, RelationCandidate
from traceview_app.trajectory_parser import (
    UNLABELED_RELATION_LABEL,
    build_relation_candidates,
    family_display_name,
    label_for_candidate,
    labels_json_bytes,
    relation_csv_zip_bytes,
    relation_label_options_for_family,
    short_preview,
    ui_label_options_for_family,
    write_viewer_dataset_files,
)
from traceview_app.formatting import wrapped_log_block

LABELER_EDITOR_VERSION = "v4"


def _candidate_rows(
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Key": candidate.key,
                "Source": candidate.source_node,
                "Target": candidate.target_node,
                "Source preview": short_preview(candidate.source_text),
                "Target preview": short_preview(candidate.target_text),
                "Label": label_for_candidate(candidate, current_labels),
            }
            for candidate in candidates
        ]
    )


def _sync_labels_from_editor(
    edited_rows: pd.DataFrame,
    current_labels: dict[str, str],
    candidates_by_key: dict[str, RelationCandidate],
) -> None:
    if edited_rows.empty:
        return

    for row in edited_rows.to_dict("records"):
        key = str(row.get("Key", ""))
        label = str(row.get("Label", ""))
        candidate = candidates_by_key.get(key)
        if not candidate:
            continue
        if label == UNLABELED_RELATION_LABEL:
            current_labels.pop(key, None)
        elif label in relation_label_options_for_family(candidate.family):
            current_labels[key] = label


def _discard_invalid_family_labels(
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> None:
    for candidate in candidates:
        label = current_labels.get(candidate.key)
        if label and label not in relation_label_options_for_family(candidate.family):
            current_labels.pop(candidate.key, None)


def _render_candidate_detail(candidate: RelationCandidate, current_labels: dict[str, str]) -> None:
    st.markdown("#### Selected Relationship")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Family", family_display_name(candidate.family))
    metric_cols[1].metric("Source", candidate.source_node)
    metric_cols[2].metric("Target", candidate.target_node)

    st.caption(f"Current label: {label_for_candidate(candidate, current_labels)}")

    source_col, target_col = st.columns(2)
    with source_col:
        st.markdown("**Source evidence**")
        wrapped_log_block(candidate.source_text)
    with target_col:
        st.markdown("**Target evidence**")
        wrapped_log_block(candidate.target_text)


def _trajectory_select(trajectories: list[ParsedTrajectory]) -> ParsedTrajectory:
    trajectory_options = {
        f"{trajectory.task_id} ({len(trajectory.steps)} steps)": trajectory
        for trajectory in trajectories
    }
    current_key = st.session_state.get(LABELER_SELECTED_TRAJECTORY_STATE_KEY)
    option_labels = list(trajectory_options)
    selected_index = 0
    for index, option_label in enumerate(option_labels):
        if trajectory_options[option_label].key == current_key:
            selected_index = index
            break

    selected_label = st.selectbox("Trajectory", option_labels, index=selected_index)
    trajectory = trajectory_options[selected_label]
    st.session_state[LABELER_SELECTED_TRAJECTORY_STATE_KEY] = trajectory.key
    return trajectory


def _send_to_overview(trajectory: ParsedTrajectory, current_labels: dict[str, str]) -> None:
    filename = write_viewer_dataset_files(trajectory, current_labels)
    st.cache_data.clear()
    st.session_state[OVERVIEW_SELECTED_FILE_KEY] = filename
    st.session_state[TASK_FILE_SELECT_STATE_KEY] = filename
    st.session_state[DETAIL_FILENAME_STATE_KEY] = filename
    st.session_state[OVERVIEW_NOTICE_STATE_KEY] = (
        f"{trajectory.task_id} was added to Overview as {filename}."
    )
    st.session_state[APP_ROUTE_STATE_KEY] = ROUTE_OVERVIEW
    st.rerun()


def render_workspace_page() -> None:
    trajectories = loaded_trajectories()
    if not trajectories:
        st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_INGEST
        st.rerun()

    meta = active_source_meta()
    render_labeling_header(
        "SINGLE-RUN WORKSPACE",
        str(meta.get("name") or "uploaded trace"),
    )

    if st.session_state.pop(LABELER_WORKSPACE_TOAST_STATE_KEY, False):
        render_labeling_notice(
            "Opening single-run workspace with all annotations applied. "
            "You can edit any relationship label in the inspector."
        )

    _, action_col = st.columns([0.72, 0.28], vertical_alignment="bottom")
    with action_col:
        if st.button("Back to annotation summary", width="stretch"):
            st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_COMPLETE
            st.rerun()

    render_parser_warnings(st.session_state.get(LABELER_ERRORS_STATE_KEY, []))

    trajectory = _trajectory_select(trajectories)
    current_labels = labels()
    all_candidates = build_relation_candidates(trajectory)
    labeled_count = sum(1 for candidate in all_candidates if candidate.key in current_labels)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Task", trajectory.task_id)
    metric_cols[1].metric("Steps", len(trajectory.steps))
    metric_cols[2].metric("Relationships", len(all_candidates))
    metric_cols[3].metric("Touched labels", labeled_count)

    family_options = {
        family_display_name(family): family
        for family in REL_SPECS
    }
    selected_family_label = st.selectbox("Relationship family", list(family_options))
    selected_family = family_options[selected_family_label]
    family_candidates = [
        candidate for candidate in all_candidates if candidate.family == selected_family
    ]
    _discard_invalid_family_labels(family_candidates, current_labels)

    st.markdown("#### Label Table")
    st.caption(
        "Only the `Label` column is editable. Allowed labels: "
        + ", ".join(relation_label_options_for_family(selected_family))
    )
    render_relationship_label_legend()
    candidates_by_key = {candidate.key: candidate for candidate in family_candidates}
    edited_rows = st.data_editor(
        _candidate_rows(family_candidates, current_labels),
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        disabled=["Key", "Source", "Target", "Source preview", "Target preview"],
        column_config={
            "Key": None,
            "Label": st.column_config.SelectboxColumn(
                "Label",
                options=list(ui_label_options_for_family(selected_family)),
                required=True,
            ),
        },
        key=f"{LABELER_EDITOR_VERSION}_label_editor_{trajectory.key}_{selected_family}",
    )
    _sync_labels_from_editor(edited_rows, current_labels, candidates_by_key)

    candidate_options = {
        f"{candidate.source_node} -> {candidate.target_node}": candidate
        for candidate in family_candidates
    }
    if candidate_options:
        selected_candidate_label = st.selectbox("Inspect relationship", list(candidate_options))
        _render_candidate_detail(candidate_options[selected_candidate_label], current_labels)

    export_col_a, export_col_b, export_col_c = st.columns(3)
    with export_col_a:
        st.download_button(
            "Download labels JSON",
            data=labels_json_bytes(trajectory, current_labels),
            file_name=f"{trajectory.task_id}.labels.json",
            mime="application/json",
            width="stretch",
        )
    with export_col_b:
        st.download_button(
            "Download viewer CSV zip",
            data=relation_csv_zip_bytes(trajectory, current_labels),
            file_name=f"{trajectory.task_id}.relationship_csvs.zip",
            mime="application/zip",
            width="stretch",
        )
    with export_col_c:
        if st.button("Send to overview", type="primary", width="stretch"):
            _send_to_overview(trajectory, current_labels)
