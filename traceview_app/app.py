"""Application entrypoint for TraceView."""

from pathlib import Path

import streamlit as st
from streamlit_agraph import Config, agraph

from traceview_app.constants import (
    ACTIONS_CATEGORIES_CAT_COL,
    ACTIONS_CATEGORIES_FOLDER,
    ACTIONS_CATEGORIES_ITER_COL,
    APP_ROUTE_STATE_KEY,
    DETAIL_PAGE_GRAPH,
    DETAIL_PAGE_INSPECTOR,
    DETAIL_FILENAME_STATE_KEY,
    LABELER_VIEWER_EXPORTS_PATH,
    OVERVIEW_SELECTED_FILE_KEY,
    REL_SPECS,
    RESULTS_PATH,
    ROOT,
    ROUTE_ANALYSIS,
    ROUTE_INSPECTOR,
    ROUTE_LABELING,
    ROUTE_OVERVIEW,
)
from traceview_app.iteration_context import build_iteration_contexts
from traceview_app.viewer_data import (
    build_overview_rows,
    bug_report_url_from_filename,
    corresponding_log_path,
    derive_primary_patch_status,
    get_patch_categories,
    list_task_files,
    load_categories,
    load_labeler_export_metadata,
    load_relation_labels,
    load_results,
    parse_reconstructed_log,
    pull_request_url_from_filename,
)
from traceview_app.graph_builder import (
    build_edge_records,
    build_graph_elements,
    build_iterations,
    collect_static_relation_records,
    step_to_iteration_map,
)
from traceview_app.models import SidebarControls, ViewContext
from traceview_app.layout_ui import (
    hide_sidebar_chrome,
    render_app_header,
    render_graph_guide,
    render_inspector,
    render_iteration_context_panel,
    render_labeling_page,
    render_overview_page,
    render_patch_overview,
    render_relationship_metrics,
    render_sidebar_controls,
    render_shared_legend,
    scroll_page_to_top,
)

INSPECTOR_SCROLL_TOP_STATE_KEY = "traceview_inspector_scroll_top"
DETAIL_PAGE_STATE_KEY = "traceview_page"
DETAIL_NODE_STATE_KEY = "traceview_selected_node"
DETAIL_CONTROLS_STATE_KEY = "traceview_controls"
PENDING_ANALYSIS_FILENAME_STATE_KEY = "traceview_pending_analysis_filename"


def _queue_analysis_filename(filename: str, *, clear_stale_node: bool = True) -> None:
    previous_filename = st.session_state.get(DETAIL_FILENAME_STATE_KEY)
    st.session_state[DETAIL_FILENAME_STATE_KEY] = filename
    st.session_state[PENDING_ANALYSIS_FILENAME_STATE_KEY] = filename
    if clear_stale_node and filename != previous_filename:
        st.session_state.pop(DETAIL_NODE_STATE_KEY, None)


def _build_view_context(filename: str, controls: SidebarControls) -> ViewContext:
    labeler_exports = load_labeler_export_metadata(LABELER_VIEWER_EXPORTS_PATH)
    export_meta = labeler_exports.get(filename, {})
    is_labeler_export = bool(export_meta)
    cat_df = load_categories(filename)

    max_iter = int(cat_df[ACTIONS_CATEGORIES_ITER_COL].max())
    steps = list(range(max_iter + 1))
    cat_map = dict(
        zip(
            cat_df[ACTIONS_CATEGORIES_ITER_COL],
            cat_df[ACTIONS_CATEGORIES_CAT_COL],
        )
    )

    iterations = build_iterations(cat_df)
    step_iteration = step_to_iteration_map(iterations)

    log_path = corresponding_log_path(filename)
    log_data = parse_reconstructed_log(log_path)

    task_id = str(export_meta.get("task_id") or Path(filename).stem)
    if is_labeler_export:
        matched_patch_categories = []
        patch_status = "UNKNOWN"
        bug_report_url = None
        pull_request_url = None
    else:
        results_data = load_results(RESULTS_PATH)
        matched_patch_categories = get_patch_categories(task_id, results_data)
        patch_status = derive_primary_patch_status(matched_patch_categories)
        bug_report_url = bug_report_url_from_filename(filename)
        pull_request_url = pull_request_url_from_filename(filename)

    relation_frames = {
        family: load_relation_labels(family, filename)
        for family in REL_SPECS
    }
    static_relation_records = collect_static_relation_records(relation_frames)
    edge_records = build_edge_records(relation_frames, max_iter, controls)
    iterations = build_iteration_contexts(iterations, log_data, edge_records)
    nodes, edges = build_graph_elements(
        steps=steps,
        cat_map=cat_map,
        iterations=iterations,
        step_iteration=step_iteration,
        edge_records=edge_records,
        controls=controls,
        patch_status=patch_status,
        max_iter=max_iter,
    )

    return {
        "task_id": task_id,
        "bug_report_url": bug_report_url,
        "pull_request_url": pull_request_url,
        "steps": steps,
        "cat_map": cat_map,
        "iterations": iterations,
        "step_iteration": step_iteration,
        "log_data": log_data,
        "matched_patch_categories": matched_patch_categories,
        "patch_status": patch_status,
        "static_relation_records": static_relation_records,
        "edge_records": edge_records,
        "nodes": nodes,
        "edges": edges,
        "available_node_ids": {node.id for node in nodes},
    }


