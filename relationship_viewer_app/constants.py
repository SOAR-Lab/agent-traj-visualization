"""Shared constants and paths for the relationship viewer."""

from pathlib import Path

from relationship_viewer_app.node_ids import (
    ACTION_NODE_KIND,
    RESULT_NODE_KIND,
    THOUGHT_NODE_KIND,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_DATA_DIR = PROJECT_ROOT / "data" / "json"
ROOT = PROJECT_ROOT / "autocoderover_csv"
LOGS_DIR = PROJECT_ROOT / "reconstructed_autocoderover"
RESULTS_PATH = JSON_DATA_DIR / "results.json"

ROUTE_OVERVIEW = "Overview"
ROUTE_ANALYSIS = "Analysis"
ROUTE_INSPECTOR = "Inspector"
ROUTE_LABELING = "Labeling"

DETAIL_PAGE_GRAPH = "graph"
DETAIL_PAGE_INSPECTOR = "inspector"

LABELER_STAGE_INGEST = "ingest"
LABELER_STAGE_ANNOTATING = "annotating"
LABELER_STAGE_COMPLETE = "complete"
LABELER_STAGE_WORKSPACE = "workspace"

ACTIONS_CATEGORIES_FOLDER = "actions_categories"
ACTIONS_CATEGORIES_ITER_COL = "iteration"
ACTIONS_CATEGORIES_CAT_COL = "category"
REL_LABEL_COL = "label"

REL_SPECS = {
    "thought_action": {
        "src": THOUGHT_NODE_KIND,
        "dst": ACTION_NODE_KIND,
        "offset": 0,
        "default_on": True,
    },
    "thought_thought": {
        "src": THOUGHT_NODE_KIND,
        "dst": THOUGHT_NODE_KIND,
        "offset": 1,
        "default_on": True,
    },
    "action_action": {
        "src": ACTION_NODE_KIND,
        "dst": ACTION_NODE_KIND,
        "offset": 1,
        "default_on": True,
    },
    "result_thought": {
        "src": RESULT_NODE_KIND,
        "dst": THOUGHT_NODE_KIND,
        "offset": 1,
        "default_on": True,
    },
    "result_action": {
        "src": RESULT_NODE_KIND,
        "dst": ACTION_NODE_KIND,
        "offset": 1,
        "default_on": True,
    },
}

REL_COLOR = {
    "Alignment": "#54A24B",
    "Follow-up": "#54A24B",
    "Follow up": "#54A24B",
    "Refinement": "#54A24B",
    "Informative": "#54A24B",
    "Triggering": "#54A24B",
    "No influence": "#9E9E9E",
    "No-influence": "#9E9E9E",
    "Redundancy": "#7F3C8D",
    "Repetition": "#7F3C8D",
    "Misalignment": "#E45756",
    "Misinterpretation": "#E45756",
    "Contradiction": "#E45756",
    "Divergence": "#F58518",
}

RELATION_LABEL_OPTIONS = (
    "No influence",
    "Alignment",
    "Follow-up",
    "Refinement",
    "Informative",
    "Triggering",
    "Redundancy",
    "Repetition",
    "Misalignment",
    "Misinterpretation",
    "Contradiction",
    "Divergence",
)

RELATION_LABEL_OPTIONS_BY_FAMILY = {
    "thought_action": (
        "Alignment",
        "Misalignment",
    ),
    "thought_thought": (
        "Follow-up",
        "Refinement",
        "Redundancy",
        "Divergence",
        "Contradiction",
    ),
    "action_action": (
        "Follow-up",
        "Refinement",
        "Repetition",
        "Divergence",
    ),
    "result_thought": (
        "Follow-up",
        "Refinement",
        "No influence",
        "Misinterpretation",
    ),
    "result_action": (
        "Informative",
        "Triggering",
        "No influence",
    ),
}

DEFAULT_EDGE_COLOR = "#BBBBBB"

CATEGORY_COLOR = {
    "explore": "#4E79A7",
    "locate": "#76B7B2",
    "search": "#59A14F",
    "reproduce": "#EDC948",
    "generate fix": "#F28E2B",
    "run tests": "#E15759",
    "refactor": "#B07AA1",
    "explain": "#9C755F",
}

BAD_RELS = {"Misalignment", "Misinterpretation", "Contradiction"}
LOOPISH_RELS = {"Redundancy", "Repetition"}
NOINF_RELS = {"No influence", "No-influence"}

THOUGHT_COLOR = "#4C78A8"
RESULT_COLOR = "#9E9E9E"

EDGE_FAMILY_OPTIONS = (
    "Thought → Action",
    "Thought → Thought",
    "Action → Action",
    "Result → Thought",
    "Result → Action",
)

STRUCTURAL_EDGE_OPTIONS = (
    "Action → Result (Structural)",
)
