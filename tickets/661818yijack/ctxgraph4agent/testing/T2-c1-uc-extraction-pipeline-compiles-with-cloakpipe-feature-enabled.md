---
id: T2
title: '[C1] UC: Extraction pipeline compiles with cloakpipe feature enabled'
repo: 661818yijack/ctxgraph4agent
category: testing
severity: medium
status: closed
owner: 661818yijack
file: null
created_at: '2026-04-28T02:04:48.113807Z'
updated_at: '2026-04-28T02:06:24.164184Z'
tags:
- uc
- cloakpipe
- compilation
version: 2
---

<!-- DESCRIPTION -->
Given the cloakpipe feature strips PII before LLM escalation\nWhen compiling with --features cloakpipe\nThen pipeline.rs compiles successfully, including the rehydration code path that mutates llm_result.entities and llm_result.relations.
