"""Shared UI chrome, controls, and public UI exports."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from relationship_viewer_app.constants import (
    CATEGORY_COLOR,
    EDGE_FAMILY_OPTIONS,
    STRUCTURAL_EDGE_OPTIONS,
)
from relationship_viewer_app.inspector_ui import render_inspector
from relationship_viewer_app.iteration_ui import render_iteration_context_panel
from relationship_viewer_app.models import SidebarControls
from relationship_viewer_app.overview_ui import OVERVIEW_SELECTED_FILE_KEY, render_overview_page
from relationship_viewer_app.ui_common import format_task_name

INSPECTOR_PAGE_TOGGLE_KEY = "relationship_viewer_inspector_separate_page"
INSPECTOR_PAGE_TOGGLE_QUERY_KEY = "inspector_page"
TASK_FILE_SELECT_STATE_KEY = "relationship_viewer_task_file_select"


def render_app_header(
    *,
    current_route: str,
    selected_task_id: str | None = None,
) -> str:
    with st.container(horizontal=True, vertical_alignment="center"):
        with st.container():
            st.title("Inspector" if current_route == "Inspector" else "Relationship Viewer")
            if current_route == "Inspector" and selected_task_id:
                st.caption(selected_task_id)
        st.space("stretch")
        if st.button(
            "Overview",
            type="primary" if current_route == "Overview" else "secondary",
            key="nav_overview",
        ):
            return "Overview"
        if st.button(
            "Analysis",
            type="primary" if current_route == "Analysis" else "secondary",
            key="nav_analysis",
        ):
            return "Analysis"

    st.divider()
    return current_route


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
        ("Structural", "#D0D0D0"),
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


def hide_sidebar_chrome() -> None:
    st.markdown(
        """
