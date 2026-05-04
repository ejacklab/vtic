---
id: T6
title: '[C6] UC: Test auto-learn triggers silently at threshold and resets counter'
repo: 661818yijack/ctxgraph4agent
category: testing
severity: medium
status: closed
owner: 661818yijack
file: null
created_at: '2026-05-03T02:03:31.870610Z'
updated_at: '2026-05-03T02:07:53.515888Z'
tags:
- uc
- test
- trigger
- learn
- silent
version: 2
due_date: '2026-05-04'
---

<!-- DESCRIPTION -->
Given a Graph with learn_interval=5
When add_episode() is called 5 times
Then the 5th call should trigger run_learning_pipeline() silently
And episodes_since_last_learn should reset to 0 after trigger
And add_episode() should NOT return an error even if pipeline fails
