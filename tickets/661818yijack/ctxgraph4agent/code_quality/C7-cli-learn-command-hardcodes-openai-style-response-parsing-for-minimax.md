---
id: C7
title: CLI learn command hardcodes OpenAI-style response parsing for MiniMax
repo: 661818yijack/ctxgraph4agent
category: code_quality
severity: medium
status: open
owner: 661818yijack
file: crates/ctxgraph-cli/src/commands/learn.rs
created_at: '2026-05-04T02:12:05.901370Z'
updated_at: '2026-05-04T02:12:05.901370Z'
tags:
- bug
- cli
- learn
- minimax
- llm
version: 1
due_date: '2026-05-05'
---

<!-- DESCRIPTION -->
The ctxgraph learn CLI command uses RealBatchLabelDescriber which calls MiniMax at https://api.minimax.io/anthropic but parses the response with OpenAI-style json['choices'][0]['message']['content']. MiniMax returns Anthropic-format responses (json['content'][0]['text']), so the CLI learn command will always fail with 'Invalid LLM response' when using MiniMax keys, even though the API key is valid and the call succeeds.

This breaks the learn command for the default MiniMax configuration that EJ gege prefers. The fix is to detect the response format and parse both OpenAI and Anthropic formats.

Affected file: crates/ctxgraph-cli/src/commands/learn.rs

This is a real bug — the MiniMax endpoint returns a different JSON shape than what the code expects.
