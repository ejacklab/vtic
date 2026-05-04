---
id: T5
title: '[C5] UC: Test learn_interval can be set and read via Graph API'
repo: 661818yijack/ctxgraph4agent
category: testing
severity: medium
status: closed
owner: 661818yijack
file: null
created_at: '2026-05-03T02:03:25.457828Z'
updated_at: '2026-05-03T02:07:53.344129Z'
tags:
- uc
- test
- interval
- learn
version: 2
due_date: '2026-05-04'
---

<!-- DESCRIPTION -->
Given a Graph with default learn_interval
When set_learn_interval(25) is called
Then get_learn_interval() returns 25
And subsequent add_episode calls should trigger learn at 25 not 50
