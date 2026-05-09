"""Sidebar progress and export controls for the labeling workspace."""

from __future__ import annotations

import streamlit as st

from traceview_app.labeling.common_ui import (
    render_compact_action_label_legend,
    render_compact_relationship_label_legend,
)
from traceview_app.shared.constants import (
    APP_ROUTE_STATE_KEY,
    DETAIL_FILENAME_STATE_KEY,
    OVERVIEW_NOTICE_STATE_KEY,
    OVERVIEW_SELECTED_FILE_KEY,
    ROUTE_OVERVIEW,
    TASK_FILE_SELECT_STATE_KEY,
)
from traceview_app.labeling.state import LABELER_WORKSPACE_STEP_STATE_KEY
from traceview_app.labeling.workspace_shared import (
    WORKSPACE_STEP_ACTIONS,
    WORKSPACE_STEP_RELATIONSHIPS,
)
from traceview_app.shared.models import ParsedTrajectory, RelationCandidate
from traceview_app.trajectory import (
    annotation_json_bytes,
    viewer_csv_zip_bytes,
    write_viewer_dataset_files,
)


def _send_to_overview(
    trajectory: ParsedTrajectory,
    current_labels: dict[str, str],
    current_action_labels: dict[str, str],
) -> None:
    filename = write_viewer_dataset_files(
        trajectory,
        current_labels,
        current_action_labels,
    )
    st.cache_data.clear()
    st.session_state[OVERVIEW_SELECTED_FILE_KEY] = filename
    st.session_state[TASK_FILE_SELECT_STATE_KEY] = filename
    st.session_state[DETAIL_FILENAME_STATE_KEY] = filename
    st.session_state[OVERVIEW_NOTICE_STATE_KEY] = (
        f"{trajectory.task_id} was added to Overview as {filename}."
    )
    st.session_state[APP_ROUTE_STATE_KEY] = ROUTE_OVERVIEW
    st.rerun()


def render_workspace_sidebar(
    *,
    trajectory: ParsedTrajectory,
    current_action_labels: dict[str, str],
    current_labels: dict[str, str],
    action_labeled_count: int,
    all_candidates: list[RelationCandidate],
    labeled_count: int,
    actions_complete: bool,
    workspace_step: str,
    selected_family: str | None = None,
    selected_family_label: str | None = None,
) -> None:
    candidate_count = len(all_candidates)
    action_count = len(trajectory.steps)
    progress = labeled_count / candidate_count if candidate_count else 0
    action_progress = action_labeled_count / action_count if action_count else 0

    st.sidebar.caption("PROGRESS")
    st.sidebar.progress(
        action_progress,
        text=f"{action_labeled_count} of {action_count} actions labeled",
    )
    if workspace_step == WORKSPACE_STEP_RELATIONSHIPS:
        st.sidebar.progress(
            progress,
            text=f"{labeled_count} of {candidate_count} relationships labeled",
        )
        st.sidebar.caption(
            f"Unlabeled relationships: {candidate_count - labeled_count}"
        )

    st.sidebar.caption("LEGEND")
    if workspace_step == WORKSPACE_STEP_ACTIONS:
        with st.sidebar.container(border=True):
            render_compact_action_label_legend()
    else:
        legend_title = selected_family_label or "RELATIONSHIP LABELS"
        with st.sidebar.container(border=True):
            render_compact_relationship_label_legend(
                selected_family,
                title=legend_title.upper(),
            )

    if workspace_step == WORKSPACE_STEP_ACTIONS and actions_complete:
        if st.sidebar.button(
            "Continue to relationship labels",
            type="primary",
            width="stretch",
        ):
            st.session_state[LABELER_WORKSPACE_STEP_STATE_KEY] = (
                WORKSPACE_STEP_RELATIONSHIPS
            )
            st.rerun()
    elif workspace_step == WORKSPACE_STEP_RELATIONSHIPS:
        if st.sidebar.button("Review action labels", width="stretch"):
            st.session_state[LABELER_WORKSPACE_STEP_STATE_KEY] = WORKSPACE_STEP_ACTIONS
            st.rerun()

    can_export = actions_complete and workspace_step == WORKSPACE_STEP_RELATIONSHIPS
    if not actions_complete:
        st.sidebar.caption("Finish action labels before exporting.")
        return
    if workspace_step != WORKSPACE_STEP_RELATIONSHIPS:
        st.sidebar.caption("Continue to relationship labels before exporting.")
        return

    st.sidebar.caption("EXPORT")
    if st.sidebar.button(
        "Send to overview",
        type="primary",
        width="stretch",
        disabled=not can_export,
    ):
        _send_to_overview(trajectory, current_labels, current_action_labels)
    st.sidebar.download_button(
        "Download annotations JSON",
        data=annotation_json_bytes(
            trajectory,
            current_labels,
            current_action_labels,
        ),
        file_name=f"{trajectory.task_id}.annotations.json",
        mime="application/json",
        width="stretch",
        disabled=not can_export,
    )
    st.sidebar.download_button(
        "Download viewer CSV zip",
        data=viewer_csv_zip_bytes(
            trajectory,
            current_labels,
            current_action_labels,
        ),
        file_name=f"{trajectory.task_id}.viewer_csvs.zip",
        mime="application/zip",
        width="stretch",
        disabled=not can_export,
    )
