"""Relationship-labeling controls for the single-run workspace."""

from __future__ import annotations

import streamlit as st

from traceview_app.shared.formatting import wrapped_log_block
from traceview_app.labeling.state import LABELER_WIDGET_STATE_PREFIX
from traceview_app.labeling.workspace_shared import (
    LABELER_EDITOR_VERSION,
    black_row_text,
    option_index,
)
from traceview_app.shared.models import RelationCandidate
from traceview_app.trajectory import (
    UNLABELED_RELATION_LABEL,
    family_display_name,
    label_for_candidate,
    relation_label_options_for_family,
    short_preview,
    ui_label_options_for_family,
)


def _relationship_widget_key(candidate: RelationCandidate) -> str:
    return (
        f"{LABELER_WIDGET_STATE_PREFIX}{LABELER_EDITOR_VERSION}_relationship_"
        f"{candidate.key}"
    )


def _set_relationship_label(
    candidate: RelationCandidate,
    selected_label: str,
    current_labels: dict[str, str],
) -> None:
    if selected_label == UNLABELED_RELATION_LABEL:
        current_labels.pop(candidate.key, None)
    elif selected_label in relation_label_options_for_family(candidate.family):
        current_labels[candidate.key] = selected_label


def sync_relationship_labels_from_widgets(
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> None:
    for candidate in candidates:
        selected_label = st.session_state.get(_relationship_widget_key(candidate))
        if isinstance(selected_label, str):
            _set_relationship_label(candidate, selected_label, current_labels)


def discard_invalid_family_labels(
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> None:
    for candidate in candidates:
        label = current_labels.get(candidate.key)
        if label and label not in relation_label_options_for_family(candidate.family):
            current_labels.pop(candidate.key, None)


def render_relationship_label_rows(
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> None:
    header_cols = st.columns([1.5, 3.0, 3.0, 1.5])
    black_row_text(header_cols[0], "PAIR", bold=True)
    black_row_text(header_cols[1], "SOURCE PREVIEW", bold=True)
    black_row_text(header_cols[2], "TARGET PREVIEW", bold=True)
    black_row_text(header_cols[3], "LABEL", bold=True)

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
        black_row_text(row_cols[0], f"{candidate.source_node} -> {candidate.target_node}")
        black_row_text(row_cols[1], short_preview(candidate.source_text, limit=160))
        black_row_text(row_cols[2], short_preview(candidate.target_text, limit=160))
        with row_cols[3]:
            selected_label = st.selectbox(
                (
                    f"Relationship label for {candidate.source_node} "
                    f"to {candidate.target_node}"
                ),
                options=options,
                index=option_index(options, current_label),
                key=widget_key,
                label_visibility="collapsed",
            )
        _set_relationship_label(candidate, selected_label, current_labels)


def render_candidate_detail(
    candidate: RelationCandidate,
    current_labels: dict[str, str],
) -> None:
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
