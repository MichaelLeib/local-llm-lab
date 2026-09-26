#!/usr/bin/env python3
"""Generate an actually token-counted retrieval corpus using llama-server's tokenizer."""
import argparse, json, pathlib, urllib.request

p = argparse.ArgumentParser()
p.add_argument('--url', default='http://127.0.0.1:8926')
p.add_argument('--target', type=int, required=True)
p.add_argument('--output', required=True)
a = p.parse_args()

def tokens(text):
    req = urllib.request.Request(a.url + '/tokenize', data=json.dumps({'content': text}).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return len(json.load(r)['tokens'])

facts = [('EARLY','ORCHID-4917'), ('MIDDLE','LANTERN-8253'), ('LATE','CIRRUS-6408')]
base = 'Read the following archive exactly. At the end, reply only as JSON with keys early, middle, late and the three exact fact codes.\n\n'
def assemble(nblocks):
    fact_at = {int(nblocks * frac): pair for frac, pair in zip((.20,.50,.80), facts)}
    parts=[base]
    for i in range(nblocks):
        if i in fact_at:
            name, value = fact_at[i]
            parts.append(f'\nFACT_{name}: {value}. Memorize this exact code.\n')
        parts.append(f'Archive segment {i:05d}: The quiet river passes stones under a cobalt sky; record {i:05d} is ordinary operational prose with no secret answer.\n')
    return ''.join(parts) + '\n\nReturn the requested JSON now.'
# Tokenize only O(log n) full candidates, avoiding a context-sized request per block.
lo, hi = 0, max(100, a.target // 4)
while tokens(assemble(hi)) < a.target - 256:
    lo, hi = hi, hi * 2
while lo + 1 < hi:
    mid = (lo + hi) // 2
    if tokens(assemble(mid)) <= a.target - 256:
        lo = mid
    else:
        hi = mid
text=assemble(lo)
n = tokens(text)
path=pathlib.Path(a.output); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text)
(path.with_suffix('.json')).write_text(json.dumps({'target_context':a.target,'actual_prompt_tokens':n,'facts':dict(facts)},indent=2))
print(json.dumps({'prompt_tokens':n,'output':str(path)}))
