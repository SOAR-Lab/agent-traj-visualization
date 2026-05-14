"""Completion summary screen for relationship labeling."""

from __future__ import annotations

from collections import Counter, defaultdict

import pandas as pd
import streamlit as st

from traceview_app.shared.constants import (
    ACTION_LABEL_OPTIONS,
    BAD_RELS,
    LABELER_STAGE_INGEST,
    LABELER_STAGE_WORKSPACE,
    LOOPISH_RELS,
    NOINF_RELS,
)
from traceview_app.labeling.common_ui import render_labeling_header
from traceview_app.labeling.state import (
    LABELER_STAGE_STATE_KEY,
    LABELER_WORKSPACE_TOAST_STATE_KEY,
    active_source_meta,
    annotation_stats,
    action_labels,
    labels,
    reset_annotation_flow,
    selected_trajectory,
)
from traceview_app.shared.models import ParsedTrajectory, RelationCandidate
from traceview_app.trajectory import (
    UNLABELED_ACTION_LABEL,
    UNLABELED_RELATION_LABEL,
    action_label_for_step,
    label_for_candidate,
    short_preview,
)

BEHAVIOR_STATUS_ORDER = ("bad", "loop-ish", "no influence", "labeled", "unlabeled")
DISTRIBUTION_COLUMN = "Distribution"


def _with_distribution(
    rows: list[dict[str, object]],
    *,
    count_column: str,
    total: int,
) -> pd.DataFrame:
    for row in rows:
        count = int(row[count_column])
        row[DISTRIBUTION_COLUMN] = round((count / total) * 100) if total else 0
    return pd.DataFrame(rows)


def _relationship_count_rows(
    stats_candidate_count: int,
    label_counts: dict[str, int],
) -> pd.DataFrame:
    unlabeled_count = stats_candidate_count - sum(label_counts.values())
    rows = [
        {"Relationship": UNLABELED_RELATION_LABEL, "Count": unlabeled_count}
    ]
    rows.extend(
        {"Relationship": label, "Count": count}
        for label, count in sorted(
            label_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )
    return _with_distribution(
        [row for row in rows if int(row["Count"]) > 0],
        count_column="Count",
        total=stats_candidate_count,
    )


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
    status_counts = Counter(detail_df["Status"])
    count_df = _with_distribution(
        [
            {"Status": status, "Steps": status_counts[status]}
            for status in BEHAVIOR_STATUS_ORDER
            if status_counts[status]
        ],
        count_column="Steps",
        total=len(detail_df),
    )
    return count_df, detail_df


def _action_category_rows(
    trajectory: ParsedTrajectory,
    current_action_labels: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for step in sorted(trajectory.steps, key=lambda item: item.step_index):
        category = action_label_for_step(
            trajectory,
            step.step_index,
            current_action_labels,
        )
        rows.append(
            {
                "Iteration": step.step_index,
                "Category": category,
                "Action": short_preview(step.action, limit=180),
            }
        )

    detail_df = pd.DataFrame(rows)
    if detail_df.empty:
        return pd.DataFrame(columns=["Category", "Steps"]), detail_df

    count_order = (UNLABELED_ACTION_LABEL, *ACTION_LABEL_OPTIONS)
    category_counts = Counter(detail_df["Category"])
    count_df = pd.DataFrame(
        [
            {"Category": category, "Steps": category_counts[category]}
            for category in count_order
            if category_counts[category]
        ]
    )
    return _with_distribution(
        count_df.to_dict("records"),
        count_column="Steps",
        total=len(detail_df),
    ), detail_df


def _format_ratio(done: int, total: int) -> str:
    return f"{done} of {total}" if total else "0 of 0"


def _percent(done: int, total: int) -> int:
    return round((done / total) * 100) if total else 0


def _render_summary_actions(*, suffix: str) -> None:
    action_col, reset_col = st.columns([0.58, 0.42])
    with action_col:
        if st.button(
            "Open in single-run workspace",
            type="primary",
            width="stretch",
            key=f"summary_open_workspace_{suffix}",
        ):
            st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_WORKSPACE
            st.session_state[LABELER_WORKSPACE_TOAST_STATE_KEY] = True
            st.rerun()
    with reset_col:
        if st.button(
            "Re-annotate with different settings",
            width="stretch",
            key=f"summary_reannotate_{suffix}",
        ):
            reset_annotation_flow()
            st.rerun()


def _render_distribution_table(
    df: pd.DataFrame,
    *,
    label_column: str,
    count_column: str,
    empty_message: str,
) -> None:
    if df.empty:
        st.info(empty_message)
        return

    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            label_column: st.column_config.TextColumn(label_column, width="medium"),
            count_column: st.column_config.NumberColumn(count_column, width="small"),
            DISTRIBUTION_COLUMN: st.column_config.ProgressColumn(
                DISTRIBUTION_COLUMN,
                min_value=0,
                max_value=100,
                format="%d%%",
                width="medium",
            ),
        },
    )


