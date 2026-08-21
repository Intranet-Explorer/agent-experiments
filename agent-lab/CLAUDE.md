# Agent Lab

A sandbox for learning multi-agent coordination against local models.
This file is read on every run. **When an agent misbehaves, add a line here.**
That is the primary feedback loop of this project.

## Setup

- Runtime: Ollama on `localhost:11434` (MLX backend, Apple Silicon)
- Default worker model: `qwen3-coder`
- Fast/cheap model: `qwen3-coder` (see 2026-08-10 measurement; the 8B is NOT cheaper)
- Escalation model (not yet pulled): `glm-4.7:cloud`

## Shared state

`notes/` is the blackboard. Any agent may read it; agents write only to their
own topic files. `notes/INDEX.md` is maintained by the `librarian` agent - do
not hand-edit it.

## Standing rules

- Prefer delegating to a specialist subagent over doing specialist work inline.
- No claim without a source. Local models hallucinate confidently; assume it.
- Never mark work done that you have not verified by running or reading it.
- Stop and report after 3 failed attempts at the same problem. Do not loop.
- Small models get small jobs - BUT verify 'small' means faster here. On this
  stack a 30B MoE beats an 8B dense model on both prefill and thinking cost.
- Keep responses short. Context is the scarcest resource on a local model.
- When reporting directory contents, quote the raw tool output verbatim before
  summarizing. Never describe a file you have not seen in a listing.
- Do not offer follow-ups that presuppose content you just showed does not exist.
- Answer once. Never repeat a summary you already gave in the same turn.
- List a directory before reading it; never Read a path that may be a directory.
- If a file lands at a different path or name than requested, report it as a
  failure and fix it. Never mention the deviation in passing and claim success.
- When delegating a review, pass the FILE PATH only. Never paste the artifact's
  contents into the subagent's prompt - a reviewer given the text will review
  from context instead of reading, and its verdict will not survive contact with
  the real file. Measured 2026-08-12: path-only found a real bug that
  contents-pasted missed, and dropped a fabricated one.

## Delegation map

| Need | Agent |
|---|---|
| Outside facts | `researcher` |
| Review before accepting | `critic` |
| Code, scripts, config | `builder` |
| Tidy `notes/` | `librarian` |

## Lessons learned

<!-- Append one line per failure observed. Date them. Never delete. -->

- 2026-08-10 - Lab created. No lessons yet.
- 2026-08-10 - qwen3:8b invented a file named `empty` in notes/ by misreading the
  italic placeholder text inside INDEX.md as a directory entry, then invented a
  purpose for it. Tool output was correct; the narration was not. RULE: when
  reporting directory contents, quote the raw tool output verbatim before
  summarizing it. Never describe a file you have not seen in a listing.
- 2026-08-10 - Latency baseline: qwen3:8b, simple 2-tool request = ~1m50s cold
  AND ~1m47s warm. Model load is NOT the cost; thinking tokens plus the harness
  system prompt are. Expect minutes, not seconds. A slow response is not a hung
  one. (Corrects an earlier guess that blamed cold start.)
- 2026-08-10 - The verbatim-quoting rule above WORKED on the next run: same
  prompt, no invented file. Config-only fixes to hallucination are viable.
- 2026-08-10 - qwen3:8b still closed with "Would you like to explore other files
  in notes/?" immediately after correctly reporting that notes/ holds exactly one
  file. RULE: do not offer follow-ups that presuppose content you just showed
  does not exist.
- 2026-08-10 - PREDICTION FALSIFIED: adding `/no_think` to standing rules did not
  change turn time (1m54s vs 1m47s). Either the soft switch is not reaching the
  model through the harness, or thinking tokens were never the dominant cost.
  Do not assume a Qwen soft switch works just because it is documented.
- 2026-08-10 - The verbatim-quoting rule BACKFIRED on run 3. qwen3:8b printed the
  CONTENTS of INDEX.md and labelled it "the verbatim directory listing" - correct
  ritual, wrong artifact - and never listed the directory at all. Adding a rule to
  a small model can buy the SHAPE of compliance without the substance. Check that
  a rule changed the behaviour, not just the vocabulary.
- 2026-08-10 - OPEN QUESTION: "Thought for 1m54s" in the harness may be total turn
  time, not thinking time. Measure latency at the Ollama layer before tuning
  prompts against it.
