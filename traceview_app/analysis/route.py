"""Analysis and inspector route UI."""

from __future__ import annotations

import streamlit as st
from streamlit_agraph import Config, agraph

from traceview_app.analysis.inspector_ui import render_inspector
from traceview_app.analysis.iteration_context import SHOW_DERIVED_ITERATION_CONTEXT
from traceview_app.analysis.iteration_ui import render_iteration_context_panel
from traceview_app.analysis.sidebar_ui import render_sidebar_controls
from traceview_app.analysis.view_context import build_view_context
from traceview_app.shared.constants import (
    APP_ROUTE_STATE_KEY,
    CATEGORY_COLOR,
    DETAIL_FILENAME_STATE_KEY,
    DETAIL_PAGE_GRAPH,
    DETAIL_PAGE_INSPECTOR,
    ROUTE_ANALYSIS,
    ROUTE_INSPECTOR,
    STRUCTURAL_EDGE_COLOR,
    STRUCTURAL_REL_LABEL,
)
from traceview_app.shared.formatting import format_task_name
from traceview_app.shared.models import SidebarControls, StaticRelationRecord, ViewContext

INSPECTOR_SCROLL_TOP_STATE_KEY = "traceview_inspector_scroll_top"
DETAIL_PAGE_STATE_KEY = "traceview_page"
DETAIL_NODE_STATE_KEY = "traceview_selected_node"
DETAIL_CONTROLS_STATE_KEY = "traceview_controls"
PENDING_ANALYSIS_FILENAME_STATE_KEY = "traceview_pending_analysis_filename"


def queue_analysis_filename(filename: str, *, clear_stale_node: bool = True) -> None:
    previous_filename = st.session_state.get(DETAIL_FILENAME_STATE_KEY)
    st.session_state[DETAIL_FILENAME_STATE_KEY] = filename
    st.session_state[PENDING_ANALYSIS_FILENAME_STATE_KEY] = filename
    if clear_stale_node and filename != previous_filename:
        st.session_state.pop(DETAIL_NODE_STATE_KEY, None)


def format_patch_status_label(primary_status: str) -> str:
    pretty = {
        "RESOLVED": "RESOLVED",
        "PATCH NOT APPLIED": "NO APPLY",
        "TEST ERRORED": "TEST ERRORED",
        "TEST TIMEOUT": "TEST TIMEOUT",
        "NO GENERATION": "NO GENERATION",
        "INSTALL FAIL": "INSTALL FAIL",
        "RESET FAILED": "RESET FAILED",
        "APPLIED": "APPLIED",
        "GENERATED": "GENERATED",
        "HAS LOGS": "HAS LOGS",
        "UNKNOWN": "UNKNOWN",
    }
    if primary_status == "UNKNOWN":
        return "UNSCORED"
    shown = pretty.get(primary_status, primary_status)
    if primary_status == "RESOLVED":
        return f"PASS ({shown})"
    return f"FAIL ({shown})"


def patch_category_badge_color(category: str) -> str:
    normalized = category.strip().lower()
    if normalized == "resolved":
        return "green"
    if normalized in {"test_timeout", "test_errored", "no_apply", "no_generation"}:
        return "red"
    if normalized in {"applied", "generated"}:
        return "blue"
    if normalized in {"with_logs", "install_fail", "reset_failed"}:
        return "orange"
    return "gray"


