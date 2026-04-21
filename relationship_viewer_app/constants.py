"""Shared constants and paths for the relationship viewer."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_DATA_DIR = PROJECT_ROOT / "data" / "json"
ROOT = PROJECT_ROOT / "autocoderover_csv"
LOGS_DIR = PROJECT_ROOT / "reconstructed_autocoderover"
RESULTS_PATH = JSON_DATA_DIR / "results.json"

ACTIONS_CATEGORIES_FOLDER = "actions_categories"
ACTIONS_CATEGORIES_ITER_COL = "iteration"
ACTIONS_CATEGORIES_CAT_COL = "category"
REL_LABEL_COL = "label"

REL_SPECS = {
    "thought_action": {"src": "T", "dst": "A", "offset": 0, "default_on": True},
    "thought_thought": {"src": "T", "dst": "T", "offset": 1, "default_on": True},
    "action_action": {"src": "A", "dst": "A", "offset": 1, "default_on": True},
    "result_thought": {"src": "R", "dst": "T", "offset": 1, "default_on": True},
    "result_action": {"src": "R", "dst": "A", "offset": 1, "default_on": True},
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