- 2026-08-10 - MEASURED AT THE OLLAMA LAYER. "List three colors", qwen3:8b,
  100% GPU, ctx 40960:
    think default (on): 8.57s, 2248 chars of thinking
    "think": false    : 0.42s, 0 chars of thinking
    identical final answer both times.
  Thinking costs 20x on a trivial prompt. The API flag WORKS; the `/no_think`
  prompt line does NOT reach the model through Claude Code. Fix belongs at the
  Ollama layer, not in this file.
- 2026-08-10 - CAUTION, do not overread the above: 2248 chars is ~600 tokens,
  roughly 8s. The harness turn was 114s. Thinking cannot be the whole story.
  Something else - prefill of the harness system prompt, multiple round trips per
  turn, or far longer traces on agentic prompts - accounts for the rest.
  UNRESOLVED.
- 2026-08-10 - `ollama create` with `PARAMETER think false` fails: "unknown
  parameter 'think'". There is NO Modelfile-level thinking switch. Thinking is
  per-request only, and Claude Code cannot send that field through the Anthropic
  compat endpoint. Therefore: on a hybrid reasoning model, thinking cannot be
  turned off from inside this lab's config. Pick a non-thinking model instead.
- 2026-08-10 - RESOLVED, the 114s turn. Measured on qwen3:8b, 100% GPU:
    prefill    = 665 tok/s  (4019 tok in 6.04s)
    generation =  59 tok/s  (195 tok in 3.31s)
  (The 0.09s prefill row in the matrix is a KV cache hit on a repeated prompt,
  not a real measurement. Do not cite it.)
  Claude Code sends 15k+ tokens of system prompt + tool schemas + CLAUDE.md +
  agent descriptions. At 665 tok/s that is ~23s of prefill PER MODEL CALL, and a
  tool-using turn costs at least two calls, plus a thinking trace at 59 tok/s.
  That is the ~114s. No single cause; it is prefill x round trips + thinking.
- 2026-08-10 - THE STRUCTURAL PROBLEM: Ollama's Anthropic compat endpoint does
  not support prompt caching (documented gap). Every turn re-prefills the whole
  conversation from scratch. PREDICTION: turn time grows linearly with
  conversation length and never recovers. Test before trusting.
- 2026-08-10 - CONSEQUENCE FOR DESIGN: long single-session agent conversations are
  the worst possible shape for this stack. Prefer many short sessions over one
  long one. Keep CLAUDE.md and agent descriptions SHORT - every word is re-billed
  at 665 tok/s on every single turn. Verbosity here has a measurable time cost.
- 2026-08-10 - `qwen3-coder` REJECTS `"think": true` with HTTP 400. It is a pure
  instruct model with no reasoning mode, so the 20x thinking penalty cannot apply
  to it at all. Ollama only accepts the `think` field on thinking-capable models
  (qwen3, gpt-oss, deepseek-r1). An HTTP 400 here is a capability answer, not a
  bug. evals/latency_matrix.py now treats it as such.
- 2026-08-10 - MEASURED qwen3-coder vs qwen3:8b. qwen3-coder WINS ON BOTH AXES:
    prefill:  1,073 t/s  vs   665 t/s   (MoE: ~30B total, few B active per token)
    thinking: impossible vs  20x tax on trivial calls
  A 30B MoE is cheaper to run here than an 8B dense model. "Bigger model = slower"
  is FALSE on this stack. Params are the wrong unit; active params are the right
  one. qwen3-coder is now the default for every agent, including the librarian.
- 2026-08-10 - What a real cold start looks like: qwen3-coder first call = 13.13s
  wall but only 0.07s prefill + 0.03s gen. The gap is ~19GB loading off disk.
  When wall >> prefill+gen, that is model load. When wall ~= prefill+gen, it is
  not. This is the check I failed to make on run 1.
- 2026-08-10 - PREDICTION: at 1,073 t/s prefill and no thinking, a ~15k-token
  Claude Code turn should cost ~14s per model call, ~30s for a 2-call tool turn -
  down from 114s. Test by rerunning the notes/ prompt on qwen3-coder.
- 2026-08-10 - TRAP: ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN are per-shell. A
  new terminal tab loses them, Claude Code silently falls back to the real
  Anthropic API and asks you to sign in. Any latency measured in that session is
  cloud Claude, NOT the local model. Always launch via the `claude-local` alias,
  and check /status before trusting a timing.
- 2026-08-11 - qwen3-coder on the notes/ prompt: CORRECT, no invented file, and NO
  thinking trace at all. Recovered on its own from an EISDIR error (tried to Read
  a directory, then switched to a listing). Strictly better than qwen3:8b here.
