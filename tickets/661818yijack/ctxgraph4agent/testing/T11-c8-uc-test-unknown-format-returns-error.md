---
id: T11
title: '[C8] UC: Test unknown format returns error'
repo: 661818yijack/ctxgraph4agent
category: testing
severity: medium
status: open
owner: 661818yijack
file: null
created_at: '2026-05-04T02:12:39.185897Z'
updated_at: '2026-05-04T02:12:39.185897Z'
tags:
- uc
- test
- error-handling
- cli
version: 1
due_date: '2026-05-05'
---

<!-- DESCRIPTION -->
Given a RealBatchLabelDescriber instance
When call_llm receives an unknown JSON format:
  {"foo":"bar"}
Then it returns an error containing 'Invalid LLM response'

This ensures graceful degradation when a provider changes their format.
