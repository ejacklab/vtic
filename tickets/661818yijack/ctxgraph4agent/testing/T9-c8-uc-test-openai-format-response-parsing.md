---
id: T9
title: '[C8] UC: Test OpenAI-format response parsing'
repo: 661818yijack/ctxgraph4agent
category: testing
severity: medium
status: open
owner: 661818yijack
file: null
created_at: '2026-05-04T02:12:22.282488Z'
updated_at: '2026-05-04T02:12:22.282488Z'
tags:
- uc
- test
- openai
- cli
version: 1
due_date: '2026-05-05'
---

<!-- DESCRIPTION -->
Given a RealBatchLabelDescriber instance
When call_llm receives an OpenAI-format JSON response:
  {"choices":[{"message":{"content":"Hello world"}}]}
Then it returns Ok("Hello world")

This tests the ZAI/GLM-5 code path.
