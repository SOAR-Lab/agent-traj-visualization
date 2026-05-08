"""Helpers for graph node IDs used by the viewer."""

from __future__ import annotations

from dataclasses import dataclass


THOUGHT_NODE_KIND = "T"
ACTION_NODE_KIND = "A"
RESULT_NODE_KIND = "R"
ITERATION_NODE_PREFIX = "IT"


@dataclass(frozen=True)
class StepNodeId:
    kind: str
    step: int


def step_node_id(kind: str, step: int) -> str:
    return f"{kind}_{step}"


def iteration_node_id(iteration_id: int) -> str:
    return f"{ITERATION_NODE_PREFIX}_{iteration_id}"


def parse_step_node_id(node_id: str) -> StepNodeId:
    kind, raw_step = node_id.split("_", 1)
    return StepNodeId(kind=kind, step=int(raw_step))


def parse_iteration_node_id(node_id: str) -> int:
    prefix, raw_iteration = node_id.split("_", 1)
    if prefix != ITERATION_NODE_PREFIX:
        raise ValueError(f"Expected iteration node ID, got {node_id!r}.")
    return int(raw_iteration)


def node_kind_name(kind: str) -> str:
    return {
        THOUGHT_NODE_KIND: "Thought",
        ACTION_NODE_KIND: "Action",
        RESULT_NODE_KIND: "Result",
    }.get(kind, kind)
