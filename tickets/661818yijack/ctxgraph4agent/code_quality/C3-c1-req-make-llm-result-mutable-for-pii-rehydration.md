---
id: C3
title: '[C1] REQ: Make llm_result mutable for PII rehydration'
repo: 661818yijack/ctxgraph4agent
category: code_quality
severity: high
status: closed
owner: 661818yijack
file: crates/ctxgraph-extract/src/pipeline.rs
created_at: '2026-04-28T02:04:45.331858Z'
updated_at: '2026-04-28T02:06:21.611028Z'
tags:
- req
- compilation
- mutability
- cloakpipe
version: 2
---

<!-- DESCRIPTION -->
In pipeline.rs lines 265-281, the match arm binds  but then attempts to mutate  and  inside the #[cfg(feature = "cloakpipe")] block. This causes E0594/E0596 compilation errors because the binding is not mutable.\n\nFix: change binding to  so the fields can be reassigned and iterated mutably.
