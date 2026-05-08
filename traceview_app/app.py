"""Application entrypoint for TraceView."""

from pathlib import Path

import streamlit as st

from traceview_app.analysis.route import (
    DETAIL_NODE_STATE_KEY,
    DETAIL_PAGE_STATE_KEY,
    INSPECTOR_SCROLL_TOP_STATE_KEY,
    queue_analysis_filename,
    render_analysis_route,
    render_inspector_route,
)
from traceview_app.labeling.router import render_labeling_page
from traceview_app.layout_ui import (
    hide_sidebar_chrome,
    render_app_header,
    scroll_page_to_top,
)
from traceview_app.overview.data import build_overview_rows, list_task_files
from traceview_app.overview.ui import render_overview_page
from traceview_app.shared.constants import (
    ACTIONS_CATEGORIES_FOLDER,
    APP_ROUTE_STATE_KEY,
    DETAIL_FILENAME_STATE_KEY,
    DETAIL_PAGE_GRAPH,
    DETAIL_PAGE_INSPECTOR,
    OVERVIEW_SELECTED_FILE_KEY,
    RESULTS_PATH,
    ROOT,
    ROUTE_ANALYSIS,
    ROUTE_INSPECTOR,
    ROUTE_LABELING,
    ROUTE_OVERVIEW,
)


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
            queue_analysis_filename(overview_filename)
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
        queue_analysis_filename(opened_filename)
        st.session_state[APP_ROUTE_STATE_KEY] = ROUTE_ANALYSIS
        st.session_state[DETAIL_PAGE_STATE_KEY] = DETAIL_PAGE_GRAPH
        st.rerun()


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
        render_inspector_route(
            task_files=task_files,
            detail_node_id=detail_node_id,
        )
        return

    render_analysis_route(
        task_files=task_files,
        selected_filename=selected_filename,
        detail_page=detail_page,
        detail_node_id=detail_node_id,
    )
