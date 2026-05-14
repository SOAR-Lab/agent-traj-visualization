"""Graph construction helpers for TraceView."""

from __future__ import annotations

import pandas as pd
from streamlit_agraph import Edge, Node

from traceview_app.analysis.iteration_context import SHOW_DERIVED_ITERATION_CONTEXT
from traceview_app.shared.constants import (
    ACTIONS_CATEGORIES_CAT_COL,
    ACTIONS_CATEGORIES_ITER_COL,
    BAD_RELS,
    DEFAULT_EDGE_COLOR,
    LOOPISH_RELS,
    NOINF_RELS,
    REL_COLOR,
    REL_LABEL_COL,
    REL_SPECS,
    RESULT_COLOR,
    STRUCTURAL_EDGE_COLOR,
    THOUGHT_COLOR,
)
from traceview_app.overview.data import category_color, normalize_rel, shorten
from traceview_app.shared.models import (
    EdgeRecord,
    IterationEdgeRecord,
    IterationRecord,
    SidebarControls,
    StaticRelationRecord,
)
from traceview_app.shared.node_ids import (
    ACTION_NODE_KIND,
    RESULT_NODE_KIND,
    THOUGHT_NODE_KIND,
    iteration_node_id,
    step_node_id,
)


def final_result_node_style(patch_status: str, base_size: int) -> tuple[str, str, int]:
    if patch_status == "RESOLVED":
        return "#2E7D32", "PASS", base_size + 10
    if patch_status == "UNKNOWN":
        return "#757575", "UNSCORED", base_size + 10
    return "#C62828", "FAIL", base_size + 10


def build_iterations(cat_df: pd.DataFrame) -> list[IterationRecord]:
    iterations: list[IterationRecord] = []
    if cat_df.empty:
        return iterations

    rows = cat_df.sort_values(ACTIONS_CATEGORIES_ITER_COL).reset_index(drop=True)
    for _, row in rows.iterrows():
        step_index = int(row[ACTIONS_CATEGORIES_ITER_COL])
        category = str(row[ACTIONS_CATEGORIES_CAT_COL])
        iterations.append(
            {
                "iteration_id": len(iterations),
                "category": category,
                "start_step": step_index,
                "end_step": step_index,
                "steps": [step_index],
            }
        )

    return iterations


def step_to_iteration_map(iterations: list[IterationRecord]) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for iteration in iterations:
        for step in iteration["steps"]:
            mapping[step] = iteration["iteration_id"]
    return mapping


def build_iteration_action_edges(
    edge_records: list[EdgeRecord],
    step_iteration: dict[int, int],
) -> list[IterationEdgeRecord]:
    iteration_edges: list[IterationEdgeRecord] = []

    for edge in edge_records:
        if edge["family"] != "action_action":
            continue
        src_iteration = step_iteration.get(edge["src_step"])
        dst_iteration = step_iteration.get(edge["dst_step"])
        if src_iteration is None or dst_iteration is None:
            continue
        if src_iteration == dst_iteration:
            continue
        iteration_edges.append(
            {
                "source": iteration_node_id(src_iteration),
                "target": iteration_node_id(dst_iteration),
                "color": REL_COLOR.get(edge["relation"], DEFAULT_EDGE_COLOR),
                "label": edge["relation"],
                "record": edge,
            }
        )

    return iteration_edges


def collect_static_relation_records(
    relation_frames: dict[str, pd.DataFrame],
) -> list[StaticRelationRecord]:
    records: list[StaticRelationRecord] = []
    for family, frame in relation_frames.items():
        if frame.empty:
            continue
        for _, row in frame.iterrows():
            relation = normalize_rel(row[REL_LABEL_COL])
            if not relation:
                continue
            records.append(
                {
                    "family": family,
                    "relation": relation,
                }
            )
    return records


def relation_passes(rel: str, controls: SidebarControls) -> bool:
    if controls.show_only_bad and rel not in BAD_RELS:
        return False
    if controls.show_only_loopish and rel not in LOOPISH_RELS:
        return False
    if controls.show_only_no_influence and rel not in NOINF_RELS:
        return False
    return True


def build_edge_records(
    relation_frames: dict[str, pd.DataFrame],
    max_iter: int,
    controls: SidebarControls,
) -> list[EdgeRecord]:
    edge_records: list[EdgeRecord] = []

    def collect_relation_edges(family: str) -> None:
        spec = REL_SPECS[family]
        frame = relation_frames[family]
        if frame.empty:
            return

        for index, row in frame.iterrows():
            src_index = index
            dst_index = index + spec["offset"]
            if src_index > max_iter or dst_index > max_iter:
                continue

            relation = normalize_rel(row[REL_LABEL_COL])
            if not relation:
                continue
            if not relation_passes(relation, controls):
                continue

            edge_records.append(
                {
                    "family": family,
                    "source": step_node_id(spec["src"], src_index),
                    "target": step_node_id(spec["dst"], dst_index),
                    "src_step": src_index,
                    "dst_step": dst_index,
                    "relation": relation,
                }
            )

    if controls.show_ta:
        collect_relation_edges("thought_action")
    if controls.show_tt:
        collect_relation_edges("thought_thought")
    if controls.show_aa:
        collect_relation_edges("action_action")
    if controls.show_rt:
        collect_relation_edges("result_thought")
    if controls.show_ra:
        collect_relation_edges("result_action")

    return edge_records


