---
id: T7
title: '[C6] UC: Test auto-learn does NOT trigger below threshold'
repo: 661818yijack/ctxgraph4agent
category: testing
severity: medium
status: closed
owner: 661818yijack
file: null
created_at: '2026-05-03T02:03:37.120733Z'
updated_at: '2026-05-03T02:07:53.696001Z'
tags:
- uc
- test
- trigger
- negative
- learn
version: 2
due_date: '2026-05-04'
---

<!-- DESCRIPTION -->
Given a Graph with learn_interval=10
When add_episode() is called 9 times
Then run_learning_pipeline() should NOT be called
And episodes_since_last_learn should be 9