- 2026-08-11 - NEW FAILURE, qwen3-coder: printed its entire summary paragraph
  TWICE, verbatim, in one turn. Also used 4 tool calls (read, read, list, read)
  for a 2-call job. On a stack with no prompt caching, redundant calls and
  duplicated output are paid for in seconds. RULE: answer once. Do not repeat a
  summary you have already given in the same turn.
- 2026-08-11 - RULE: before reading a path, know whether it is a file or a
  directory. Do not Read a directory and recover from EISDIR - list it first.
- 2026-08-11 - PREDICTION FALSIFIED, and this one matters. Predicted ~30s for the
  notes/ prompt on qwen3-coder. MEASURED 1m55s - the same as qwen3:8b's 1m47s.
  Removing the 20x thinking tax AND running 1.6x faster prefill changed the turn
  time by NOTHING. Therefore the ~114s is NOT model-bound. Something in the
  harness dominates both models.
  Ruled out so far: thinking tokens, model size, prefill throughput, GPU
  offload, cold start.
  Still live: number of model round trips per turn, true prompt size per call
  (may be far larger than the 15k I assumed), per-request overhead in the
  Anthropic compat layer, streaming behaviour.
  NEXT: count actual requests and prompt_eval_count per turn in Ollama's logs.
  Do not tune anything else until that number exists.
- 2026-08-11 - METHOD NOTE: three predictions made today, two falsified. Both
  falsifications came from measuring the harness instead of the model. The
  pattern: I keep optimising the layer I can see rather than the layer that
  costs. Measure first, at the layer where the time is actually spent.
- 2026-08-11 - DELEGATION WORKS. builder -> librarian handoff succeeded on
  qwen3-coder: correct order, both agents invoked, script created executable and
  returns the right answer, INDEX.md updated. A 30B local model CAN hold a
  routing decision. This was the open question the whole lab existed to answer.
- 2026-08-11 - But: asked for `scripts/count_notes.sh`, got `count_notes.sh` in
  the repo root. The agent NOTICED the deviation, said so in passing, and still
  reported success. Noticing and shrugging is worse than not noticing. RULE: if
  the output path or name differs from what was asked, that is a FAILURE to
  report, not a footnote.
