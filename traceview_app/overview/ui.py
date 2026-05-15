"""Overview-page UI for run selection and filtering."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from traceview_app.labeling.resume_export import resume_viewer_export_in_workspace
from traceview_app.shared.constants import (
    APP_ROUTE_STATE_KEY,
    OVERVIEW_NOTICE_STATE_KEY,
    OVERVIEW_SELECTED_FILE_KEY,
    ROUTE_LABELING,
)
from traceview_app.overview.data import (
    bug_report_url_from_filename,
    delete_user_viewer_export,
)
from traceview_app.shared.models import OverviewRow
from traceview_app.shared.formatting import format_task_name

OVERVIEW_TABLE_HEIGHT = 930


def _render_wrapped_summary_text(
    text: object,
    *,
    font_size: str = "1rem",
    font_weight: int = 400,
    color: str = "#111827",
    line_height: str = "1.25",
) -> None:
    st.markdown(
        (
            f'<div style="font-size:{font_size};font-weight:{font_weight};'
            f'color:{color};line-height:{line_height};'
            'overflow-wrap:anywhere;word-break:break-word;">'
            f"{html.escape(str(text))}</div>"
        ),
        unsafe_allow_html=True,
    )


def _outcome_badge_color(outcome: str) -> str:
    if outcome == "pass":
        return "green"
    if outcome == "fail":
        return "red"
    return "gray"


def _compact_categories(categories: list[str], limit: int = 5) -> str:
    if not categories:
        return "none"

    grouped = []
    current = categories[0]
    count = 0
    for category in categories:
        if category == current:
            count += 1
            continue
        grouped.append((current, count))
        current = category
        count = 1
    grouped.append((current, count))

    parts = [
        f"{category} x{count}" if count > 1 else category
        for category, count in grouped[:limit]
    ]
    if len(grouped) > limit:
        parts.append("...")
    return " > ".join(parts)


def _format_flags(row: OverviewRow, limit: int = 4) -> str:
    flags = [str(tag).lower() for tag in row.get("flagged_relations", [])]
    return ", ".join(flags[:limit]) if flags else "none"


def _relation_counts_df(relation_counts: dict[str, int], limit: int = 8) -> pd.DataFrame:
    if not relation_counts:
        return pd.DataFrame(columns=["Relation", "Count"])

    sorted_counts = sorted(
        relation_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:limit]
    return pd.DataFrame(
        [{"Relation": relation, "Count": str(count)} for relation, count in sorted_counts]
    )


def _overview_table_df(rows: list[OverviewRow]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Agent": row["agent_name"],
                "Outcome": row["outcome"],
                "Iterations": str(row["iteration_count"]),
                "Issue number": format_task_name(row["task_id"]),
                "Behavior": _compact_categories(row.get("categories", [])),
                "Relationship anomalies": _format_flags(row),
            }
            for row in rows
        ]
    )


def _overview_summary_metrics(rows: list[OverviewRow]) -> None:
    total = len(rows)
    pass_count = sum(1 for row in rows if row["outcome"] == "pass")
    fail_count = sum(1 for row in rows if row["outcome"] == "fail")
    unscored_count = sum(1 for row in rows if row["outcome"] == "unscored")
    avg_iterations = (
        sum(int(row["iteration_count"]) for row in rows) / total if total else 0
    )

    metric_cols = st.columns(5)
    metric_cols[0].metric("Runs", total)
    metric_cols[1].metric("Pass", pass_count)
    metric_cols[2].metric("Fail", fail_count)
    metric_cols[3].metric("Unscored", unscored_count)
    metric_cols[4].metric("Avg iterations", f"{avg_iterations:.1f}")


def _render_delete_uploaded_trace(row: OverviewRow) -> None:
    if not row.get("is_user_export"):
        return

    with st.popover("Delete uploaded trace", use_container_width=True):
        st.write(
            "Remove this uploaded trace from local Overview and Analysis data. "
            "Bundled AutoCodeRover runs cannot be deleted here."
        )
        if st.button(
            "Delete this trace",
            type="secondary",
            width="stretch",
            key=f"delete_uploaded_trace_{row['filename']}",
        ):
            delete_user_viewer_export(row["filename"])
            st.cache_data.clear()
            st.session_state.pop(OVERVIEW_SELECTED_FILE_KEY, None)
            st.session_state[OVERVIEW_NOTICE_STATE_KEY] = (
                f"Deleted uploaded trace {row['task_id']}."
            )
            st.rerun()


def _render_continue_labeling(row: OverviewRow) -> None:
    if not row.get("is_user_export"):
        return

    if st.button(
        "Continue labeling trace",
        width="stretch",
        key=f"continue_labeling_{row['filename']}",
    ):
        try:
            resume_viewer_export_in_workspace(row["filename"])
        except ValueError as exc:
            st.error(str(exc))
            return
        st.session_state[APP_ROUTE_STATE_KEY] = ROUTE_LABELING
        st.rerun()


def render_overview_page(rows: list[OverviewRow]) -> str | None:
    if not rows:
        st.info("No task runs are available.")
        return None

    if notice := st.session_state.pop(OVERVIEW_NOTICE_STATE_KEY, None):
        st.success(str(notice))

    selected_filename = st.session_state.get(OVERVIEW_SELECTED_FILE_KEY)
    if selected_filename not in {row["filename"] for row in rows}:
        selected_filename = rows[0]["filename"]
        st.session_state[OVERVIEW_SELECTED_FILE_KEY] = selected_filename

    st.markdown("### Runs")
    _overview_summary_metrics(rows)

    tag_options = sorted(
        {
            tag.lower()
            for row in rows
            for tag in row.get("flagged_relations", [])
        }
    )

    filter_col, table_col, summary_col = st.columns([0.12, 0.60, 0.28], gap="medium")

    with filter_col:
        with st.container(border=True):
            st.caption("FILTERS")
            outcome_filter = st.radio(
                "Outcome",
                ["all", "pass", "fail", "unscored"],
                horizontal=False,
                label_visibility="visible",
            )
            selected_tags = st.multiselect("Tags", tag_options)
            search_text = st.text_input("Task search", placeholder="django, sympy, issue...")

    filtered_rows = rows
    if outcome_filter != "all":
        filtered_rows = [row for row in filtered_rows if row["outcome"] == outcome_filter]
    if selected_tags:
        selected_tag_set = set(selected_tags)
        filtered_rows = [
            row
            for row in filtered_rows
            if selected_tag_set.intersection(
                {tag.lower() for tag in row.get("flagged_relations", [])}
            )
        ]
    if search_text.strip():
        needle = search_text.strip().lower()
        filtered_rows = [
            row
            for row in filtered_rows
            if needle in row["task_id"].lower()
            or needle in format_task_name(row["task_id"]).lower()
        ]

    if filtered_rows and selected_filename not in {row["filename"] for row in filtered_rows}:
        selected_filename = filtered_rows[0]["filename"]
        st.session_state[OVERVIEW_SELECTED_FILE_KEY] = selected_filename

    with table_col:
        if not filtered_rows:
            st.warning("No runs match the current filters.")
        else:
            table_state = st.dataframe(
                _overview_table_df(filtered_rows),
                hide_index=True,
                width="stretch",
                height=OVERVIEW_TABLE_HEIGHT,
                on_select="rerun",
                selection_mode="single-row",
                key="overview_run_table",
                column_config={
                    "Iterations": st.column_config.TextColumn(
                        "Iterations",
                        help="Number of detailed iterations in the run.",
                    ),
                    "Behavior": st.column_config.TextColumn(
                        "Behavior",
                        help="Compressed sequence of action categories.",
                    ),
                },
            )
            selected_indices = table_state.selection.rows
            if selected_indices and selected_indices[0] < len(filtered_rows):
                selected_filename = filtered_rows[selected_indices[0]]["filename"]
                st.session_state[OVERVIEW_SELECTED_FILE_KEY] = selected_filename

    selected_row = next(
        (row for row in rows if row["filename"] == selected_filename),
        rows[0],
    )

    with summary_col:
        with st.container(border=True):
            bug_report_url = (
                bug_report_url_from_filename(selected_row["filename"])
                if selected_row.get("pull_request_url")
                else None
            )
            st.caption("RUN SUMMARY")
            _render_wrapped_summary_text(
                format_task_name(selected_row["task_id"]),
                font_size="1.45rem",
                font_weight=650,
                line_height="1.18",
            )
            _render_wrapped_summary_text(
                selected_row["task_id"],
                font_size="0.85rem",
                color="#6B7280",
            )
            metric_cols = st.columns(2)
            with metric_cols[0]:
                st.caption("Outcome")
                st.badge(
                    selected_row["outcome"].upper(),
                    color=_outcome_badge_color(selected_row["outcome"]),
                )
            metric_cols[1].metric("Iterations", selected_row["iteration_count"])
            st.markdown("**Behavior**")
            st.write(_compact_categories(selected_row.get("categories", []), limit=10))
            st.markdown("**Relations**")
            relation_counts_df = _relation_counts_df(
                selected_row.get("relation_counts", {})
            )
            if relation_counts_df.empty:
                st.caption("No labeled relations")
            else:
                st.dataframe(
                    relation_counts_df,
                    hide_index=True,
                    width="stretch",
                )
            st.markdown("**Relationship anomalies**")
            st.write(_format_flags(selected_row, limit=6))
            if bug_report_url:
                st.link_button(
                    "Open bug report",
                    bug_report_url,
                    width="stretch",
                )
            if selected_row.get("pull_request_url"):
                st.link_button(
                    "Open solving pull request",
                    selected_row["pull_request_url"],
                    width="stretch",
                )
            _render_continue_labeling(selected_row)
            _render_delete_uploaded_trace(selected_row)
            if st.button("Open analysis", type="primary", width="stretch"):
                return selected_row["filename"]

    return None