def add_detailed_structural_flow_edges(
    *,
    edges: list[Edge],
    steps: list[int],
    edge_records: list[EdgeRecord],
    controls: SidebarControls,
    patch_status: str,
    max_iter: int,
) -> None:
    if not controls.show_structural_flow or controls.filters_active:
        return

    step_set = set(steps)
    existing_pairs = {
        (record["source"], record["target"])
        for record in edge_records
    }

    def add_edge(source: str, target: str, color: str = STRUCTURAL_EDGE_COLOR) -> None:
        if (source, target) in existing_pairs:
            return
        edges.append(
            Edge(
                source=source,
                target=target,
                color=color,
                label="",
            )
        )
        existing_pairs.add((source, target))

    for step_index in steps:
        add_edge(
            step_node_id(THOUGHT_NODE_KIND, step_index),
            step_node_id(ACTION_NODE_KIND, step_index),
        )

        action_result_color = STRUCTURAL_EDGE_COLOR
        if step_index == max_iter:
            action_result_color, _, _ = final_result_node_style(
                patch_status,
                controls.node_size,
            )
        add_edge(
            step_node_id(ACTION_NODE_KIND, step_index),
            step_node_id(RESULT_NODE_KIND, step_index),
            action_result_color,
        )

        next_step_index = step_index + 1
        if next_step_index in step_set:
            add_edge(
                step_node_id(RESULT_NODE_KIND, step_index),
                step_node_id(THOUGHT_NODE_KIND, next_step_index),
            )


def build_graph_elements(
    *,
    steps: list[int],
    cat_map: dict[int, str],
    iterations: list[IterationRecord],
    step_iteration: dict[int, int],
    edge_records: list[EdgeRecord],
    controls: SidebarControls,
    patch_status: str,
    max_iter: int,
) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    lane_y = {
        THOUGHT_NODE_KIND: 0,
        ACTION_NODE_KIND: controls.lane_gap,
        RESULT_NODE_KIND: controls.lane_gap * 2,
    }

    if controls.graph_mode == "Detailed":
        for step_index in steps:
            category = cat_map.get(step_index, "")
            category_short = shorten(category, controls.label_max_len)

            result_color = RESULT_COLOR
            result_label = f"R{step_index}"
            result_size = controls.node_size

            if step_index == max_iter:
                result_color, outcome_label, result_size = final_result_node_style(
                    patch_status,
                    controls.node_size,
                )
                result_label = f"R{step_index}\n{outcome_label}"

            nodes.append(
                Node(
                    id=step_node_id(THOUGHT_NODE_KIND, step_index),
                    label=f"T{step_index}",
                    size=controls.node_size,
                    color=THOUGHT_COLOR,
                    x=step_index * controls.step_spacing,
                    y=lane_y[THOUGHT_NODE_KIND],
                )
            )
            nodes.append(
                Node(
                    id=step_node_id(ACTION_NODE_KIND, step_index),
                    label=(
                        f"A{step_index}\n{category_short}"
                        if category_short
                        else f"A{step_index}"
                    ),
                    size=controls.node_size,
                    color=category_color(category),
                    x=step_index * controls.step_spacing,
                    y=lane_y[ACTION_NODE_KIND],
                )
            )
            nodes.append(
                Node(
                    id=step_node_id(RESULT_NODE_KIND, step_index),
                    label=result_label,
                    size=result_size,
                    color=result_color,
                    x=step_index * controls.step_spacing,
                    y=lane_y[RESULT_NODE_KIND],
                )
            )

        for record in edge_records:
            edges.append(
                Edge(
                    source=record["source"],
                    target=record["target"],
                    color=REL_COLOR.get(record["relation"], DEFAULT_EDGE_COLOR),
                    label=record["relation"] if controls.show_edge_labels else "",
                )
            )

        add_detailed_structural_flow_edges(
            edges=edges,
            steps=steps,
            edge_records=edge_records,
            controls=controls,
            patch_status=patch_status,
            max_iter=max_iter,
        )

    else:
        for iteration in iterations:
            iteration_id = iteration["iteration_id"]
            category = iteration["category"]
            label_parts = [
                f"I{iteration_id}",
                shorten(category, controls.label_max_len),
            ]
            context_label = iteration.get("context_label", "")
            if SHOW_DERIVED_ITERATION_CONTEXT and context_label:
                label_parts.append(shorten(context_label, controls.label_max_len + 10))
            label = "\n".join(label_parts)
            nodes.append(
                Node(
                    id=iteration_node_id(iteration_id),
                    label=label,
                    size=controls.node_size + 8,
                    color=category_color(category),
                    x=iteration_id * int(controls.step_spacing * 1.2),
                    y=controls.lane_gap,
                )
            )

        iteration_edges = build_iteration_action_edges(edge_records, step_iteration)
        semantic_iteration_pairs = {
            (edge["source"], edge["target"])
            for edge in iteration_edges
        }
        for edge in iteration_edges:
            edges.append(
                Edge(
                    source=edge["source"],
                    target=edge["target"],
                    color=edge["color"],
                    label=edge["label"] if controls.show_edge_labels else "",
                    font={
                        "align": "top",
                        "vadjust": -8,
                        "background": "rgba(255,255,255,0.9)",
                        "strokeWidth": 2,
                        "strokeColor": "#FFFFFF",
                    },
                )
            )

        if not controls.filters_active:
            for iteration_index in range(len(iterations) - 1):
                source = iteration_node_id(iteration_index)
                target = iteration_node_id(iteration_index + 1)
                if (source, target) in semantic_iteration_pairs:
                    continue
                edges.append(
                    Edge(
                        source=source,
                        target=target,
                        color=STRUCTURAL_EDGE_COLOR,
                        label="",
                    )
                )

    return nodes, edges
