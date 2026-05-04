---
id: C8
title: '[C7] REQ: Add dual-format LLM response parser'
repo: 661818yijack/ctxgraph4agent
category: code_quality
severity: high
status: open
owner: 661818yijack
file: crates/ctxgraph-cli/src/commands/learn.rs
created_at: '2026-05-04T02:12:14.275183Z'
updated_at: '2026-05-04T02:12:14.275183Z'
tags:
- req
- cli
- learn
- llm
- parsing
version: 1
due_date: '2026-05-05'
---

<!-- DESCRIPTION -->
The RealBatchLabelDescriber::call_llm method in crates/ctxgraph-cli/src/commands/learn.rs currently only parses OpenAI-format responses (json['choices'][0]['message']['content']). It needs to support both OpenAI and Anthropic formats because:

1. ZAI (GLM-5) uses OpenAI format
2. MiniMax uses Anthropic format (json['content'][0]['text'])

The fix: after receiving the JSON response, try OpenAI format first, then fall back to Anthropic format. Extract the text content from whichever format is present.

Acceptance criteria:
- call_llm returns the LLM text content for OpenAI-format responses
- call_llm returns the LLM text content for Anthropic-format responses
- If neither format is found, return the existing 'Invalid LLM response' error
- No breaking changes to the CLI interface

File: crates/ctxgraph-cli/src/commands/learn.rs
