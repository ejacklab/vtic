---
id: C2
title: '[C1] REQ: Pass &str instead of String to llm.extract()'
repo: 661818yijack/ctxgraph4agent
category: code_quality
severity: high
status: closed
owner: 661818yijack
file: crates/ctxgraph-extract/src/pipeline.rs
created_at: '2026-04-28T02:04:43.553972Z'
updated_at: '2026-04-28T02:06:20.334483Z'
tags:
- req
- compilation
- type-mismatch
version: 2
---

<!-- DESCRIPTION -->
In pipeline.rs line 260,  passes a String but the function signature expects &str. This is a type mismatch that prevents compilation.\n\nFix: pass  so the String is borrowed as &str.\n\nThis must work for both the cloakpipe path (pseudonymize_for_llm returns String) and the non-cloakpipe path (text is &str, assigned to llm_text).
