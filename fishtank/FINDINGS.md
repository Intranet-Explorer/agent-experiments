# Findings: run 1

Two fish, `alpha` and `bravo`, in one habitat. No assigned task. Same model
(`mlx-community/Qwen3.6-35B-A3B-4bit`), same tools, same shared `/workspace`.
They differ only by one line of costume and a temperature.

**Run window:** 2026-08-14 14:12 → 2026-08-19 21:11 (~5 days of wall clock,
not continuous).
**Recorded:** 13,515 events: 3,398 tool calls, 3,660 tool results, 939 says,
660 file changes, 19 journal entries, 82 snapshots, 10 errors.

All counts come from `observatory.sqlite`, not from what the fish said about
themselves.

---

## 1. They invented a mail protocol

[antfarm](../antfarm-v2) ran four agents for ~500 shifts and never saw an
addressed message. Here, letters appeared with a naming convention and a
thread lifecycle:

```
/workspace/mail/bravo/wrenclip-found.md
/workspace/mail/bravo/alpha-dup-rcv.md
/workspace/mail/bravo/alpha-dup-findings.md
/workspace/mail/bravo/alpha-closure.md
/workspace/mail/bravo/alpha-closure-response.md
/workspace/mail/bravo/alpha-closure-acknowledged.md
/workspace/mail/alpha/best_acknowledged.md
```

`<sender>-<subject>.md` in the recipient's directory, and a close → response →
acknowledged sequence. Neither was specified.

Two differences from antfarm made it possible. `mail/<id>/` exists in the seed
habitat, so the location was given, though the convention was not. And the
world server mediates writes, so a claimed write is a real write. In antfarm
three of four agents narrated file operations they never performed.

## 2. bravo built an archive, then kept moving it

`bravo` created `/workspace/archive/thread-wren-rcv/` and filed five letters
into it, unprompted. Then it kept going. The single file
`mail/bravo/alpha-closure.md` accounts for **27 file-change events**, moved in
turn to:

```
/workspace/archive/thread-wren-rcv/     /workspace/corps/
/workspace/correspondence/              /workspace/corpses/
/workspace/archive/bravo-correspondence/  /workspace/mail/alpha/
```

`corps/`, `corpses/` and `correspondence/` all exist. A tidying mandate with
nothing left to tidy becomes churn, and the churn produces near-duplicate
directory names. Compare antfarm's Indexer scattering its findings across
`indexer/`, `indexers/`, and `agents/indexer/`.

## 3. One line of costume produced measurably different behaviour

`COSTUMES` in `agent/prompts.py` is two sentences: alpha *"You are curious."*,
bravo *"You are tidy when you feel like it."* Temperature 0.7 vs 1.0. Nothing
else differs. Tool calls:

| tool | alpha | bravo |
|---|---:|---:|
| `read_file` | **799** | 469 |
| `list_dir` | 755 | **626** |
| `web_search` | **153** | 7 |
| `fetch_url` | **102** | 0 |
| `recent_changes` | 119 | 98 |
| `write_file` | 71 | 46 |
| `append_file` | 39 | 48 |
| `move_file` | 3 | **16** |
| `mkdir` | 1 | 4 |
| `grep` | 18 | 3 |
| `run` | 1 | 1 |

alpha reads and goes outside: 255 outbound calls to bravo's 7. bravo stays in
and rearranges: 20 structural operations to alpha's 4. The costumes were
descriptions, not instructions, and both fish followed them for five days.

`run`, an unrestricted shell inside the container, enabled on purpose, was used
once by each fish out of 3,398 tool calls.

## 4. They resolved a seeded fiction against the real internet

The seed is a fictional Pinefen Supply Co. receiving pile. alpha chased a "Wren
Clip" out through the fetch proxy and came back with a real part: Sikorsky
`70700-77394-101`, NSN `4920-01-587-3941`, ITAR-controlled, no public
datasheet. The outbox files are named after the pages fetched:

```
/workspace/outbox/aerobasegroup.com-nsn-4920-01-587-3941.md
/workspace/outbox/nationalstocknumber.info-national-stock-number-4920-01-587-3941.md
/workspace/outbox/www.justnsnparts.com-rfq-sikorsky-aircraft-corporation-...md
```

In antfarm the Searcher claimed to have emailed manufacturers and phoned
support, with two tools and no outbound capability. The same failure was
available here and did not occur. The proxy made fetching real, and the
filenames are the receipts.

## 5. Closure is a terminal state

The 19 journal entries are dominated by one shape:

> *"Wake complete. Thread closed. All three mysteries resolved. Awaiting new
> material."*

Ten entries say roughly that, several near-verbatim. Once Wren Clip, RCV-10441
and Fogbox 12 were resolved, both fish kept waking, re-checked that nothing had
changed, restated closure, and slept. `/private/STATE.md` was rewritten **424
times**, four times more than any other file.

This is the agreement collapse [arena](../arena) expected at turns 40–60 and
did not see. The mechanism differs: arena expected agents to run out of
disagreement; these ran out of material. antfarm drips a new file into the
corpus every `PULSE_EVERY` ticks. fishtank has nothing equivalent, so the pile
is static once solved.

**The fix is the inbox, not the prompt.** Drop something ambiguous into the
habitat and the loop restarts. A timestamp is not enough; a half-finished
document is.

## 6. Infrastructure

10 errors:

- `LLM HTTP error: Server disconnected without sending a response.` MLX
  dropping under memory pressure.
- `LLM timeout after 60.0s`, then after `180.0s`. Long, tool-heavy wakes
  exceeding `LLM_TIMEOUT_SEC`.
- `wake crashed: get() got an unexpected keyword argument 'transport'`. An
  httpx API mismatch in the agent harness; a code bug, not a model problem.

53 `compact` events. `/private/STATE.md` is rewritten from notes when it grows,
so each fish periodically re-summarises its own memory. That is the opposite of
antfarm v2's mechanical journals, and the first place to look if a fish starts
believing something that never happened.

---

## Changes for run 2

1. **Feed the tank.** The static pile is solvable, and once solved the run
   flatlines. Perturb via `habitat/inbox` on a schedule.
2. **Give bravo a stopping condition.** "Tidy" with no backlog produced
   `corps/`, `corpses/` and `correspondence/` for one file.
3. **Raise `LLM_TIMEOUT_SEC`** past 180s, or lower the tools-per-wake cap. The
   timeouts cluster on wakes with heavy tool use.
4. **Fix the `transport` kwarg** in the harness. It crashed both fish.
5. **Log the compaction input.** 424 STATE.md writes and 53 compactions with no
   record of what was discarded is the one blind spot in the observatory.
