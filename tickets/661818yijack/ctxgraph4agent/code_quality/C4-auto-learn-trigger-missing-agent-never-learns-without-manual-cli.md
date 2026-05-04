---
id: C4
title: "Auto-learn trigger missing \u2014 agent never learns without manual CLI"
repo: 661818yijack/ctxgraph4agent
category: code_quality
severity: high
status: closed
owner: 661818yijack
file: crates/ctxgraph-core/src/graph.rs
created_at: '2026-05-03T02:03:02.112855Z'
updated_at: '2026-05-03T02:07:52.637864Z'
tags:
- learn
- auto-trigger
- pipeline
- critical-gap
version: 2
due_date: '2026-05-04'
---

<!-- DESCRIPTION -->
The learn pipeline (run_learning_pipeline) exists and works, but it is ONLY triggered by explicit CLI/MCP 'learn' command. The design decision from 2026-04-05 says 'learn runs automatically after every N episodes (default 50).' The code has zero implementation: Graph::add_episode() never checks episode count, no episodes_since_last_learn counter exists in system_metadata, and run_learning_pipeline() is only called by explicit CLI/MCP. This means the agent never learns unless manually told to — defeating the core 'agent gets better over time' value proposition.
