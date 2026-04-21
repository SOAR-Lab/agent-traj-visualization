"""Application entrypoint for the relationship viewer."""

from pathlib import Path

import streamlit as st
from streamlit_agraph import Config, agraph

from relationship_viewer_app.constants import (
    ACTIONS_CATEGORIES_CAT_COL,
    ACTIONS_CATEGORIES_FOLDER,
    ACTIONS_CATEGORIES_ITER_COL,
    REL_SPECS,
    RESULTS_PATH,
    ROOT,
)
from relationship_viewer_app.data import (
    bug_report_url_from_filename,
    corresponding_log_path,
    derive_primary_patch_status,
    get_patch_categories,
    list_task_files,
    load_categories,
    load_relation_labels,
    load_results,
    parse_reconstructed_log,
)
from relationship_viewer_app.graph import (
    build_edge_records,
    build_graph_elements,
    build_iterations,
    collect_static_relation_records,
    step_to_iteration_map,
)
from relationship_viewer_app.models import SidebarControls
from relationship_viewer_app.ui import (
    hide_sidebar_chrome,
    render_graph_guide,
    render_inspector,
    render_inspector_page_header,
    render_patch_overview,
    render_relationship_metrics,
    render_sidebar_controls,
    render_shared_legend,
)

DETAIL_PAGE_STATE_KEY = "relationship_viewer_page"
DETAIL_NODE_STATE_KEY = "relationship_viewer_selected_node"
DETAIL_FILENAME_STATE_KEY = "relationship_viewer_filename"
DETAIL_CONTROLS_STATE_KEY = "relationship_viewer_controls"


def _build_view_context(filename: str, controls: SidebarControls) -> dict:
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

    results_data = load_results(RESULTS_PATH)
    task_id = Path(filename).stem
    matched_patch_categories = get_patch_categories(task_id, results_data)
    patch_status = derive_primary_patch_status(matched_patch_categories)
    bug_url = bug_report_url_from_filename(filename)

    relation_frames = {
        family: load_relation_labels(family, filename)
        for family in REL_SPECS
    }
    static_relation_records = collect_static_relation_records(relation_frames)
    edge_records = build_edge_records(relation_frames, max_iter, controls)
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
        "bug_url": bug_url,
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


def main() -> None:
    st.set_page_config(layout="wide")

    if not ROOT.exists():
        st.error(f"Folder not found: {ROOT.resolve()}")
        st.stop()

    task_files = list_task_files()
    if not task_files:
        st.error(f"No files found in {ROOT / ACTIONS_CATEGORIES_FOLDER}")
        st.stop()

    detail_page = st.session_state.get(DETAIL_PAGE_STATE_KEY, "graph")
    detail_node_id = st.session_state.get(DETAIL_NODE_STATE_KEY)

    if detail_page == "inspector":
        filename = st.session_state.get(DETAIL_FILENAME_STATE_KEY)
        controls = st.session_state.get(DETAIL_CONTROLS_STATE_KEY)

        if (
                not filename
                or filename not in task_files
                or not isinstance(controls, SidebarControls)
                or not controls.inspector_separate_page
                or not detail_node_id
        ):
            st.session_state[DETAIL_PAGE_STATE_KEY] = "graph"
            st.session_state.pop(DETAIL_NODE_STATE_KEY, None)
            st.rerun()

        try:
            view = _build_view_context(filename, controls)
        except Exception as exc:
            st.error(str(exc))
            st.stop()

        if detail_node_id not in view["available_node_ids"]:
            st.session_state[DETAIL_PAGE_STATE_KEY] = "graph"
            st.session_state.pop(DETAIL_NODE_STATE_KEY, None)
            st.rerun()

        hide_sidebar_chrome()
        if render_inspector_page_header(
                task_id=view["task_id"],
        ):
            st.session_state[DETAIL_PAGE_STATE_KEY] = "graph"
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
        return

    st.title("Relationship Viewer")
    filename, controls = render_sidebar_controls(task_files)
    st.session_state[DETAIL_FILENAME_STATE_KEY] = filename
    st.session_state[DETAIL_CONTROLS_STATE_KEY] = controls

    try:
        view = _build_view_context(filename, controls)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    render_patch_overview(
        task_id=view["task_id"],
        bug_url=view["bug_url"],
        graph_mode=controls.graph_mode,
        iterations_count=len(view["iterations"]),
        steps_count=len(view["steps"]),
        patch_status=view["patch_status"],
        matched_patch_categories=view["matched_patch_categories"],
    )
    render_shared_legend()
    render_graph_guide(controls.graph_mode)

    if not controls.inspector_separate_page and detail_page == "inspector":
        st.session_state[DETAIL_PAGE_STATE_KEY] = "graph"
        detail_page = "graph"

    if detail_node_id not in view["available_node_ids"]:
        st.session_state.pop(DETAIL_NODE_STATE_KEY, None)
        if detail_page == "inspector":
            st.session_state[DETAIL_PAGE_STATE_KEY] = "graph"
            detail_page = "graph"
        detail_node_id = None

    config = Config(width="100%", height=560, directed=True, physics=False)
    with st.container(border=True):
        selected = agraph(nodes=view["nodes"], edges=view["edges"], config=config)

    if controls.inspector_separate_page and selected:
        st.session_state[DETAIL_NODE_STATE_KEY] = str(selected)
        st.session_state[DETAIL_PAGE_STATE_KEY] = "inspector"
        st.rerun()

    if controls.inspector_separate_page:
        st.markdown("---")
        st.caption("Click a node to open its inspector on a separate page.")
    else:
        render_inspector(
            selected=selected,
            controls=controls,
            cat_map=view["cat_map"],
            log_data=view["log_data"],
            edge_records=view["edge_records"],
            iterations=view["iterations"],
            step_iteration=view["step_iteration"],
        )

    render_relationship_metrics(view["static_relation_records"])
