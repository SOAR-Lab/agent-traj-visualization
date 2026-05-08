"""Editable single-run workspace for relationship labeling."""

from __future__ import annotations

import html

import streamlit as st

from traceview_app.constants import (
    ACTION_LABEL_OPTIONS,
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
    render_action_label_legend,
    render_labeling_header,
    render_labeling_notice,
    render_parser_warnings,
    render_relationship_label_legend,
)
from traceview_app.labeling_state import (
    LABELER_ERRORS_STATE_KEY,
    LABELER_SELECTED_TRAJECTORY_STATE_KEY,
    LABELER_STAGE_STATE_KEY,
    LABELER_WIDGET_STATE_PREFIX,
    LABELER_WORKSPACE_TOAST_STATE_KEY,
    LABELER_WORKSPACE_STEP_STATE_KEY,
    action_labels,
    active_source_meta,
    labels,
    loaded_trajectories,
)
from traceview_app.models import ParsedTrajectory, RelationCandidate, TrajectoryStep
from traceview_app.trajectory_parser import (
    UNLABELED_ACTION_LABEL,
    UNLABELED_RELATION_LABEL,
    action_label_for_step,
    action_label_key,
    annotation_json_bytes,
    build_relation_candidates,
    family_display_name,
    label_for_candidate,
    relation_label_options_for_family,
    short_preview,
    ui_label_options_for_family,
    viewer_csv_zip_bytes,
    write_viewer_dataset_files,
)
from traceview_app.formatting import wrapped_log_block

LABELER_EDITOR_VERSION = "v4"
WORKSPACE_STEP_ACTIONS = "actions"
WORKSPACE_STEP_RELATIONSHIPS = "relationships"


def _black_row_text(target: object, text: object, *, bold: bool = False) -> None:
    weight = "600" if bold else "400"
    target.markdown(
        (
            f'<span style="color:#111111;font-size:0.875rem;'
            f'font-weight:{weight};">{html.escape(str(text))}</span>'
        ),
        unsafe_allow_html=True,
    )


def _render_step_log_popover(step: TrajectoryStep) -> None:
    with st.popover("View", use_container_width=True):
        st.markdown(f"**Iteration {step.step_index}**")
        st.markdown("**Thought**")
        wrapped_log_block(step.thought)
        st.markdown("**Action**")
        wrapped_log_block(step.action)
        st.markdown("**Result**")
        wrapped_log_block(step.result)


def _option_index(options: tuple[str, ...], label: str) -> int:
    try:
        return options.index(label)
    except ValueError:
        return 0


def _action_widget_key(trajectory: ParsedTrajectory, step_index: int) -> str:
    return (
        f"{LABELER_WIDGET_STATE_PREFIX}{LABELER_EDITOR_VERSION}_action_"
        f"{trajectory.key}_{step_index}"
    )


def _relationship_widget_key(candidate: RelationCandidate) -> str:
    return (
        f"{LABELER_WIDGET_STATE_PREFIX}{LABELER_EDITOR_VERSION}_relationship_"
        f"{candidate.key}"
    )


def _set_action_label(
    trajectory: ParsedTrajectory,
    step_index: int,
    selected_label: str,
    current_action_labels: dict[str, str],
) -> None:
    key = action_label_key(trajectory, step_index)
    if selected_label == UNLABELED_ACTION_LABEL:
        current_action_labels.pop(key, None)
    elif selected_label in ACTION_LABEL_OPTIONS:
        current_action_labels[key] = selected_label


def _set_relationship_label(
    candidate: RelationCandidate,
    selected_label: str,
    current_labels: dict[str, str],
) -> None:
    if selected_label == UNLABELED_RELATION_LABEL:
        current_labels.pop(candidate.key, None)
    elif selected_label in relation_label_options_for_family(candidate.family):
        current_labels[candidate.key] = selected_label


def _sync_action_labels_from_widgets(
    trajectory: ParsedTrajectory,
    current_action_labels: dict[str, str],
) -> None:
    for step in trajectory.steps:
        widget_key = _action_widget_key(trajectory, step.step_index)
        selected_label = st.session_state.get(widget_key)
        if isinstance(selected_label, str):
            _set_action_label(
                trajectory,
                step.step_index,
                selected_label,
                current_action_labels,
            )


