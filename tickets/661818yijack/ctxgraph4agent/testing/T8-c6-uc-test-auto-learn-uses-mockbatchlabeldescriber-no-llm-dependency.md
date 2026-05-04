---
id: T8
title: '[C6] UC: Test auto-learn uses MockBatchLabelDescriber (no LLM dependency)'
repo: 661818yijack/ctxgraph4agent
category: testing
severity: medium
status: closed
owner: 661818yijack
file: null
created_at: '2026-05-03T02:03:43.191102Z'
updated_at: '2026-05-03T02:07:53.871475Z'
tags:
- uc
- test
- learn
- mock
- no-llm
version: 2
due_date: '2026-05-04'
---

<!-- DESCRIPTION -->
Given a Graph with no API keys configured
When add_episode() triggers auto-learn at threshold
Then the pipeline should use MockBatchLabelDescriber
And the pipeline should complete without network calls
And add_episode() should succeed without errors
