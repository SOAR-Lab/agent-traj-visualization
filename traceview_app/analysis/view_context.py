"""Build analysis view data for graph and inspector routes."""

from __future__ import annotations

from pathlib import Path

from traceview_app.analysis.graph_builder import (
    build_edge_records,
    build_graph_elements,
    build_iterations,
    collect_static_relation_records,
    step_to_iteration_map,
)
from traceview_app.analysis.iteration_context import build_iteration_contexts
from traceview_app.overview.data import (
    bug_report_url_from_filename,
    corresponding_log_path,
    derive_primary_patch_status,
    get_patch_categories,
    load_categories,
    load_labeler_export_metadata,
    load_relation_labels,
    load_results,
    parse_reconstructed_log,
    pull_request_url_from_filename,
)
from traceview_app.shared.constants import (
    ACTIONS_CATEGORIES_CAT_COL,
    ACTIONS_CATEGORIES_ITER_COL,
    LABELER_VIEWER_EXPORTS_PATH,
    REL_SPECS,
    RESULTS_PATH,
)
from traceview_app.shared.models import SidebarControls, ViewContext


def build_view_context(filename: str, controls: SidebarControls) -> ViewContext:
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
