"""Action-labeling controls for the single-run workspace."""

from __future__ import annotations

import streamlit as st

from traceview_app.shared.constants import ACTION_LABEL_OPTIONS
from traceview_app.shared.formatting import wrapped_log_block
from traceview_app.labeling.state import LABELER_WIDGET_STATE_PREFIX
from traceview_app.labeling.workspace_shared import (
    LABELER_EDITOR_VERSION,
    black_row_text,
    option_index,
)
from traceview_app.shared.models import ParsedTrajectory, TrajectoryStep
from traceview_app.trajectory import (
    UNLABELED_ACTION_LABEL,
    action_label_for_step,
    action_label_key,
    short_preview,
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


def _action_widget_key(trajectory: ParsedTrajectory, step_index: int) -> str:
    return (
        f"{LABELER_WIDGET_STATE_PREFIX}{LABELER_EDITOR_VERSION}_action_"
        f"{trajectory.key}_{step_index}"
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


def sync_action_labels_from_widgets(
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


def render_action_label_rows(
    trajectory: ParsedTrajectory,
    current_action_labels: dict[str, str],
) -> None:
    options = (UNLABELED_ACTION_LABEL, *ACTION_LABEL_OPTIONS)
    header_cols = st.columns([0.7, 4.3, 0.8, 1.5])
    black_row_text(header_cols[0], "ITERATION", bold=True)
    black_row_text(header_cols[1], "ACTION PREVIEW", bold=True)
    black_row_text(header_cols[2], "LOG", bold=True)
    black_row_text(header_cols[3], "LABEL", bold=True)

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
        black_row_text(row_cols[0], step.step_index)
        black_row_text(row_cols[1], short_preview(step.action, limit=240))
        with row_cols[2]:
            _render_step_log_popover(step)
        with row_cols[3]:
            selected_label = st.selectbox(
                f"Action label for iteration {step.step_index}",
                options=options,
                index=option_index(options, current_label),
                key=widget_key,
                label_visibility="collapsed",
            )
        _set_action_label(
            trajectory,
            step.step_index,
            selected_label,
            current_action_labels,
        )
