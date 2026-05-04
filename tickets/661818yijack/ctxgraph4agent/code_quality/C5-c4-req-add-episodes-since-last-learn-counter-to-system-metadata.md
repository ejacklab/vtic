---
id: C5
title: '[C4] REQ: Add episodes_since_last_learn counter to system_metadata'
repo: 661818yijack/ctxgraph4agent
category: code_quality
severity: high
status: closed
owner: 661818yijack
file: crates/ctxgraph-core/src/storage/sqlite.rs
created_at: '2026-05-03T02:03:09.274560Z'
updated_at: '2026-05-03T02:07:52.819088Z'
tags:
- req
- learn
- counter
- system_metadata
version: 2
due_date: '2026-05-04'
---

<!-- DESCRIPTION -->
Add a system_metadata counter 'episodes_since_last_learn' that increments on every add_episode() call. When it reaches the configured threshold (default 50, stored as 'learn_interval' in system_metadata), trigger the learning pipeline. After triggering, reset the counter to 0. The counter and interval must be persisted in system_metadata (same pattern as query_count_since_cleanup / cleanup_interval).