def _render_coverage_header(
    *,
    iteration_count: int,
    action_labeled_count: int,
    relationship_labeled_count: int,
    relationship_count: int,
) -> None:
    graph_node_count = iteration_count * 3
    action_percent = _percent(action_labeled_count, iteration_count)
    relationship_percent = _percent(relationship_labeled_count, relationship_count)

    with st.container(border=True):
        st.caption("LABELING COVERAGE")
        metric_cols = st.columns(4)
        metric_cols[0].metric("Iterations", iteration_count)
        metric_cols[1].metric("Graph nodes", graph_node_count)
        metric_cols[2].metric("Action labels", _format_ratio(action_labeled_count, iteration_count))
        metric_cols[3].metric(
            "Relationship labels",
            _format_ratio(relationship_labeled_count, relationship_count),
        )

        progress_cols = st.columns(2)
        with progress_cols[0]:
            st.progress(
                action_percent / 100,
                text=f"Action labeling {action_percent}%",
            )
        with progress_cols[1]:
            st.progress(
                relationship_percent / 100,
                text=f"Relationship labeling {relationship_percent}%",
            )


def render_summary_screen() -> None:
    trajectory = selected_trajectory()
    if trajectory is None:
        st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_INGEST
        st.rerun()

    current_labels = labels()
    current_action_labels = action_labels()
    stats = annotation_stats(trajectory, current_labels)
    relationship_counts = _relationship_count_rows(
        stats.candidate_count,
        dict(stats.label_counts),
    )
    status_counts, behavior_detail = _behavior_rows(
        trajectory,
        stats.candidates,
        current_labels,
    )
    action_counts, action_detail = _action_category_rows(
        trajectory,
        current_action_labels,
    )
    action_labeled_count = int(
        (action_detail["Category"] != UNLABELED_ACTION_LABEL).sum()
        if not action_detail.empty
        else 0
    )

    meta = active_source_meta()
    render_labeling_header(
        "ANNOTATION COMPLETE",
        str(meta.get("name") or trajectory.source_name),
    )

    _render_coverage_header(
        iteration_count=len(trajectory.steps),
        action_labeled_count=action_labeled_count,
        relationship_labeled_count=stats.labeled_count,
        relationship_count=stats.candidate_count,
    )
    _render_summary_actions(suffix="top")

    st.info("Every annotation is editable in the single-run workspace.")

    summary_tab, behavior_tab, action_tab, issues_tab = st.tabs(
        ["Summary", "Behavior", "Action Categories", "Issues"]
    )

    with summary_tab:
        with st.container(border=True):
            st.caption("RELATIONSHIP LABELS")
            _render_distribution_table(
                relationship_counts,
                label_column="Relationship",
                count_column="Count",
                empty_message="No relationship candidates are available for this trace.",
            )

    with behavior_tab:
        with st.container(border=True):
            st.caption("BEHAVIOR")
            _render_distribution_table(
                status_counts,
                label_column="Status",
                count_column="Steps",
                empty_message="No behavior data is available for this trace.",
            )
            with st.expander("Iteration behavior detail"):
                st.dataframe(behavior_detail, hide_index=True, width="stretch")

    with action_tab:
        with st.container(border=True):
            st.caption("ACTION CATEGORIES")
            _render_distribution_table(
                action_counts,
                label_column="Category",
                count_column="Steps",
                empty_message="No action category data is available for this trace.",
            )
            with st.expander("Iteration action category detail"):
                st.dataframe(action_detail, hide_index=True, width="stretch")

    with issues_tab:
        with st.container(border=True):
            st.caption("ISSUES")
            if stats.labeled_count == 0:
                st.info("Relationship issue checks are pending until relationships are labeled.")
            elif stats.bad_pairs:
                st.error("Bad relationships found.")
                st.dataframe(
                    _bad_relationship_rows(stats.bad_pairs),
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.success("No contradiction, misinterpretation, or misalignment labels found.")