def _sync_relationship_labels_from_widgets(
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> None:
    for candidate in candidates:
        selected_label = st.session_state.get(_relationship_widget_key(candidate))
        if isinstance(selected_label, str):
            _set_relationship_label(candidate, selected_label, current_labels)


def _count_action_labels(
    trajectory: ParsedTrajectory,
    current_action_labels: dict[str, str],
) -> int:
    return sum(
        1
        for step in trajectory.steps
        if action_label_for_step(
            trajectory,
            step.step_index,
            current_action_labels,
        )
        != UNLABELED_ACTION_LABEL
    )


def _count_relationship_labels(
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> int:
    return sum(
        1
        for candidate in candidates
        if label_for_candidate(candidate, current_labels) != UNLABELED_RELATION_LABEL
    )


def _discard_invalid_family_labels(
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> None:
    for candidate in candidates:
        label = current_labels.get(candidate.key)
        if label and label not in relation_label_options_for_family(candidate.family):
            current_labels.pop(candidate.key, None)


def _render_action_label_rows(
    trajectory: ParsedTrajectory,
    current_action_labels: dict[str, str],
) -> None:
    options = (UNLABELED_ACTION_LABEL, *ACTION_LABEL_OPTIONS)
    header_cols = st.columns([0.7, 4.3, 0.8, 1.5])
    _black_row_text(header_cols[0], "ITERATION", bold=True)
    _black_row_text(header_cols[1], "ACTION PREVIEW", bold=True)
    _black_row_text(header_cols[2], "LOG", bold=True)
    _black_row_text(header_cols[3], "LABEL", bold=True)

    for step in sorted(trajectory.steps, key=lambda item: item.step_index):
        current_label = action_label_for_step(
            trajectory,
            step.step_index,
            current_action_labels,
        )
        widget_key = _action_widget_key(trajectory, step.step_index)
        if (
            widget_key in st.session_state
            and st.session_state[widget_key] not in options
        ):
            st.session_state[widget_key] = current_label

        row_cols = st.columns([0.7, 4.3, 0.8, 1.5])
        _black_row_text(row_cols[0], step.step_index)
        _black_row_text(row_cols[1], short_preview(step.action, limit=240))
        with row_cols[2]:
            _render_step_log_popover(step)
        with row_cols[3]:
            selected_label = st.selectbox(
                f"Action label for iteration {step.step_index}",
                options=options,
                index=_option_index(options, current_label),
                key=widget_key,
                label_visibility="collapsed",
            )
        _set_action_label(
            trajectory,
            step.step_index,
            selected_label,
            current_action_labels,
        )


def _render_relationship_label_rows(
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> None:
    header_cols = st.columns([1.5, 3.0, 3.0, 1.5])
    _black_row_text(header_cols[0], "PAIR", bold=True)
    _black_row_text(header_cols[1], "SOURCE PREVIEW", bold=True)
    _black_row_text(header_cols[2], "TARGET PREVIEW", bold=True)
    _black_row_text(header_cols[3], "LABEL", bold=True)

    for candidate in candidates:
        options = ui_label_options_for_family(candidate.family)
        current_label = label_for_candidate(candidate, current_labels)
        widget_key = _relationship_widget_key(candidate)
        if (
            widget_key in st.session_state
            and st.session_state[widget_key] not in options
        ):
            st.session_state[widget_key] = current_label

        row_cols = st.columns([1.5, 3.0, 3.0, 1.5])
        _black_row_text(row_cols[0], f"{candidate.source_node} -> {candidate.target_node}")
        _black_row_text(row_cols[1], short_preview(candidate.source_text, limit=160))
        _black_row_text(row_cols[2], short_preview(candidate.target_text, limit=160))
        with row_cols[3]:
            selected_label = st.selectbox(
                (
                    f"Relationship label for {candidate.source_node} "
                    f"to {candidate.target_node}"
                ),
                options=options,
                index=_option_index(options, current_label),
                key=widget_key,
                label_visibility="collapsed",
            )
        _set_relationship_label(candidate, selected_label, current_labels)


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


def _render_workspace_sidebar(
    *,
    trajectory: ParsedTrajectory,
    current_action_labels: dict[str, str],
    current_labels: dict[str, str],
    action_labeled_count: int,
    all_candidates: list[RelationCandidate],
    labeled_count: int,
    actions_complete: bool,
    workspace_step: str,
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
    st.sidebar.progress(
        progress,
        text=f"{labeled_count} of {candidate_count} relationships labeled",
    )
    st.sidebar.caption(
        f"Unlabeled relationships: {candidate_count - labeled_count}"
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

    st.sidebar.caption("EXPORT")
    can_export = actions_complete and workspace_step == WORKSPACE_STEP_RELATIONSHIPS
    if not actions_complete:
        st.sidebar.caption("Finish action labels before exporting.")
    elif workspace_step != WORKSPACE_STEP_RELATIONSHIPS:
        st.sidebar.caption("Continue to relationship labels before exporting.")
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
    _sync_action_labels_from_widgets(trajectory, current_action_labels)
    _sync_relationship_labels_from_widgets(all_candidates, current_labels)
    labeled_count = _count_relationship_labels(all_candidates, current_labels)
    action_labeled_count = _count_action_labels(trajectory, current_action_labels)
    action_count = len(trajectory.steps)
    actions_complete = action_labeled_count == action_count
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

    if workspace_step == WORKSPACE_STEP_ACTIONS:
        st.markdown("#### Action Labels")
        st.caption(
            "Label the action taken in each iteration. These labels drive Overview "
            "behavior and graph action categories."
        )
        render_action_label_legend()
        _render_action_label_rows(trajectory, current_action_labels)
        action_labeled_count = _count_action_labels(trajectory, current_action_labels)
        actions_complete = action_labeled_count == action_count

        _render_workspace_sidebar(
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
    _discard_invalid_family_labels(family_candidates, current_labels)

    st.markdown(f"#### Relationship Labels: {selected_family_label}")
    st.caption(
        "Only the `Label` column is editable. Allowed labels: "
        + ", ".join(relation_label_options_for_family(selected_family))
    )
    render_relationship_label_legend()
    _render_relationship_label_rows(family_candidates, current_labels)
    labeled_count = _count_relationship_labels(all_candidates, current_labels)

    _render_workspace_sidebar(
        trajectory=trajectory,
        current_action_labels=current_action_labels,
        current_labels=current_labels,
        action_labeled_count=action_labeled_count,
        all_candidates=all_candidates,
        labeled_count=labeled_count,
        actions_complete=actions_complete,
        workspace_step=workspace_step,
    )

    candidate_options = {
        f"{candidate.source_node} -> {candidate.target_node}": candidate
        for candidate in family_candidates
    }
    if candidate_options:
        selected_candidate_label = st.selectbox("Inspect relationship", list(candidate_options))
        _render_candidate_detail(candidate_options[selected_candidate_label], current_labels)
