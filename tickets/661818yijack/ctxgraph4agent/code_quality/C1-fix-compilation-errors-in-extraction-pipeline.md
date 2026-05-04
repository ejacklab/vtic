---
id: C1
title: Fix compilation errors in extraction pipeline
repo: 661818yijack/ctxgraph4agent
category: code_quality
severity: high
status: closed
owner: 661818yijack
file: crates/ctxgraph-extract/src/pipeline.rs
created_at: '2026-04-28T02:04:17.247554Z'
updated_at: '2026-04-28T02:06:18.987474Z'
tags:
- compilation
- pipeline
- llm
- cloakpipe
version: 2
---

<!-- DESCRIPTION -->
The extraction pipeline fails to compile due to two issues in pipeline.rs:\n1. llm.extract() expects &str but receives String (line 260)\n2. llm_result needs mut binding for PII rehydration (lines 269, 274)\n\nThese errors block clippy and any builds with --all-features. The code was likely introduced during the CloakPipe/LLM refactor and never compiled successfully.\n\nAffected file: crates/ctxgraph-extract/src/pipeline.rs
