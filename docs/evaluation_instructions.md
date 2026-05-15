# TraceView Evaluation Instructions

Use this guide before and during the survey. The survey form itself will walk
you through the evaluation tasks and ask questions at the relevant checkpoints.

## 0. Quick Start

TraceView is a visual analytics tool for inspecting LLM agent trajectories from
automatic program repair runs. It turns raw logs into iterations with `Thought`,
`Action`, and `Result` nodes, then lets you label actions, label relationships,
send the run to Overview, and inspect the graph in Analysis.

From the anonymous repository page:

1. Open <https://anonymous.4open.science/r/agent-traj-visualization-8EF9/>.
2. Click the `ZIP` button, not the browser download button.
3. Unzip the file and open a terminal inside the unzipped repository folder.

Run:

```bash
uv --version
```

If `uv` is missing, install it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then run TraceView from the repository root:

```bash
uv sync
uv run streamlit run traceview.py
```

Use one sample trajectory from `evaluation_samples/`, such as:

```text
evaluation_samples/django__django-10924__eval_01_localization.traj
```

## 1. Background

Automatic program repair (APR) systems try to solve software bugs, including
GitHub issues in open-source software (OSS) projects. LLM-based APR systems often
work step by step: at each step they produce a thought, choose an action, and
receive environment feedback as a result.

TraceView is meant to help people who work with these systems better visualize
and understand that process: what the system did, what worked, and what did not.
It turns long text logs into a more intuitive interface for inspecting the
repair process.

Evaluate whether TraceView helps you:

- understand an APR agent run from raw trajectory logs
- label what each action is doing
- label how thoughts, actions, and results influence later steps
- move from a high-level run summary to graph-level analysis
- find problematic steps, nodes, relationships, or iterations efficiently

Focus on clarity, missing context, confusing labels, workflow friction, and places
where the interface behaves differently from what you expected.

Fill out the survey while using the tool. For timing questions, start the timer
when you begin looking for problematic parts in `Analysis`. Stop when you can
name the problematic step, node, relationship, or iteration and explain why.

TraceView uses action categories and relationship labels to describe what the
agent is doing and how one part of the trajectory relates to another. You do not
need to memorize these labels before starting. They should make more sense as
you complete the labeling and graph-inspection tasks, and the interface also
shows compact legends when you need them.

Use these definitions as a quick reference when labeling and when interpreting
the graph.

### Action Categories

| Label | Meaning |
| --- | --- |
| `Explore` | Broadly inspect the task, repository, environment, or available context. |
| `Locate` | Identify the specific file, symbol, function, or code area to change. |
| `Search` | Run a targeted search for text, references, examples, or related behavior. |
| `Reproduce` | Run commands or checks to observe, reproduce, or isolate the problem. |
| `Generate fix` | Create or edit code intended to solve the task. |
| `Run tests` | Run tests, linters, or validation commands after a change. |
| `Refactor` | Reorganize or simplify code without changing intended behavior. |
| `Explain` | Reason, summarize, or plan without directly changing or validating code. |

### Relationship Labels

| Label | Meaning |
| --- | --- |
| `Alignment` | The action correctly follows or implements the thought. |
| `Misalignment` | The action does not match or serve the source thought. |
| `Follow-up` | The target continues the same line of work from the source. |
| `Refinement` | The target narrows, corrects, or improves on the source. |
| `Redundancy` | The target repeats prior reasoning without meaningful new progress. |
| `Repetition` | The target repeats a similar action without useful new information. |
| `Divergence` | The target shifts away from the prior goal without clear rationale. |
| `Contradiction` | The target conflicts with information or reasoning in the source. |
| `Informative` | The result gives useful information for the target action. |
| `Triggering` | The result directly prompts the target action. |
| `No influence` | The source does not materially affect the target. |
| `Misinterpretation` | The target draws an incorrect conclusion from the source result. |

Relationship families describe which two nodes are being compared:

- `Thought -> Action`: does the action match the same-step thought?
- `Thought -> Thought`: how does the next thought relate to the current thought?
- `Action -> Action`: how does the next action relate to the current action?
- `Result -> Thought`: how does the next thought use the current result?
- `Result -> Action`: how does the next action use the current result?

## 2. Main Parts Of TraceView

TraceView has three main sections:

- `Labeling`: upload or paste a trajectory, label actions, label relationships,
  and send the labeled run forward.
- `Overview`: review available runs and open one in graph analysis.
- `Analysis`: inspect the trajectory graph in `Iteration` or `Detailed` mode.

`Iteration` mode collapses consecutive steps with the same action category into
higher-level iteration nodes. `Detailed` mode shows the full step graph with
separate `Thought`, `Action`, and `Result` nodes.

## 3. Evaluation Flow

After setup, return to the survey form. The form will walk you through each task
in order and ask the relevant questions at the right checkpoint. Answer the
task-specific questions as you complete each task, then answer the final
overall-evaluation questions after finishing the full workflow.

For timing questions in the form, start the timer when you begin looking for
problematic parts in `Analysis`. Stop when you can name the problematic step,
node, relationship, or iteration and explain why.

The final quality-criteria questions ask about:

- `Accuracy`: did the visualization match the original trajectory?
- `Integrity`: did the interface help you understand the repair process?
- `Completeness`: was enough evidence available to make judgments?
- `Design`: did the hierarchy help you move between overview and detail?

Use concrete examples when possible, especially for confusing renderings,
missing information, or the problematic step, node, relationship, or iteration
you identified.
