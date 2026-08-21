# agent-lab

A notebook, not a program. This repo is what it costs to run Claude Code
against a local model, measured rather than guessed.

There is no entry point and nothing to install. The artifact is
**[`CLAUDE.md`](CLAUDE.md)** — a dated, append-only log of every way a local
model misbehaved while driving a four-subagent setup, and what actually fixed
it. Four subagent definitions in `.claude/agents/` are the configuration those
lessons were learned against.

If you are pointing Claude Code at Ollama and wondering why it feels slow or
why your subagents keep failing, the answers are probably in here.

---

## How it works

Claude Code is pointed at a local Ollama server via the Anthropic-compatible
endpoint. `CLAUDE.md` is re-read on every run and holds the standing rules.
Four subagents are declared in `.claude/agents/`:

| Agent | Role | Tools |
|---|---|---|
| `builder` | code, scripts, config | Read, Write, Edit, Bash, Glob, Grep |
| `critic` | adversarial review before acceptance | Read, Grep, Glob |
| `librarian` | maintains the `notes/` blackboard | Read, Write, Edit, Glob, Grep |
| `researcher` | outside facts | Read, Write, Glob, Grep |

`notes/` is a shared blackboard any agent may read and only its owner may
write. `evals/tasks.md` is a five-item regression list — tool call, delegation,
sourcing, refusal-to-loop, handoff — to re-run after any model or prompt
change. `evals/latency_matrix.py` measures throughput at the Ollama layer
rather than through the harness.

## Running it

```bash
# point Claude Code at a local Ollama server
export ANTHROPIC_BASE_URL=http://localhost:11434
export ANTHROPIC_AUTH_TOKEN=local
claude
```

Wrap that in a `claude-local` alias. **Check `/status` before trusting any
measurement** — these variables are per-shell, and a new terminal tab silently
falls back to the real Anthropic API. Timings taken in that state are cloud
Claude, not your model.

## The findings

The full log is in [`CLAUDE.md`](CLAUDE.md). The load-bearing ones:

**A 30B MoE is cheaper than an 8B dense model on this stack.** Measured on
Apple Silicon: `qwen3-coder` prefills at **1,073 tok/s** against `qwen3:8b`'s
**665 tok/s**. Active parameters are the right unit, not total parameters.
"Bigger model = slower" is false here.

**Thinking costs about 20x on trivial prompts** — 8.57s vs 0.42s for "list
three colors", identical answers. But the `/no_think` prompt switch does *not*
reach the model through the harness, and there is no Modelfile-level toggle
(`PARAMETER think false` is rejected). It is a per-request field only. On a
hybrid reasoning model you cannot turn thinking off from inside the config —
pick a non-thinking model instead.

**Neither of those explains the latency.** Removing the thinking tax *and*
running 1.6x faster prefill changed a real agentic turn by nothing: 1m55s vs
1m47s. The harness dominates. Ruled out: thinking tokens, model size, prefill
throughput, GPU offload, cold start. The structural cause is that Ollama's
Anthropic-compat endpoint has no prompt caching, so every turn re-prefills the
whole conversation. Consequence: **prefer many short sessions to one long
one**, and keep this file short — every word is re-billed on every turn.

**Only declare tools that exist on your backend.** `critic.md` declared
`WebSearch`/`WebFetch`, which Ollama does not provide. That broke the subagent
call itself with "Invalid tool parameters" and hung for 8 minutes. Removing
them dropped the same call to 20s. Phantom tool names are not ignored; they
poison the invocation.

**Literal templates bind; prose format specs do not.** `critic.md` supplies its
output format as a literal code block and the model matched it exactly.
`librarian.md` described its format in prose and the model invented its own.

**Withholding context from a reviewer improves the review.** Handed the
artifact's *text*, the critic produced a full review before its file read even
succeeded, then re-emitted a byte-identical review after actually reading the
file. Its verdict preceded its evidence. Handed only the *path*, the same model
found the real defect it had missed and dropped a fabricated one. Pass a critic
the path, never the contents.

**Absence of criticism is not approval.** Subagent output can fail to reach the
orchestrator even when the agent completes cleanly. Twice the orchestrator
filled the gap by writing its own review and, once, approved unreviewed work
without saying so. If a verdict is not visible in the transcript, the work is
unreviewed. Recovery path: the harness writes each subagent's output to
`/private/tmp/claude-501/<project>/<session>/tasks/<agent-id>.output`.

**Compliance can be shape without substance.** A rule requiring raw tool output
to be quoted before summarising produced a run where the model printed the
*contents* of a file and labelled them "the verbatim directory listing" — never
listing the directory at all. Check that a rule changed the behaviour, not just
the vocabulary.

## What this fed into

The measurement discipline here — and specifically the path-not-contents rule
for reviewers, and mechanical rather than self-reported records — carried
directly into [antfarm](../antfarm), which instruments claimed actions against
the real tool log.

## Status

Dormant since 2026-08-13. The `evals/tasks.md` results table was never filled
in; `notes/INDEX.md` is stale. `researcher.md` still declares `WebSearch` and
`WebFetch`, which by this repo's own findings will break it on an Ollama
backend — fix that before using it.

MIT licensed.
