"""Analysis sidebar controls."""

from __future__ import annotations

import streamlit as st

from traceview_app.shared.constants import (
    EDGE_FAMILY_OPTIONS,
    STRUCTURAL_EDGE_OPTIONS,
    TASK_FILE_SELECT_STATE_KEY,
)
from traceview_app.shared.models import SidebarControls

INSPECTOR_PAGE_TOGGLE_KEY = "traceview_inspector_separate_page"
INSPECTOR_PAGE_TOGGLE_QUERY_KEY = "inspector_page"
ACTION_ACTION_EDGE_FAMILY = "Action → Action"
DEFAULT_DETAILED_EDGE_FAMILIES = tuple(
    option for option in EDGE_FAMILY_OPTIONS if option != ACTION_ACTION_EDGE_FAMILY
)


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

    graph_mode_options = ["Iteration", "Detailed"]
    default_graph_mode = (
        default_controls.graph_mode
        if default_controls and default_controls.graph_mode in graph_mode_options
        else "Iteration"
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
        default_edge_families = list(DEFAULT_DETAILED_EDGE_FAMILIES)
        if default_controls and default_controls.graph_mode == "Detailed":
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
        if default_controls and default_controls.graph_mode == "Detailed":
            selected_defaults = [
                option
                for option in default_controls.selected_structural_edges
                if option in STRUCTURAL_EDGE_OPTIONS
            ]
            if selected_defaults or not default_controls.selected_structural_edges:
                default_structural_edges = selected_defaults
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
