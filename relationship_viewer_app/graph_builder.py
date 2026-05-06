"""Graph construction helpers for the relationship viewer."""

from __future__ import annotations

import pandas as pd
from streamlit_agraph import Edge, Node

from relationship_viewer_app.constants import (
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
    THOUGHT_COLOR,
)
from relationship_viewer_app.viewer_data import category_color, normalize_rel, shorten
from relationship_viewer_app.models import (
    EdgeRecord,
    IterationEdgeRecord,
    IterationRecord,
    SidebarControls,
    StaticRelationRecord,
)
from relationship_viewer_app.node_ids import (
    ACTION_NODE_KIND,
    RESULT_NODE_KIND,
    THOUGHT_NODE_KIND,
    iteration_node_id,
    step_node_id,
)


def final_result_node_style(patch_status: str, base_size: int) -> tuple[str, str, int]:
    if patch_status == "RESOLVED":
        return "#2E7D32", "PASS", base_size + 10
    return "#C62828", "FAIL", base_size + 10


def build_iterations(cat_df: pd.DataFrame) -> list[IterationRecord]:
    iterations: list[IterationRecord] = []
    if cat_df.empty:
        return iterations

    rows = cat_df.sort_values(ACTIONS_CATEGORIES_ITER_COL).reset_index(drop=True)
    current_category = None
    current_steps: list[int] = []

    for _, row in rows.iterrows():
        step_index = int(row[ACTIONS_CATEGORIES_ITER_COL])
        category = str(row[ACTIONS_CATEGORIES_CAT_COL])

        if current_category is None:
            current_category = category
            current_steps = [step_index]
        elif category == current_category:
            current_steps.append(step_index)
        else:
            iterations.append(
                {
                    "iteration_id": len(iterations),
                    "category": current_category,
                    "start_step": current_steps[0],
                    "end_step": current_steps[-1],
                    "steps": current_steps[:],
                }
            )
            current_category = category
            current_steps = [step_index]

    if current_steps:
        iterations.append(
            {
                "iteration_id": len(iterations),
                "category": current_category,
                "start_step": current_steps[0],
                "end_step": current_steps[-1],
                "steps": current_steps[:],
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

        if controls.show_structural_ar and not controls.filters_active:
            for step_index in steps:
                edge_color = "#D0D0D0"
                if step_index == max_iter:
                    edge_color, _, _ = final_result_node_style(
                        patch_status,
                        controls.node_size,
                    )
                edges.append(
                    Edge(
                        source=step_node_id(ACTION_NODE_KIND, step_index),
                        target=step_node_id(RESULT_NODE_KIND, step_index),
                        color=edge_color,
                        label="",
                    )
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
            if context_label:
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
                        color="#D0D0D0",
                        label="",
                    )
                )

    return nodes, edges
