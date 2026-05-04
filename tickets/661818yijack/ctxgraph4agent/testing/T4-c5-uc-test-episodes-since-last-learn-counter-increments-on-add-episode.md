---
id: T4
title: '[C5] UC: Test episodes_since_last_learn counter increments on add_episode'
repo: 661818yijack/ctxgraph4agent
category: testing
severity: medium
status: closed
owner: 661818yijack
file: null
created_at: '2026-05-03T02:03:20.364711Z'
updated_at: '2026-05-03T02:07:53.166029Z'
tags:
- uc
- test
- counter
- learn
version: 2
due_date: '2026-05-04'
---

<!-- DESCRIPTION -->
Given a fresh Graph
When add_episode() is called 3 times
Then episodes_since_last_learn should be 3
And get_learn_interval() should return default 50