<style>
section[data-testid="stSidebar"] {
    display: none !important;
}
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}
[data-testid="collapsedControl"] {
    display: none !important;
}
button[kind="header"][aria-label="Open sidebar"] {
    display: none !important;
}
button[kind="header"][aria-label="Close sidebar"] {
    display: none !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def scroll_page_to_top() -> None:
    components.html(
        """
<script>
const scrollTop = () => {
  const doc = window.parent.document;
  window.parent.scrollTo(0, 0);
  [
    doc.scrollingElement,
    doc.documentElement,
    doc.body,
    doc.querySelector('[data-testid="stAppViewContainer"]'),
    doc.querySelector('[data-testid="stMain"]'),
    doc.querySelector('.stMain')
  ].filter(Boolean).forEach((el) => {
    el.scrollTop = 0;
    if (el.scrollTo) el.scrollTo(0, 0);
  });
};
setTimeout(scrollTop, 0);
setTimeout(scrollTop, 150);
setTimeout(scrollTop, 400);
</script>
        """,
        height=0,
    )


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


def _query_param_to_bool(value: object) -> bool:
    if isinstance(value, list):
        value = value[-1] if value else None
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_inspector_page_preference() -> bool:
    if INSPECTOR_PAGE_TOGGLE_KEY in st.session_state:
        return bool(st.session_state[INSPECTOR_PAGE_TOGGLE_KEY])
    return _query_param_to_bool(st.query_params.get(INSPECTOR_PAGE_TOGGLE_QUERY_KEY))


def set_inspector_page_preference(value: bool) -> None:
    st.session_state[INSPECTOR_PAGE_TOGGLE_KEY] = value
    if value:
        st.query_params[INSPECTOR_PAGE_TOGGLE_QUERY_KEY] = "1"
        return
    if INSPECTOR_PAGE_TOGGLE_QUERY_KEY in st.query_params:
        del st.query_params[INSPECTOR_PAGE_TOGGLE_QUERY_KEY]


def render_sidebar_controls(
    task_files: list[str],
    default_filename: str | None = None,
    default_controls: SidebarControls | None = None,
    sync_default_filename: bool = False,
) -> tuple[str, SidebarControls]:
    st.sidebar.header("Dataset")
    if sync_default_filename and default_filename in task_files:
        st.session_state[TASK_FILE_SELECT_STATE_KEY] = default_filename
    elif st.session_state.get(TASK_FILE_SELECT_STATE_KEY) not in task_files:
        st.session_state[TASK_FILE_SELECT_STATE_KEY] = (
            default_filename if default_filename in task_files else task_files[0]
        )
    filename = st.sidebar.selectbox(
        "Task file",
        task_files,
        key=TASK_FILE_SELECT_STATE_KEY,
    )

    graph_mode_options = ["Detailed", "Iteration"]
    default_graph_mode = (
        default_controls.graph_mode
        if default_controls and default_controls.graph_mode in graph_mode_options
        else "Detailed"
    )
    graph_mode = st.sidebar.radio(
        "Graph mode",
        graph_mode_options,
        index=graph_mode_options.index(default_graph_mode),
        horizontal=True,
    )
    inspector_page_preference = (
        default_controls.inspector_separate_page
        if default_controls
        else get_inspector_page_preference()
    )

    inspector_separate_page = st.sidebar.toggle(
        "Open inspector on separate page",
        value=inspector_page_preference,
    )
    if inspector_separate_page != inspector_page_preference:
        set_inspector_page_preference(inspector_separate_page)
    else:
        st.session_state[INSPECTOR_PAGE_TOGGLE_KEY] = inspector_separate_page

    selected_edge_families = tuple(EDGE_FAMILY_OPTIONS)
    selected_structural_edges = tuple(STRUCTURAL_EDGE_OPTIONS)

    if graph_mode == "Detailed":
        st.sidebar.header("Relational Edges")
        default_edge_families = list(EDGE_FAMILY_OPTIONS)
        if default_controls:
            default_edge_families = [
                option
                for option in default_controls.selected_edge_families
                if option in EDGE_FAMILY_OPTIONS
            ]
        selected_edge_families = tuple(
            st.sidebar.pills(
                "Edge families",
                EDGE_FAMILY_OPTIONS,
                selection_mode="multi",
                default=default_edge_families,
                label_visibility="collapsed",
            )
        )

        default_structural_edges = list(STRUCTURAL_EDGE_OPTIONS)
        if default_controls:
            default_structural_edges = [
                option
                for option in default_controls.selected_structural_edges
                if option in STRUCTURAL_EDGE_OPTIONS
            ]
        selected_structural_edges = tuple(
            st.sidebar.pills(
                "Structural edges",
                STRUCTURAL_EDGE_OPTIONS,
                selection_mode="multi",
                default=default_structural_edges,
                label_visibility="collapsed",
            )
        )

    st.sidebar.header("Filters")
    show_only_bad = st.sidebar.checkbox(
        "Only bad relations",
        default_controls.show_only_bad if default_controls else False,
    )
    show_only_loopish = st.sidebar.checkbox(
        "Only loop-ish relations",
        default_controls.show_only_loopish if default_controls else False,
    )
    show_only_no_influence = st.sidebar.checkbox(
        "Only no-influence relations",
        default_controls.show_only_no_influence if default_controls else False,
    )

    st.sidebar.header("Layout")
    step_spacing = st.sidebar.slider(
        "Step spacing",
        120,
        320,
        default_controls.step_spacing if default_controls else 190,
        10,
    )
    lane_gap = st.sidebar.slider(
        "Lane gap",
        90,
        180,
        default_controls.lane_gap if default_controls else 120,
        10,
    )
    node_size = st.sidebar.slider(
        "Node size",
        18,
        46,
        default_controls.node_size if default_controls else 26,
        1,
    )
    label_max_len = st.sidebar.slider(
        "Max action label length",
        8,
        24,
        default_controls.label_max_len if default_controls else 14,
        1,
    )
    show_edge_labels = st.sidebar.checkbox(
        "Show edge labels",
        default_controls.show_edge_labels if default_controls else True,
    )

    controls = SidebarControls(
        graph_mode=graph_mode,
        inspector_separate_page=inspector_separate_page,
        selected_edge_families=selected_edge_families,
        selected_structural_edges=selected_structural_edges,
        show_only_bad=show_only_bad,
        show_only_loopish=show_only_loopish,
        show_only_no_influence=show_only_no_influence,
        step_spacing=step_spacing,
        lane_gap=lane_gap,
        node_size=node_size,
        label_max_len=label_max_len,
        show_edge_labels=show_edge_labels,
    )
    return filename, controls


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
Read the graph left to right across iterations, then click any node to inspect that step and its attached relations.
"""
        )
        return

    st.markdown(
        """
### How to read this graph

Iteration mode collapses consecutive detailed steps with the same action category into iteration nodes like `I7`.
Clicking a node opens the grouped content and cross-iteration relations.
"""
    )


def render_relationship_metrics(
    static_relation_records: list[dict],
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
