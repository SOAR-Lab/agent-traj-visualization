# TraceView Evaluation Instructions

Use this guide to evaluate TraceView from the perspective of someone labeling,
reviewing, and inspecting an agent trajectory.

[IMAGE PLACEHOLDER: TraceView home or first screen]

## Evaluation Goal

Evaluate whether TraceView helps users:

- understand an agent trajectory at a high level
- label action categories and relationships efficiently
- move a labeled trajectory into Overview
- inspect a trajectory graph in Analysis
- understand where labels, relationships, and raw evidence come from

Focus on clarity, workflow friction, missing context, confusing labels, and places
where the app does not behave the way you expected.

## Before You Start

You should have one of the following:

- a running TraceView URL from the study organizer
- a local checkout with setup instructions from `README.md`

Recommended sample traces are available in `evaluation_samples/`. Each file is
an 8-step SWE-agent `.traj` window selected to keep labeling work manageable.

If running locally, start the app from the project root:

```shell
streamlit run traceview.py
```

Use a modern browser. Keep the browser window wide enough to see the graph and
sidebar comfortably.

[IMAGE PLACEHOLDER: Browser showing TraceView loaded]

## What To Record During Evaluation

While using the app, write down:

- what you expected to happen before each major action
- what actually happened
- any text, labels, or controls that felt unclear
- places where you had to scroll more than expected
- places where you wanted more context
- any bugs, lag, visual overlap, or broken navigation
- one thing you would keep unchanged
- one thing you would improve first

Use the feedback template at the end of this document.

## Evaluation Task 1: First Impression And Navigation

1. Open TraceView.
2. Identify the main navigation buttons: `Labeling`, `Overview`, and `Analysis`.
3. Without reading the README, explain what you think each section does.
4. Click each navigation button once.
5. Return to `Labeling`.

[IMAGE PLACEHOLDER: Main navigation buttons]

Evaluate:

- Are the three sections easy to understand?
- Is it clear where a new user should begin?
- Does the active page state look obvious?
- Does navigation preserve or reset state in a way that makes sense?

## Evaluation Task 2: Ingest A Raw Trajectory

1. Go to `Labeling`.
2. Upload or paste the provided trajectory sample.
3. If a local sample loader is available, you may use that instead.
4. Review any parser warnings.
5. Continue into the annotation flow.

[IMAGE PLACEHOLDER: Labeling ingest screen]

Evaluate:

- Is it clear what file types or input formats are accepted?
- Is the upload/paste flow understandable?
- Are parser warnings readable and actionable?
- Is it clear how many steps were parsed?

## Evaluation Task 3: Review The Completion Summary

After ingest, review the completion summary before entering the workspace.

1. Look at the coverage metrics.
2. Open each tab: `Summary`, `Behavior`, `Action Categories`, and `Issues`.
3. Use the `Open in single-run workspace` button.

[IMAGE PLACEHOLDER: Completion summary coverage header]

Evaluate:

- Do the coverage metrics make sense?
- Are the tabs named clearly?
- Is it clear that the summary is a review page and not the main editing area?
- Is the primary next action easy to find?

## Evaluation Task 4: Label Action Categories

In the single-run workspace, start with action labeling.

1. Review the sidebar progress indicator.
2. Read the compact action-label legend in the sidebar.
3. Label at least the first five actions.
4. Open at least two `View` popovers to inspect raw thought/action/result logs.
5. If the provided sample is short, label all actions.
6. If the sample is long, label enough actions to judge the workflow.

[IMAGE PLACEHOLDER: Action labeling table and sidebar legend]

Evaluate:

- Is it clear that action labels must be completed before relationship labels?
- Is the sidebar legend useful without being too large?
- Are action previews long enough to make a decision?
- Is the `View` popover useful for longer logs?
- Do label selections persist immediately?
- Is scrolling manageable?

## Evaluation Task 5: Label Relationships

After action labeling is complete, continue to relationship labels.

1. Click `Continue to relationship labels`.
2. Use the sidebar to choose a relationship family.
3. Read the sidebar legend for the selected family.
4. Label at least five relationships.
5. Open the relationship inspector for at least one relationship.
6. Switch to another relationship family and repeat briefly.

[IMAGE PLACEHOLDER: Relationship labeling table]

Evaluate:

- Is the transition from action labels to relationship labels clear?
- Is the selected relationship family obvious?
- Are allowed labels understandable?
- Is the compact legend enough to make a labeling decision?
- Does the relationship inspector provide enough evidence?
- Is it clear what remains unlabeled?

## Evaluation Task 6: Export Or Send To Overview

When relationship labeling is available:

1. Review the export controls in the sidebar.
2. Send the labeled trajectory to `Overview`.
3. Optionally download the annotation JSON or viewer CSV zip.

[IMAGE PLACEHOLDER: Sidebar export controls]

Evaluate:

- Are export controls shown only when you expect them?
- Is `Send to overview` easy to find?
- Is it clear what each download contains?
- Does the transition to Overview feel successful?

## Evaluation Task 7: Review The Run In Overview

In `Overview`:

1. Find the uploaded or labeled run.
2. Review the run summary.
3. Note whether the result is shown as unscored.
4. Open the run in `Analysis`.

[IMAGE PLACEHOLDER: Overview page with labeled run]

Evaluate:

- Is the uploaded/labeled run easy to find?
- Is it clear that uploaded traces do not have AutoCodeRover result metadata?
- Is the information dense enough without being overwhelming?
- Is opening Analysis discoverable?

## Evaluation Task 8: Inspect The Graph In Analysis

Analysis starts in `Iteration` mode.

1. Confirm that `Iteration` mode is selected by default.
2. Inspect the collapsed iteration graph.
3. Click an iteration node.
4. Review the inspector output.
5. Switch to `Detailed` mode.
6. Click a `Thought`, `Action`, or `Result` node.
7. Try at least one relation filter.
8. Adjust one layout control, such as node size or label length.

[IMAGE PLACEHOLDER: Analysis iteration graph]

[IMAGE PLACEHOLDER: Analysis detailed graph]

Evaluate:

- Is Iteration mode a useful default?
- Is it clear what a collapsed iteration node represents?
- Is the inspector useful in both graph modes?
- Are filters and layout controls understandable?
- Does the graph remain readable after changes?
- Is the separate inspector page option useful or confusing?

## Evaluation Task 9: Final Reflection

Answer these questions after completing the workflow:

1. What was the easiest part of the workflow?
2. What was the most confusing part?
3. Where did you need more context?
4. Where did the UI show too much information?
5. Where did the UI hide information you needed?
6. Would you trust the exported data? Why or why not?
7. What should be changed before using this with more evaluators?

## Feedback Template

Copy this template into your notes.

```text
Evaluator name:
Date:
Browser:
Operating system:
Trace used:

Overall rating, 1-5:

What worked well:

What was confusing:

Navigation issues:

Labeling issues:

Overview issues:

Analysis/graph issues:

Missing information:

Bugs or visual problems:

Most important improvement:

Additional comments:
```

## Optional Severity Scale

Use this scale for issues:

- `Critical`: blocks completion of the evaluation task
- `High`: causes wrong interpretation or major workflow friction
- `Medium`: slows the evaluator down but has a workaround
- `Low`: polish, wording, or minor layout issue
