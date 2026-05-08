"""Small shared widgets for the relationship labeling screens."""

from __future__ import annotations

import streamlit as st

from traceview_app.constants import (
    ACTION_LABEL_OPTIONS,
    RELATION_LABEL_OPTIONS,
    RELATION_LABEL_OPTIONS_BY_FAMILY,
)

ACTION_LABEL_DESCRIPTIONS = {
    "Unlabeled": "No action category has been selected for this iteration yet.",
    "Explore": "Broadly inspect the task, repository, environment, or available context.",
    "Locate": "Identify the specific file, symbol, function, or code area to change.",
    "Search": "Run a targeted search for text, references, examples, or related behavior.",
    "Reproduce": "Run commands or checks to observe, reproduce, or isolate the problem.",
    "Generate fix": "Create or edit code intended to solve the task.",
    "Run tests": "Run tests, linters, or validation commands after a change.",
    "Refactor": "Reorganize or simplify code without changing intended behavior.",
    "Explain": "Reason, summarize, or plan without directly changing or validating code.",
}

LABEL_DESCRIPTIONS = {
    "Unlabeled": "No decision has been made for this relationship yet.",
    "No influence": "The source does not materially affect the target.",
    "Alignment": "The action correctly follows or implements the thought.",
    "Follow-up": "The target continues the same line of work from the source.",
    "Refinement": "The target narrows, corrects, or improves on the source.",
    "Informative": "The result gives useful information for the target action.",
    "Triggering": "The result directly prompts the target action.",
    "Redundancy": "The target repeats prior reasoning without meaningful new progress.",
    "Repetition": "The target repeats a similar action without useful new information.",
    "Misalignment": "The action does not match or serve the source thought.",
    "Misinterpretation": "The target draws an incorrect conclusion from the source result.",
    "Contradiction": "The target conflicts with information or reasoning in the source.",
    "Divergence": "The target shifts away from the prior goal without clear rationale.",
}

_LABEL_FAMILY_NAMES = {
    "thought_action": "Thought -> Action",
    "thought_thought": "Thought -> Thought",
    "action_action": "Action -> Action",
    "result_thought": "Result -> Thought",
    "result_action": "Result -> Action",
}


def _families_for_label(label: str) -> str:
    if label == "Unlabeled":
        return "All families"
    families = [
        _LABEL_FAMILY_NAMES.get(family, family)
        for family, options in RELATION_LABEL_OPTIONS_BY_FAMILY.items()
        if label in options
    ]
    return ", ".join(families)


def render_labeling_header(eyebrow: str, title: str, meta: str | None = None) -> None:
    st.caption(eyebrow)
    st.subheader(title)
    if meta:
        st.caption(meta)


def render_labeling_notice(message: str) -> None:
    st.success(message)


def render_action_label_legend() -> None:
    rows = [
        {
            "Label": label,
            "Meaning": ACTION_LABEL_DESCRIPTIONS[label],
        }
        for label in ("Unlabeled", *ACTION_LABEL_OPTIONS)
    ]

    st.markdown("#### Action Label Legend")
    st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        column_config={
            "Meaning": st.column_config.TextColumn(
                "Meaning",
                width="large",
            ),
        },
    )


def render_relationship_label_legend() -> None:
    rows = [
        {
            "Label": label,
            "Meaning": LABEL_DESCRIPTIONS[label],
            "Available in": _families_for_label(label),
        }
        for label in ("Unlabeled", *RELATION_LABEL_OPTIONS)
    ]

    st.markdown("#### Relationship Label Legend")
    st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        column_config={
            "Meaning": st.column_config.TextColumn(
                "Meaning",
                width="large",
            ),
            "Available in": st.column_config.TextColumn(
                "Available in",
                width="large",
            ),
        },
    )


def render_parser_warnings(errors: list[str], *, expanded: bool = False) -> None:
    if not errors:
        return

    with st.expander(f"Parser warnings ({len(errors)})", expanded=expanded):
        for error in errors[:25]:
            st.warning(error)
        if len(errors) > 25:
            st.caption(f"{len(errors) - 25} additional warnings hidden.")
