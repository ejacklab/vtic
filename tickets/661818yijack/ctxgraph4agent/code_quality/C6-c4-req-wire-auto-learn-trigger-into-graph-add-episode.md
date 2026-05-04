---
id: C6
title: '[C4] REQ: Wire auto-learn trigger into Graph::add_episode()'
repo: 661818yijack/ctxgraph4agent
category: code_quality
severity: high
status: closed
owner: 661818yijack
file: crates/ctxgraph-core/src/graph.rs
created_at: '2026-05-03T02:03:15.121900Z'
updated_at: '2026-05-03T02:07:52.991981Z'
tags:
- req
- learn
- trigger
- add_episode
version: 2
due_date: '2026-05-04'
---

<!-- DESCRIPTION -->
Modify Graph::add_episode() to increment episodes_since_last_learn after successful episode insertion. When the counter reaches learn_interval (default 50), call run_learning_pipeline() with a MockBatchLabelDescriber (silent, no LLM dependency) to avoid requiring API keys. After triggering, reset the counter to 0. The trigger should be silent — if the pipeline fails, log the error but don't fail the add_episode() call. The agent should never see 'learn failed' when it's just logging an episode.
