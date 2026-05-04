---
id: T10
title: '[C8] UC: Test Anthropic-format response parsing'
repo: 661818yijack/ctxgraph4agent
category: testing
severity: medium
status: open
owner: 661818yijack
file: null
created_at: '2026-05-04T02:12:30.682261Z'
updated_at: '2026-05-04T02:12:30.682261Z'
tags:
- uc
- test
- anthropic
- cli
- minimax
version: 1
due_date: '2026-05-05'
---

<!-- DESCRIPTION -->
Given a RealBatchLabelDescriber instance
When call_llm receives an Anthropic-format JSON response:
  {"content":[{"type":"text","text":"Hello world"}]}
Then it returns Ok("Hello world")

This tests the MiniMax code path.
