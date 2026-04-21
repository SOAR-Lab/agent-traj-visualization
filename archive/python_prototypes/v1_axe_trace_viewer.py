"""Early AXE trace viewer prototype."""

import streamlit as st
import json
from pathlib import Path
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_DATA_DIR = PROJECT_ROOT / "data" / "json"
GRAPH_FILE = JSON_DATA_DIR / "graph_trace.json"
TRACE_FILE = JSON_DATA_DIR / "normalized_trace.json"
CONTEXT_FILE = JSON_DATA_DIR / "file_context.json"

# PAGE SETUP
st.set_page_config(
    page_title="Agent Trace Visualization",
    layout="wide"
)

st.title("Agent Execution Trace Visualization")

# LOAD DATA
@st.cache_data
def load_data():

    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        graph = json.load(f)

    with open(TRACE_FILE, "r", encoding="utf-8") as f:
        trace = json.load(f)

    with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
        context = json.load(f)

    return graph, trace, context


graph, trace, context = load_data()

nodes = graph["nodes"]

# AGENT SWIMLANE MAPPING
LANE_MAP = {
    "strategist": 2,
    "explorer": 1,
    "exploiter": 0
}

LANE_LABELS = {
    2: "strategist",
    1: "explorer",
    0: "exploiter"
}

# BUILD TIMELINE DATA
x_vals = []
y_vals = []
colors = []
sizes = []
hover_text = []

for node in nodes:

    step_id = int(node["id"])
    agent = node["node"]

    x_vals.append(step_id)
    y_vals.append(LANE_MAP.get(agent, -1))

    # COLOR LOGIC
    if not node["success"]:
        colors.append("red")

    elif node["step_type"] == "THINK":
        colors.append("blue")

    elif node["step_type"] == "ACT":
        colors.append("orange")

    else:
        colors.append("gray")

    # SIZE LOGIC (file read highlight)
    if node.get("file_read"):
        sizes.append(18)
    else:
        sizes.append(10)

    hover = (
        f"Step: {step_id}<br>"
        f"Agent: {agent}<br>"
        f"Step Type: {node['step_type']}<br>"
        f"Kind: {node['kind']}<br>"
        f"Decision: {node.get('decision')}<br>"
        f"File Read: {node.get('file_read') or 'None'}<br>"
        f"Success: {node['success']}"
    )

    hover_text.append(hover)

# DRAW TIMELINE
fig = go.Figure()

fig.add_trace(go.Scatter(

    x=x_vals,
    y=y_vals,

    mode="markers",

    marker=dict(
        size=sizes,
        color=colors,
        line=dict(width=1, color="black")
    ),

    text=hover_text,

    hovertemplate="<b>%{text}</b><extra></extra>"
))

fig.update_layout(

    height=500,

    title="Agent Execution Swimlane Timeline",

    xaxis=dict(
        title="Execution Step"
    ),

    yaxis=dict(
        title="Agent",
        tickvals=list(LANE_LABELS.keys()),
        ticktext=list(LANE_LABELS.values())
    ),

    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# SIDEBAR STEP SELECTOR
st.sidebar.title("Step Inspector")

selected_step = st.sidebar.number_input(

    "Step ID",

    min_value=0,
    max_value=len(trace)-1,

    value=0,
    step=1
)

step = trace[selected_step]

# STEP DETAILS PANEL
st.header(f"Step {selected_step} Details")

col1, col2 = st.columns(2)

with col1:

    st.subheader("Basic Info")

    st.write("Agent:", step["node"])
    st.write("Kind:", step["kind"])
    st.write("Step Type:", step["step_type"])
    st.write("Success:", step["success"])
    st.write("Decision:", step["decision"])

with col2:

    st.subheader("File Context")

    st.write("File Read:", step["file_read"])

    st.write("Files seen so far:")

    st.json(context[selected_step]["files_seen_so_far"])

# THOUGHT DISPLAY
st.subheader("Thought Trace")

if step["thought"]:

    for thought in step["thought"]:
        st.code(thought)

else:

    st.write("No thought recorded")

# RAW DATA
with st.expander("Raw Step Data"):

    st.json(step)

# METRICS PANEL
st.header("Trace Metrics")

total_steps = len(trace)

think_steps = sum(
    1 for s in trace
    if s["step_type"] == "THINK"
)

act_steps = sum(
    1 for s in trace
    if s["step_type"] == "ACT"
)

fail_steps = sum(
    1 for s in trace
    if not s["success"]
)

files_read = len(set(
    s["file_read"]
    for s in trace
    if s["file_read"]
))

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Steps", total_steps)
col2.metric("Think Steps", think_steps)
col3.metric("Act Steps", act_steps)
col4.metric("Failures", fail_steps)

st.metric("Unique Files Read", files_read)

# LEGEND
st.header("Legend")

st.write("Blue = THINK step")
st.write("Orange = ACT step")
st.write("Red = Failure")
st.write("Large dot = File read")
