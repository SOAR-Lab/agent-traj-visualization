"""Second viewer prototype for trajectory timelines."""

import streamlit as st
import json
from pathlib import Path
from streamlit_agraph import agraph, Node, Edge, Config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_DATA_DIR = PROJECT_ROOT / "data" / "json"
GRAPH_PATH = JSON_DATA_DIR / "agraph_graph.json"

st.set_page_config(layout="wide")
st.title("Thought Trace Timeline")

# Load Graph
@st.cache_data
def load_graph():
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))

graph = load_graph()

# Controls
st.sidebar.header("Display Options")

show_only_failures = st.sidebar.checkbox("Show Only Failed Results", False)
collapse_success = st.sidebar.checkbox("Hide Successful Results", False)

# Build Clean Timeline Layout
nodes = []
edges = []

STEP_SPACING = 120

LANE_Y = {
    "thought": 0,
    "action": 100,
    "result": 200
}

filtered_nodes = graph["nodes"]

if show_only_failures:
    failed_steps = {
        n["step_index"]
        for n in graph["nodes"]
        if n["type"] == "result" and n.get("success") is False
    }
    filtered_nodes = [
        n for n in graph["nodes"]
        if n["step_index"] in failed_steps
    ]

for n in filtered_nodes:

    # Optional collapse logic
    if collapse_success and n["type"] == "result" and n.get("success") is True:
        continue

    color = "#cccccc"

    if n["type"] == "thought":
        color = "#4C78A8"

    elif n["type"] == "action":
        color = "#F58518"

    elif n["type"] == "result":
        color = "#E45756" if n.get("success") is False else "#54A24B"

    nodes.append(
        Node(
            id=n["id"],
            label="",  # NO LABELS (prevents clutter)
            size=14,
            color=color,
            x=n["step_index"] * STEP_SPACING,
            y=LANE_Y[n["type"]]
        )
    )

# Edges (light grey except failure)
for e in graph["edges"]:

    if collapse_success and e.get("success") is True:
        continue

    edges.append(
        Edge(
            source=e["source"],
            target=e["target"],
            color="#E45756" if e.get("success") is False else "#bbbbbb"
        )
    )

config = Config(
    width="100%",
    height=450,
    directed=True,
    physics=False
)

selected_node_id = agraph(nodes=nodes, edges=edges, config=config)

# Detail Panel
if selected_node_id:

    selected = next(
        n for n in graph["nodes"]
        if n["id"] == selected_node_id
    )

    st.markdown("---")
    st.header(f"Step {selected['step_index']} — {selected['type'].upper()}")

    if selected["type"] == "result":
        st.subheader("Success")
        st.write(selected.get("success", True))

    st.subheader("Full Content")
    st.code(selected.get("full_text"))

# Metrics
st.markdown("---")
st.header("Trace Metrics")

thoughts = [n for n in graph["nodes"] if n["type"] == "thought"]
actions = [n for n in graph["nodes"] if n["type"] == "action"]
results = [n for n in graph["nodes"] if n["type"] == "result"]
failures = [n for n in results if n.get("success") is False]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Steps", len(thoughts))
col2.metric("Actions", len(actions))
col3.metric("Results", len(results))
col4.metric("Failures", len(failures))

if results:
    st.metric("Failure Rate", f"{len(failures)/len(results)*100:.2f}%")

# Legend
st.markdown("---")
st.header("Legend")

st.markdown("🔵 Thought")
st.markdown("🟠 Action")
st.markdown("🟢 Result (Success)")
st.markdown("🔴 Result (Failure)")
