"""Editable single-run workspace for relationship labeling."""

from __future__ import annotations

import streamlit as st

from traceview_app.shared.constants import (
    LABELER_STAGE_COMPLETE,
    LABELER_STAGE_INGEST,
    REL_SPECS,
)
from traceview_app.labeling.workspace_action_ui import (
    render_action_label_rows,
    sync_action_labels_from_widgets,
)
from traceview_app.labeling.common_ui import (
    render_labeling_header,
    render_labeling_notice,
    render_parser_warnings,
)
from traceview_app.labeling.workspace_relationship_ui import (
    discard_invalid_family_labels,
    render_candidate_detail,
    render_relationship_label_rows,
    sync_relationship_labels_from_widgets,
)
from traceview_app.labeling.state import (
    LABELER_ERRORS_STATE_KEY,
    LABELER_SELECTED_TRAJECTORY_STATE_KEY,
    LABELER_STAGE_STATE_KEY,
    LABELER_WORKSPACE_TOAST_STATE_KEY,
    LABELER_WORKSPACE_STEP_STATE_KEY,
    action_labels,
    active_source_meta,
    labels,
    loaded_trajectories,
)
from traceview_app.labeling.workspace_shared import (
    WORKSPACE_STEP_ACTIONS,
    WORKSPACE_STEP_RELATIONSHIPS,
    count_action_labels,
    count_relationship_labels,
)
from traceview_app.labeling.workspace_sidebar import render_workspace_sidebar
from traceview_app.shared.models import ParsedTrajectory
from traceview_app.trajectory import (
    build_relation_candidates,
    family_display_name,
    relation_label_options_for_family,
)


def _trajectory_sidebar_select(trajectories: list[ParsedTrajectory]) -> ParsedTrajectory:
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

    selected_label = st.sidebar.selectbox(
        "Trajectory",
        option_labels,
        index=selected_index,
    )
    trajectory = trajectory_options[selected_label]
    st.session_state[LABELER_SELECTED_TRAJECTORY_STATE_KEY] = trajectory.key
    return trajectory


def _family_sidebar_select() -> tuple[str, str]:
    family_options = {
        family_display_name(family): family
        for family in REL_SPECS
    }
    selected_family_label = st.sidebar.selectbox(
        "Relationship family",
        list(family_options),
    )
    return selected_family_label, family_options[selected_family_label]


def _workspace_step(actions_complete: bool) -> str:
    workspace_step = st.session_state.setdefault(
        LABELER_WORKSPACE_STEP_STATE_KEY,
        WORKSPACE_STEP_ACTIONS,
    )
    if workspace_step not in (WORKSPACE_STEP_ACTIONS, WORKSPACE_STEP_RELATIONSHIPS):
        workspace_step = WORKSPACE_STEP_ACTIONS
        st.session_state[LABELER_WORKSPACE_STEP_STATE_KEY] = workspace_step
    if workspace_step == WORKSPACE_STEP_RELATIONSHIPS and not actions_complete:
        workspace_step = WORKSPACE_STEP_ACTIONS
        st.session_state[LABELER_WORKSPACE_STEP_STATE_KEY] = workspace_step
    return workspace_step


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

    render_parser_warnings(st.session_state.get(LABELER_ERRORS_STATE_KEY, []))

    st.sidebar.header("Labeling")
    if st.sidebar.button("Back to annotation summary", width="stretch"):
        st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_COMPLETE
        st.rerun()
    trajectory = _trajectory_sidebar_select(trajectories)

    current_action_labels = action_labels()
    current_labels = labels()
    all_candidates = build_relation_candidates(trajectory)
    sync_action_labels_from_widgets(trajectory, current_action_labels)
    sync_relationship_labels_from_widgets(all_candidates, current_labels)

    labeled_count = count_relationship_labels(all_candidates, current_labels)
    action_labeled_count = count_action_labels(trajectory, current_action_labels)
    action_count = len(trajectory.steps)
    actions_complete = action_labeled_count == action_count
    workspace_step = _workspace_step(actions_complete)

    if workspace_step == WORKSPACE_STEP_ACTIONS:
        st.markdown("#### Action Labels")
        st.caption(
            "Label the action taken in each iteration. These labels drive Overview "
            "behavior and graph action categories."
        )
        render_action_label_rows(trajectory, current_action_labels)
        action_labeled_count = count_action_labels(trajectory, current_action_labels)
        actions_complete = action_labeled_count == action_count

        render_workspace_sidebar(
            trajectory=trajectory,
            current_action_labels=current_action_labels,
            current_labels=current_labels,
            action_labeled_count=action_labeled_count,
            all_candidates=all_candidates,
            labeled_count=labeled_count,
            actions_complete=actions_complete,
            workspace_step=workspace_step,
        )

        if actions_complete:
            st.success("All actions are labeled.")
        else:
            st.info(
                f"Label {action_count - action_labeled_count} more actions to "
                "continue to relationships."
            )
        return

    selected_family_label, selected_family = _family_sidebar_select()
    family_candidates = [
        candidate for candidate in all_candidates if candidate.family == selected_family
    ]
    discard_invalid_family_labels(family_candidates, current_labels)

    st.markdown(f"#### Relationship Labels: {selected_family_label}")
    st.caption(
        "Only the `Label` column is editable. Allowed labels: "
        + ", ".join(relation_label_options_for_family(selected_family))
    )
    render_relationship_label_rows(family_candidates, current_labels)
    labeled_count = count_relationship_labels(all_candidates, current_labels)

    render_workspace_sidebar(
        trajectory=trajectory,
        current_action_labels=current_action_labels,
        current_labels=current_labels,
        action_labeled_count=action_labeled_count,
        all_candidates=all_candidates,
        labeled_count=labeled_count,
        actions_complete=actions_complete,
        workspace_step=workspace_step,
        selected_family=selected_family,
        selected_family_label=selected_family_label,
    )

    candidate_options = {
        f"{candidate.source_node} -> {candidate.target_node}": candidate
        for candidate in family_candidates
    }
    if candidate_options:
        selected_candidate_label = st.selectbox(
            "Inspect relationship",
            list(candidate_options),
        )
        render_candidate_detail(candidate_options[selected_candidate_label], current_labels)
