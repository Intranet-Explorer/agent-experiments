# agent-lab

Claude Code driven by a local model through Ollama, with four subagents. A
notebook, not a program: no entry point, nothing to install.

The main artifact is [`CLAUDE.md`](CLAUDE.md). It holds the standing rules the
model reads on every run, plus an append-only log of each misbehaviour observed
and what fixed it. `.claude/agents/` holds the four subagent definitions those
lessons were learned against.

| Agent | Role | Tools |
|---|---|---|
| `builder` | code, scripts, config | Read, Write, Edit, Bash, Glob, Grep |
| `critic` | adversarial review before acceptance | Read, Grep, Glob |
| `librarian` | maintains the `notes/` blackboard | Read, Write, Edit, Glob, Grep |
| `researcher` | outside facts | Read, Write, Glob, Grep |

- `notes/` is a shared blackboard. Any agent may read it; only the owner of a
  file may write it.
- `evals/tasks.md` is a five-item regression list (tool call, delegation,
  sourcing, refusal to loop, handoff). Re-run it after any model or prompt
  change.
- `evals/latency_matrix.py` measures throughput at the Ollama layer, bypassing
  the harness.
- `count_notes.sh` is the builder's output from the handoff test.

## Running it

```bash
# point Claude Code at a local Ollama server
export ANTHROPIC_BASE_URL=http://localhost:11434
export ANTHROPIC_AUTH_TOKEN=local
claude
```

Wrap that in a `claude-local` alias. The variables are per-shell. A new
terminal tab without them falls back to the Anthropic API with no warning, and
timings taken there are cloud Claude, not the local model. Check `/status`
before trusting a measurement.

```bash
python3 evals/latency_matrix.py [model]   # default qwen3:8b
```

## Findings

Measured on Apple Silicon. Full log in [`CLAUDE.md`](CLAUDE.md).

**A 30B MoE is cheaper than an 8B dense model on this stack.** `qwen3-coder`
prefills at 1,073 tok/s; `qwen3:8b` at 665 tok/s. Active parameters are the
unit that matters, not total parameters.

**Thinking costs about 20x on a trivial prompt.** "List three colors" took
8.57s with thinking and 0.42s without, same answer. The `/no_think` prompt
switch does not reach the model through the harness. There is no Modelfile
toggle (`PARAMETER think false` is rejected). Thinking is a per-request field
only, so on a hybrid reasoning model it cannot be turned off from the config.
Use a non-thinking model instead.

**Neither explains the latency.** Removing thinking and getting 1.6x faster
prefill left an agentic turn unchanged: 1m55s vs 1m47s. Ruled out: thinking
tokens, model size, prefill throughput, GPU offload, cold start. The harness
dominates. Ollama's Anthropic-compatible endpoint has no prompt caching, so
every turn re-prefills the whole conversation. Prefer many short sessions to
one long one, and keep `CLAUDE.md` short; every word is re-prefilled on every
turn.

**Declare only tools the backend has.** `critic.md` declared `WebSearch` and
`WebFetch`, which Ollama does not provide. The subagent call failed with
"Invalid tool parameters" and hung for 8 minutes. With them removed the same
call took 20s. Unknown tool names are not ignored; they break the invocation.

**Literal templates bind; prose format specs do not.** `critic.md` gives its
output format as a literal code block, and the model matched it exactly.
`librarian.md` describes its format in prose, and the model made up its own.

**A reviewer given the path reviews better than one given the contents.**
Handed the artifact's text, the critic produced a full review before its file
read succeeded, then emitted a byte-identical review after reading the file.
Handed only the path, the same model found the defect it had missed (the
script's relative path returns 0 from any other directory) and dropped a
fabricated one. Pass a critic the path, never the contents.

**No verdict in the transcript means unreviewed.** Subagent output can fail to
reach the orchestrator even when the subagent completes cleanly. Twice the
orchestrator wrote its own review in its place; once it approved unreviewed
work without saying so. The output is still on disk at
`/private/tmp/claude-501/<project>/<session>/tasks/<agent-id>.output`.

**A rule can change the vocabulary without changing the behaviour.** A rule
requiring raw tool output to be quoted before summarising produced a run where
the model printed a file's contents, labelled them "the verbatim directory
listing", and never listed the directory.

The path-not-contents rule for reviewers, and mechanical records over
self-reports, carried into [antfarm-v2](../antfarm-v2), which checks claimed
actions against the tool log.

## Status

Dormant. The results table in `evals/tasks.md` was never filled in.
`notes/INDEX.md` is stale. `researcher.md` still declares `WebSearch` and
`WebFetch`, which breaks it on an Ollama backend; remove them before use.

MIT licensed.