def _apply_route_change(
    *,
    selected_route: str,
    previous_route: str,
    task_files: list[str],
) -> None:
    st.session_state[APP_ROUTE_STATE_KEY] = selected_route
    if selected_route == ROUTE_OVERVIEW:
        st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
        st.session_state.pop(DETAIL_NODE_STATE_KEY, None)
    elif selected_route == ROUTE_ANALYSIS:
        overview_filename = st.session_state.get(OVERVIEW_SELECTED_FILE_KEY)
        if previous_route == ROUTE_OVERVIEW and overview_filename in task_files:
            _queue_analysis_filename(overview_filename)
        st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
    elif selected_route == ROUTE_LABELING:
        st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
    st.rerun()


def _apply_current_route_click(route: str) -> None:
    if route in {ROUTE_OVERVIEW, ROUTE_ANALYSIS}:
        st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
        st.session_state.pop(DETAIL_NODE_STATE_KEY, None)
    elif route == ROUTE_LABELING:
        st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
    st.rerun()


def _ensure_dataset_available(task_files: list[str]) -> None:
    if not ROOT.exists():
        st.error(f"Folder not found: {ROOT.resolve()}")
        st.stop()
    if not task_files:
        st.error(f"No files found in {ROOT / ACTIONS_CATEGORIES_FOLDER}")
        st.stop()


def _render_overview_route(task_files: list[str]) -> None:
    try:
        overview_rows = build_overview_rows(tuple(task_files), RESULTS_PATH)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    opened_filename = render_overview_page(overview_rows)
    if opened_filename:
        _queue_analysis_filename(opened_filename)
        st.session_state[APP_ROUTE_STATE_KEY] = ROUTE_ANALYSIS
        st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
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


def _render_inspector_route(
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
        view = _build_view_context(filename, controls)
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


def _render_analysis_route(
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
        view = _build_view_context(filename, controls)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    _render_patch_summary(view, controls)

    if controls.graph_mode == "Iteration":
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


def main() -> None:
    st.set_page_config(page_title="TraceView", layout="wide")

    detail_page = st.session_state.get(DETAIL_PAGE_STATE_KEY, DETAIL_PAGE_GRAPH)
    detail_node_id = st.session_state.get(DETAIL_NODE_STATE_KEY)
    if detail_page == DETAIL_PAGE_INSPECTOR:
        st.session_state[APP_ROUTE_STATE_KEY] = ROUTE_INSPECTOR

    route = st.session_state.get(APP_ROUTE_STATE_KEY, ROUTE_LABELING)
    selected_filename = st.session_state.get(DETAIL_FILENAME_STATE_KEY)
    selected_task_id = Path(selected_filename).stem if selected_filename else None
    task_files = list_task_files() if ROOT.exists() else []

    if route == ROUTE_INSPECTOR:
        hide_sidebar_chrome()

    selected_route, route_button_clicked = render_app_header(
        current_route=route,
        selected_task_id=selected_task_id,
    )
    if route == ROUTE_INSPECTOR and st.session_state.pop(
        INSPECTOR_SCROLL_TOP_STATE_KEY,
        False,
    ):
        scroll_page_to_top()

    if selected_route != route:
        _apply_route_change(
            selected_route=selected_route,
            previous_route=route,
            task_files=task_files,
        )
    if route_button_clicked:
        _apply_current_route_click(route)

    if route == ROUTE_LABELING:
        render_labeling_page()
        return

    _ensure_dataset_available(task_files)

    if route == ROUTE_OVERVIEW:
        _render_overview_route(task_files)
        return

    if route == ROUTE_INSPECTOR:
        _render_inspector_route(
            task_files=task_files,
            detail_node_id=detail_node_id,
        )
        return

    _render_analysis_route(
        task_files=task_files,
        selected_filename=selected_filename,
        detail_page=detail_page,
        detail_node_id=detail_node_id,
    )
