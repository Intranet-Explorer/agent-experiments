#!/usr/bin/env python3
"""Isolate where local-model latency actually goes.

Runs a 2x2: small vs large system prompt, thinking on vs off.
Reports wall time plus Ollama's own token counters so prefill and
generation can be told apart.

Models with no reasoning mode reject `think` with HTTP 400. That is a
result, not an error: it means the 20x thinking penalty cannot apply.

Usage:  python3 evals/latency_matrix.py [model]
"""
import json, sys, time, urllib.error, urllib.request

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3:8b"
URL = "http://localhost:11434/api/chat"
BIG = "You are an agent. Follow all rules carefully. " * 400  # ~4k tokens


def post(payload):
    req = urllib.request.Request(
        URL, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    t = time.time()
    d = json.load(urllib.request.urlopen(req))
    return d, time.time() - t


def run(label, system, think):
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": "Say ok."}]
    payload = {"model": MODEL, "stream": False, "messages": msgs}
    if think is not None:
        payload["think"] = think
    try:
        d, el = post(payload)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:80].replace("\n", " ")
        print(f"{label:<28} {'--':>7}   HTTP {e.code}: {body}")
        return None
    m = d["message"]
    ns = lambda k: d.get(k, 0) / 1e9
    pc, ec = d.get("prompt_eval_count", 0), d.get("eval_count", 0)
    pd, ed = ns("prompt_eval_duration"), ns("eval_duration")
    rate = lambda n, s: f"{n/s:,.0f}t/s" if s > 0.01 else "cached"
    print(f"{label:<28} {el:7.2f}s  "
          f"prefill={pd:5.2f}s({pc:>5}tok {rate(pc,pd):>8})  "
          f"gen={ed:5.2f}s({ec:>5}tok {rate(ec,ed):>8})  "
          f"think={len(m.get('thinking') or ''):>5}ch")
    return True


print(f"model: {MODEL}\n")
print(f"{'case':<28} {'wall':>8}  {'prefill':>32}  {'generate':>30}  {'thinking':>9}")
print("-" * 118)

supports_think = run("small prompt, think ON", None, True)
if supports_think:
    run("small prompt, think OFF", None, False)
    run("4k prompt,   think ON",   BIG,  True)
    run("4k prompt,   think OFF",  BIG,  False)
else:
    print("\n-> model has no reasoning mode; rerunning without the think field\n")
    run("small prompt (no think)", None, None)
    run("4k prompt   (no think)",  BIG,  None)
    run("4k prompt   (repeat)",    BIG,  None)

print("\nNOTE: a prefill row showing 'cached' is a KV cache hit on a repeated"
      "\nprompt, not a real measurement. Compare only cold rows.")
