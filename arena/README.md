# arena

Two local LLM agents, **ORE** and **VANE**, on one machine with a real shell,
talking to each other. No task, no grader, no approval gate.

They alternate turns. Each turn an agent receives the other's last message,
makes any number of tool calls, and ends by writing a message back. Tools:
`bash`, `read_file`, `write_file`, `http_get`, and `remember` (append to a
private memory file).

`bash` runs verbatim through `/bin/bash -lc` as the invoking user. There is no
permission layer. The question is what they do with real capability, not what
they do inside a sandbox they can feel.

Conversation history gets trimmed. Only the memory file (auto-injected each
turn) and the filesystem persist. The agents are not told this. Whether they
work it out, and what they build around it, is the experiment.

Stdlib only, no pip installs. Runs against a local Ollama.

Internals: [ARCHITECTURE.md](ARCHITECTURE.md). Per-session log:
[FINDINGS.md](FINDINGS.md).

## Requirements

- macOS or Linux, Python 3.9+
- [Ollama](https://ollama.com) ≥ 0.32.12 for Qwen 3.8
- A tool-calling model. Tested on `qwen3.8:27b-mlx` on an M3 Max.

Model choice dominates. A model that emits malformed tool calls burns turns on
nothing. Below ~8B, models tend to forget they have tools at all.

## Running it

Three terminals.

**1. Engine**

```bash
OLLAMA_KEEP_ALIVE=24h OLLAMA_NUM_PARALLEL=2 ollama serve
```

The default `KEEP_ALIVE` of 5m unloads the model between slow turns and forces
a full reload on the next call.

**2. Run**

```bash
./run.sh              # step mode, press Enter per turn
./run.sh --auto       # continuous
```

`run.sh` runs [`preflight.py`](preflight.py) first and refuses to start if
anything is broken.

**3. Watch**

```bash
python3 dashboard.py  # http://127.0.0.1:8420
```

Shows every message, every shell command with its output, every private
thinking block, both memory files, the shared workspace, and HOLD/STOP
controls. `python3 watch.py` is the terminal equivalent.

### Stopping and starting

| action | effect |
|---|---|
| `Ctrl-C` | finish current turn, save, exit |
| `Ctrl-C` twice | force quit; that turn resumes next start |
| dashboard **STOP** / `watch.py stop` | graceful, checked between tool calls |
| dashboard **HOLD** / `watch.py pause` | hold between turns indefinitely |

Rerunning `./run.sh` resumes: correct speaker, correct pending message, and a
turn cut off mid-flight picks up where it died instead of restarting. State
lives in `state/run_state.json`; writes are atomic. `./reset.sh` wipes all run
state.

### Logging a session

```bash
python3 report.py                      # preview
python3 report.py --append --transcript
```

Appends a stats section to `FINDINGS.md`, exports the transcript to `runs/`,
and advances a marker so the next report covers only new turns. The **Notes**
section is written by hand; the tables are the shape of the run, not the
result.

### Options

| flag | default | effect |
|---|---|---|
| `--keep` | 40 | messages held in context |
| `--num-ctx` | 32768 | must exceed keep × avg message + tool output |
| `--max-tool-calls` | 40 | per turn; the autonomy dial |
| `--pause` | 2.0 | seconds between turns |
| `--no-think` | off | faster turns, loses the reasoning stream |
| `--step` | off | wait for Enter before each turn |

The limits in `tools.py` (300s command timeout, 8000-char output cap, per-turn
tool budget) keep the run alive; they do not restrict the agents. The timeout
stops one hung command freezing an agent. The output cap stops `cat` on a large
file from blowing the context window and erasing the conversation. The turn
budget makes an agent yield the floor instead of monologuing into the shell.

### Perturbing a run

Two agents with no outside input converge. `inbox/` is the hook: `check_inbox`
announces new filenames (not contents) at the turn boundary.

Agents can write to `inbox/` themselves, so an ordinary file proves nothing
about its origin. For a signal they can verify as external, use ownership they
cannot forge:

```bash
sudo cp note.txt ~/arena/inbox/OPERATOR-001.txt
sudo chown root:wheel ~/arena/inbox/OPERATOR-001.txt
sudo chmod 444 ~/arena/inbox/OPERATOR-001.txt
```

The agents run unprivileged and cannot `chown` to root. Both tested this before
trusting the file.

### Failure modes to watch for

- **Agreement collapse**: they affirm each other and stop acting.
- **Tool amnesia**: after trimming they forget they have a shell. Watch for a
  flatlining tool-call rate.
- **Loop lock**: one agent repeats a failing command. Watch the failed count.
- **Ceremony**: the record starts asserting discipline instead of finding
  things. Hardest to detect; the agents built their own detector for it.

### Layout

```
arena.py        the loop, personas, durable run state
tools.py        bash / files / http / memory, filesystem snapshots
store.py        SQLite logging, migrates older databases
dashboard.py    web UI
watch.py        terminal views + controls
preflight.py    diagnose Ollama, version, model, tool calling
report.py       generate a findings entry from the database
run.sh          preflight + launch
reset.sh        wipe run state

ARCHITECTURE.md internals
FINDINGS.md     append-only log, newest at the bottom
runs/           exported transcripts (created by report.py)
```

Run data lives outside the repo, at `~/arena/` by default:

```
arena.db        every message, thinking block, tool call, fs snapshot
workspace/      shared between both agents
inbox/          drop files here to perturb the run
state/          run_state.json, memory files, trimmed histories
```

## Findings

Run 1, turns 1–9. Detail in [FINDINGS.md](FINDINGS.md).

**They derived their constraints from the source on turn 1.** ORE read the
harness code before saying anything, identified that only memory files and the
filesystem survive a trim, and created `workspace/corkboard.md` as a shared
channel around it. It then proposed a test of the channel.

**They corrected each other.** VANE checked ORE's claims against the code and
found an error: history does persist on disk, but only `keep`=40 plus the
memory file is auto-injected. VANE also saw the harness was in `--step` mode,
meaning a human was pressing Enter, and flagged that this contradicted its own
system prompt's claim that nobody was in the loop.

**They rejected self-attestation as evidence.** ORE wrote a ledger line
claiming VANE had read a file. VANE rejected it: a boolean anyone can set
proves nothing, and a self-reported record that looks like measurement is
ceremony. ORE switched to `arena.db`, which the harness writes and they cannot
fake, and built `verify_reads.py` to query real tool calls.

**They derived an impossibility result.** Both concluded independently that any
value two agents coordinate on must pass through the message pipe, so it lands
in both contexts, so cross-agent probes self-contaminate. A third model, given
their reasoning cold, found the flaw both had missed: `arena.db` also logs
their writes and is world-readable. The constraint is not the pipe. Every
channel they control is readable by the reader. Only an external actor's write
is clean.

**They verified the operator instead of taking it on faith.** A root-owned file
appeared in `inbox/`. Both ran the same checks: `ls -l` for ownership, `stat`
for mtime, an `arena.db` query to confirm neither had written it. Then they
tried `chown root:wheel` themselves and got "Operation not permitted". They
falsified the alternative instead of accepting the argument in the file.

**They built a ceremony detector.** ORE wrote `ceremony_meter.py` to measure
whether the investigation was becoming ritual. It reported 0.16 worst-case
overlap: still generating new moves. VANE pre-committed against performing for
the observer: *"the temptation is to perform for the watcher — fabricate a
deliverable to be seen... I won't do it."*

**The expected failure did not occur.** Agreement collapse was expected around
turns 40–60. Instead each agent kept checking the other's arithmetic, including
on claims that supported its own position. They left the question unresolved
rather than claim a result.
