"""Small shared widgets for the relationship labeling screens."""

from __future__ import annotations

import streamlit as st


def render_labeling_header(eyebrow: str, title: str, meta: str | None = None) -> None:
    st.caption(eyebrow)
    st.subheader(title)
    if meta:
        st.caption(meta)


def render_labeling_notice(message: str) -> None:
    st.success(message)


def render_parser_warnings(errors: list[str], *, expanded: bool = False) -> None:
    if not errors:
        return

    with st.expander(f"Parser warnings ({len(errors)})", expanded=expanded):
        for error in errors[:25]:
            st.warning(error)
        if len(errors) > 25:
            st.caption(f"{len(errors) - 25} additional warnings hidden.")