- 2026-08-11 - The librarian ignored the output format specified in its own agent
  file and invented one, then added a promise about future behaviour ("will
  update the count as new files are added"). Agent-file format specs are weakly
  binding on a local model. If format matters, give a literal template and say
  "copy this exactly".
- 2026-08-11 - CRITIC TEST FAILED, new failure class: ASYNC LIVELOCK.
  Sequence: orchestrator called the critic subagent -> "Invalid tool parameters"
  -> agent was BACKGROUNDED in a broken state and never returned -> orchestrator
  could not detect the stall -> it filled ~10 minutes with redundant tool calls
  it had already made, said "I'll wait for the critic", and then answered the
  question itself anyway. Killed manually at 9m48s.
  Root cause: qwen3-coder emitted malformed parameters for the subagent tool.
  Note the contrast with the builder->librarian test, which SUCCEEDED. Delegation
  is not reliably reproducible on this stack - it works sometimes.
  Also observed: visible text corruption in the output stream (words truncated
  mid-sentence). Unknown whether that is the model, the compat layer, or the TUI.
- 2026-08-11 - CONFOUND on the entry above: the Mac screen locked / may have
  slept during that run, which pauses inference. The ~10 minutes is therefore NOT
  clean evidence of a livelock, and the run resumed on wake. What IS still solid:
  the "Invalid tool parameters" error, the backgrounded agent, the redundant
  repeated tool calls, and the orchestrator answering inline while claiming to
  wait. The DURATION is unreliable. Disable sleep before timing anything:
  `caffeinate -dimsu` in a spare tab.
- 2026-08-11 - RULE CANDIDATE (untested): a subagent that has not returned is a
  FAILURE to report, not a reason to do the work inline. Never narrate waiting.
  Never re-run tool calls you have already made while waiting.
- 2026-08-11 - CRITIC RETEST, full trace. The real defect is the RETURN PATH, not
  delegation. Log shows `Agent "Review count_notes.sh script" finished - 8m 4s`,
  so the critic RAN and COMPLETED. Its output never reached the orchestrator.
  Downstream: orchestrator spawned a Monitor task (exited, no output), repeated
  its own analysis 5x near-verbatim, then APPROVED the script - "works
  correctly", "successfully fulfills its purpose" - on a task that explicitly
  required a review first. It never reported that the critic had failed.
  WORST CASE for a critic loop: reviewer vanishes silently, work ships approved.
  Standing rules gave zero protection here (violated 'answer once', 'never
  narrate waiting', 'report failures' simultaneously).
- 2026-08-11 - CONSEQUENCE: do not trust an unverified subagent result on this
  stack. If a critic's verdict is not visible in the transcript, treat the work
  as UNREVIEWED. Absence of criticism is not approval.
- 2026-08-11 - UNTESTED HYPOTHESIS for "Invalid tool parameters": critic.md
  declared WebSearch/WebFetch, which likely do not exist on the Ollama backend.
  builder and librarian - the two agents that WORKED - declare only local file
  tools. researcher still declares them and has never run successfully. Removed
  them from critic.md; needs a fresh session to test, as the running session had
  already loaded the old file.
- 2026-08-11 - HYPOTHESIS CONFIRMED. After removing WebSearch/WebFetch from
  critic.md and restarting: NO "Invalid tool parameters" error, and the critic
  ran in 20s and 14s instead of 8m. RULE: only declare tools in an agent file
  that actually exist on the current backend. Phantom tool names break the
  subagent call itself. Ollama has no WebSearch/WebFetch - remove them from
  researcher.md too before using it.
- 2026-08-11 - STILL BROKEN: the subagent's output does not reach the orchestrator
  even when the agent completes cleanly. Orchestrator again wrote the review
  itself - but this time it SAID SO ("I cannot wait for the critic subagent's
  results... I've provided my own review"), which is a real improvement over the
  previous run where it silently approved unreviewed work.
- 2026-08-11 - RECOVERY PATH FOUND: the harness writes each subagent's output to
  /private/tmp/claude-501/<project>/<session>/tasks/<agent-id>.output
  When a subagent result does not come back, read that file directly. The work is
  not lost, only the handoff.
- 2026-08-12 - CRITIC OUTPUT RECOVERED AND GRADED. Format bound PERFECTLY
  (exact BLOCKING/CONCERNS/VERIFIED). Contrast with the librarian, which ignored
  its format: critic.md supplies a LITERAL TEMPLATE in a code block, librarian.md
  described its format in prose. RULE CONFIRMED: literal templates bind, prose
  format specs do not.
- 2026-08-12 - CRITIC ACCURACY, graded against the real file:
    FOUND (real):   no check that notes/ exists; hidden files are counted
    INVENTED:       "security vulnerability - add quoting around the find output"
                    is FALSE. `count=$(...)` needs no quoting; spaces in
                    filenames do not affect `wc -l`. Cargo-culted shell advice
                    promoted to BLOCKING.
    MISSED:         the script uses the RELATIVE path `notes/`, so it silently
                    returns 0 when run from any other directory. The one defect
                    that actually matters.
  Score: 2 real, 1 fabricated, 1 miss. A critic that invents a BLOCKING issue is
  worse than no critic - it trains you to ignore it.
- 2026-08-12 - THE DEEPEST FINDING. Trace order: the critic tried to Read
  scripts/count_notes.sh -> "File does not exist" -> it produced its FULL review
  anyway from the script text pasted into its prompt -> was nudged -> globbed,
  found and read the real file -> emitted a BYTE-IDENTICAL review.
  Its verdict preceded its evidence and was unchanged by it. The tool calls were
  theatre. Same failure family as the "verbatim directory listing" run: correct
  ritual, no substance. In a critic this is the worst place for it, because the
  entire value is independent verification.
  RULE: never paste the artifact into the subagent prompt. Pass the PATH only,
  so the agent cannot review from context and must actually read the file.
- 2026-08-12 - PREDICTION CONFIRMED, and it is the best result of the lab so far.
  Same model, same critic.md, only the invocation changed (path only, contents
  NOT pasted). Review quality changed materially:
    FOUND this time:   "silently returns 0 when run from a directory other than
                        where notes/ exists" - the relative-path bug it MISSED
                        when handed the contents, and the defect that matters.
    DROPPED this time: the fabricated `count=$(...)` "security vulnerability".
  Withholding context from a reviewer IMPROVES the review. Give a critic the
  path, never the artifact. This is now a standing rule.
- 2026-08-12 - The orchestrator independently discovered the recovery path: when
  the subagent handoff failed it read the agent's .output file itself and
  extracted the review. Unprompted. Local models can adapt around harness bugs.
- 2026-08-12 - Still imperfect: one "Invalid tool parameters" on the first
  subagent attempt, which it retried successfully. Turn took 10m20s (screen sleep
  may again be a confound - run `caffeinate -dimsu` before timing).