def action_category_legend(title: str = "#### Action Categories") -> None:
    st.markdown(title)

    items = [
        ("Explore", CATEGORY_COLOR["explore"]),
        ("Locate", CATEGORY_COLOR["locate"]),
        ("Search", CATEGORY_COLOR["search"]),
        ("Reproduce", CATEGORY_COLOR["reproduce"]),
        ("Generate fix", CATEGORY_COLOR["generate fix"]),
        ("Run tests", CATEGORY_COLOR["run tests"]),
        ("Refactor", CATEGORY_COLOR["refactor"]),
        ("Explain", CATEGORY_COLOR["explain"]),
    ]

    cols = st.columns(4)
    for index, (label, color) in enumerate(items):
        with cols[index % 4]:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <div style="width:14px;height:14px;border-radius:50%;background:{color};border:1px solid #444;"></div>
                    <div>{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def relation_legend(title: str = "#### Edge Types") -> None:
    items = [
        ("Good flow", "#54A24B"),
        ("Shift / divergence", "#F58518"),
        ("Loop-ish", "#7F3C8D"),
        ("Bad", "#E45756"),
        ("No influence", "#9E9E9E"),
        (STRUCTURAL_REL_LABEL, STRUCTURAL_EDGE_COLOR),
    ]
    st.markdown(title)
    cols = st.columns(3)
    for index, (label, color) in enumerate(items):
        with cols[index % 3]:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <div style="width:18px;height:4px;background:{color};border-radius:3px;"></div>
                    <div>{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_shared_legend() -> None:
    st.markdown("### Legend")
    st.caption("Node color shows action category. Edge color shows relation type in both modes.")

    col_left, col_right = st.columns([1.35, 1.0])
    with col_left:
        action_category_legend()
    with col_right:
        relation_legend()


def render_patch_overview(
    *,
    task_id: str,
    bug_report_url: str | None,
    pull_request_url: str | None,
    graph_mode: str,
    iterations_count: int,
    steps_count: int,
    patch_status: str,
    matched_patch_categories: list[str],
) -> None:
    st.caption("SELECTED RUN")
    title_col, action_col = st.columns([0.72, 0.28], vertical_alignment="center")

    with title_col:
        st.subheader(format_task_name(task_id))
        st.caption(task_id)
    with action_col:
        if bug_report_url:
            st.link_button("Open bug report", bug_report_url, width="stretch")
        if pull_request_url:
            st.link_button("Open solving pull request", pull_request_url, width="stretch")

    count_label = "Iterations" if graph_mode == "Iteration" else "Steps"
    count_value = iterations_count if graph_mode == "Iteration" else steps_count
    metric_cols = st.columns(3)
    metric_cols[0].metric("Graph mode", graph_mode)
    metric_cols[1].metric(count_label, count_value)
    metric_cols[2].metric("Patch result", format_patch_status_label(patch_status))

    if matched_patch_categories:
        st.caption("Patch result categories")
        with st.container(horizontal=True):
            for category in matched_patch_categories:
                st.badge(category, color=patch_category_badge_color(category))


def render_graph_guide(graph_mode: str) -> None:
    if graph_mode == "Detailed":
        st.markdown(
            """
### How to read this graph

Detailed mode shows one `T -> A -> R` triplet per step.
Read the graph left to right across iterations, then click any node to inspect
that step and its attached relations.
"""
        )
        return

    st.markdown(
        """
### How to read this graph

Iteration mode shows one node per source iteration, labeled like `I7` and
colored by action category.
Clicking a node opens the iteration content and its cross-iteration relations.
"""
    )


def render_relationship_metrics(
    static_relation_records: list[StaticRelationRecord],
    *,
    embedded: bool = False,
) -> None:
    if embedded:
        st.caption("Relation totals for the selected run.")
    else:
        st.markdown("---")
        st.header("Relationship Metrics")

    if not static_relation_records:
        st.write("No relation data available for this task.")
        return

    relation_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}

    for edge in static_relation_records:
        relation_counts[edge["relation"]] = relation_counts.get(edge["relation"], 0) + 1
        family_counts[edge["family"]] = family_counts.get(edge["family"], 0) + 1

    total = sum(relation_counts.values())
    st.metric("Total labeled relations", total)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**By relationship**")
        for relation, count in sorted(
            relation_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            st.write(f"- {relation}: {count} ({count / total:.1%})")

    with col_b:
        st.markdown("**By edge family**")
        for family, count in sorted(
            family_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            st.write(f"- {family}: {count}")


def _render_patch_summary(view: ViewContext, controls: SidebarControls) -> None:
    with st.container(border=True):
        render_patch_overview(
            task_id=view["task_id"],
            bug_report_url=view["bug_report_url"],
            pull_request_url=view["pull_request_url"],
            graph_mode=controls.graph_mode,
            iterations_count=len(view["iterations"]),
            steps_count=len(view["steps"]),
            patch_status=view["patch_status"],
            matched_patch_categories=view["matched_patch_categories"],
        )


def _render_analysis_support_tabs(view: ViewContext, controls: SidebarControls) -> None:
    support_tabs = st.tabs(["Guide", "Legend", "Relationship Metrics"])
    with support_tabs[0]:
        render_graph_guide(controls.graph_mode)
    with support_tabs[1]:
        render_shared_legend()
    with support_tabs[2]:
        render_relationship_metrics(view["static_relation_records"], embedded=True)


def _open_inspector_route() -> None:
    st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_INSPECTOR
    st.session_state[APP_ROUTE_STATE_KEY] = ROUTE_INSPECTOR
    st.session_state[INSPECTOR_SCROLL_TOP_STATE_KEY] = True
    st.rerun()


def _render_missing_inspector_target() -> None:
    with st.container(border=True):
        st.subheader("No inspector target selected")
        st.write("Open a run in Analysis and select a graph node to inspect raw evidence.")
        if st.button("Open analysis", type="primary"):
            st.session_state[APP_ROUTE_STATE_KEY] = ROUTE_ANALYSIS
            st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
            st.session_state.pop(DETAIL_NODE_STATE_KEY, None)
            st.rerun()


def render_inspector_route(
    *,
    task_files: list[str],
    detail_node_id: str | None,
) -> None:
    filename = st.session_state.get(DETAIL_FILENAME_STATE_KEY)
    controls = st.session_state.get(DETAIL_CONTROLS_STATE_KEY)

    if (
        not filename
        or filename not in task_files
        or not isinstance(controls, SidebarControls)
        or not detail_node_id
    ):
        _render_missing_inspector_target()
        return

    try:
        view = build_view_context(filename, controls)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    if detail_node_id not in view["available_node_ids"]:
        st.session_state.pop(DETAIL_NODE_STATE_KEY, None)
        st.session_state[APP_ROUTE_STATE_KEY] = ROUTE_ANALYSIS
        st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
        st.rerun()

    render_inspector(
        selected=detail_node_id,
        controls=controls,
        cat_map=view["cat_map"],
        log_data=view["log_data"],
        edge_records=view["edge_records"],
        iterations=view["iterations"],
        step_iteration=view["step_iteration"],
        standalone=True,
    )


def render_analysis_route(
    *,
    task_files: list[str],
    selected_filename: str | None,
    detail_page: str,
    detail_node_id: str | None,
) -> None:
    st.markdown("### Analysis")
    saved_controls = st.session_state.get(DETAIL_CONTROLS_STATE_KEY)
    pending_filename = st.session_state.pop(PENDING_ANALYSIS_FILENAME_STATE_KEY, None)
    default_filename = pending_filename or selected_filename
    filename, controls = render_sidebar_controls(
        task_files,
        default_filename=default_filename,
        default_controls=saved_controls if isinstance(saved_controls, SidebarControls) else None,
        sync_default_filename=pending_filename is not None,
    )
    st.session_state[DETAIL_FILENAME_STATE_KEY] = filename
    st.session_state[DETAIL_CONTROLS_STATE_KEY] = controls

    try:
        view = build_view_context(filename, controls)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    _render_patch_summary(view, controls)

    if SHOW_DERIVED_ITERATION_CONTEXT and controls.graph_mode == "Iteration":
        with st.expander("Iteration Context", expanded=True):
            render_iteration_context_panel(view["iterations"], show_heading=False)

    if not controls.inspector_separate_page and detail_page == DETAIL_PAGE_INSPECTOR:
        st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
        detail_page = DETAIL_PAGE_GRAPH

    if detail_node_id not in view["available_node_ids"]:
        st.session_state.pop(DETAIL_NODE_STATE_KEY, None)
        if detail_page == DETAIL_PAGE_INSPECTOR:
            st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
            detail_page = DETAIL_PAGE_GRAPH
        detail_node_id = None

    st.markdown("### Relationship Graph")
    config = Config(width="100%", height=560, directed=True, physics=False)
    with st.container(border=True):
        selected = agraph(nodes=view["nodes"], edges=view["edges"], config=config)

    selected_node_id = str(selected) if selected else detail_node_id
    if selected:
        st.session_state[DETAIL_NODE_STATE_KEY] = str(selected)

    if controls.inspector_separate_page and selected:
        _open_inspector_route()

    if controls.inspector_separate_page:
        st.markdown("---")
        st.caption("Click a node to open its inspector on a separate page.")
    else:
        open_full_inspector = render_inspector(
            selected=selected_node_id,
            controls=controls,
            cat_map=view["cat_map"],
            log_data=view["log_data"],
            edge_records=view["edge_records"],
            iterations=view["iterations"],
            step_iteration=view["step_iteration"],
            show_full_inspector_button=True,
        )
        if open_full_inspector:
            _open_inspector_route()

    _render_analysis_support_tabs(view, controls)
