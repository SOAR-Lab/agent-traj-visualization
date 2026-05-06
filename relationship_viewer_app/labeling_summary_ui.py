"""Completion summary screen for relationship labeling."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd
import streamlit as st

from relationship_viewer_app.constants import (
    BAD_RELS,
    LABELER_STAGE_INGEST,
    LABELER_STAGE_WORKSPACE,
    LOOPISH_RELS,
    NOINF_RELS,
)
from relationship_viewer_app.labeling_common_ui import render_labeling_header
from relationship_viewer_app.labeling_state import (
    LABELER_STAGE_STATE_KEY,
    LABELER_WORKSPACE_TOAST_STATE_KEY,
    active_source_meta,
    annotation_stats,
    labels,
    reset_annotation_flow,
    selected_trajectory,
)
from relationship_viewer_app.models import ParsedTrajectory, RelationCandidate
from relationship_viewer_app.trajectory_parser import (
    UNLABELED_RELATION_LABEL,
    label_for_candidate,
)


def _label_count_rows(stats_candidate_count: int, label_counts: dict[str, int]) -> pd.DataFrame:
    if not label_counts:
        return pd.DataFrame(
            [{"Relationship": "unlabeled candidates", "Count": stats_candidate_count}]
        )

    rows = [
        {"Relationship": label, "Count": count}
        for label, count in sorted(
            label_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]
    return pd.DataFrame(rows)


def _bad_relationship_rows(bad_pairs: list[tuple[RelationCandidate, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Label": label,
                "Source": candidate.source_node,
                "Target": candidate.target_node,
            }
            for candidate, label in bad_pairs
        ]
    )


def _behavior_rows(
    trajectory: ParsedTrajectory,
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels_by_step: dict[int, list[str]] = defaultdict(list)
    for candidate in candidates:
        label = label_for_candidate(candidate, current_labels)
        if label == UNLABELED_RELATION_LABEL:
            continue
        labels_by_step[candidate.source_step].append(label)
        labels_by_step[candidate.target_step].append(label)

    rows = []
    for step in trajectory.steps:
        step_labels = labels_by_step.get(step.step_index, [])
        if any(label in BAD_RELS for label in step_labels):
            status = "bad"
        elif any(label in LOOPISH_RELS for label in step_labels):
            status = "loop-ish"
        elif any(label in NOINF_RELS for label in step_labels):
            status = "no influence"
        elif step_labels:
            status = "labeled"
        else:
            status = "unlabeled"
        rows.append(
            {
                "Iteration": step.step_index,
                "Status": status,
                "Labels": ", ".join(sorted(set(step_labels))),
            }
        )

    detail_df = pd.DataFrame(rows)
    count_df = (
        detail_df["Status"]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Steps")
        .sort_values("Status")
    )
    return count_df, detail_df


def render_summary_screen() -> None:
    trajectory = selected_trajectory()
    if trajectory is None:
        st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_INGEST
        st.rerun()

    current_labels = labels()
    stats = annotation_stats(trajectory, current_labels)
    confidence = "n/a"
    if stats.candidate_count:
        confidence = f"{round((stats.labeled_count / stats.candidate_count) * 100)}%"

    meta = active_source_meta()
    render_labeling_header(
        "ANNOTATION COMPLETE",
        str(meta.get("name") or trajectory.source_name),
    )

    left, right = st.columns([1.04, 1.0])
    with left:
        with st.container(border=True):
            st.caption("ANNOTATION SUMMARY")
            node_cols = st.columns(3)
            node_cols[0].metric("Thoughts", len(trajectory.steps))
            node_cols[1].metric("Actions", len(trajectory.steps))
            node_cols[2].metric("Results", len(trajectory.steps))

            st.caption("RELATIONSHIPS")
            st.dataframe(
                _label_count_rows(stats.candidate_count, dict(stats.label_counts)),
                hide_index=True,
                width="stretch",
            )

            if stats.bad_pairs:
                st.error("Bad relationships found.")
                st.dataframe(
                    _bad_relationship_rows(stats.bad_pairs),
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.success("No contradiction, misinterpretation, or misalignment labels yet.")

    with right:
        with st.container(border=True):
            st.caption("CLASSIFIER CONFIDENCE")
            st.metric("Relationship labeling", confidence)
            st.caption("Low-confidence labels can be reviewed in the workspace.")

        with st.container(border=True):
            st.caption("BEHAVIOR")
            status_counts, behavior_detail = _behavior_rows(
                trajectory,
                stats.candidates,
                current_labels,
            )
            st.bar_chart(status_counts, x="Status", y="Steps", width="stretch")
            with st.expander("Iteration behavior detail"):
                st.dataframe(behavior_detail, hide_index=True, width="stretch")

        st.info("Every annotation is editable in the single-run workspace.")

        if st.button("Open in single-run workspace", type="primary", width="stretch"):
            st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_WORKSPACE
            st.session_state[LABELER_WORKSPACE_TOAST_STATE_KEY] = True
            st.rerun()
        if st.button("Re-annotate with different settings", width="stretch"):
            reset_annotation_flow()
            st.rerun()
