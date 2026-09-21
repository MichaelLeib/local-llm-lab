#!/usr/bin/env python3
"""Read-only Hub inspection and EXP-005 reference freeze for EXP-007."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path('/Users/<user>/HermesProjects/Local-LLM-Lab')
OUT = ROOT / 'results/raw/EXP-007'
SOURCE = OUT / 'source'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(parents=True, exist_ok=True)

UA = {'User-Agent': 'Local-LLM-Lab-EXP-007/1.0'}

def get_bytes(url, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), dict(r.headers), r.geturl()

def get_json(url):
    data, headers, final = get_bytes(url)
    return json.loads(data), headers, final

def safe_get(url, label):
    try:
        b, hdr, final = get_bytes(url)
        return {'ok': True, 'url': url, 'final_url': final, 'sha256': hashlib.sha256(b).hexdigest(),
                'bytes': len(b), 'text': b.decode('utf-8', 'replace')}
    except Exception as e:
        return {'ok': False, 'url': url, 'error': repr(e), 'label': label}

def model_api(repo):
    return get_json('https://huggingface.co/api/models/' + urllib.parse.quote(repo, safe='/'))[0]

def tree(repo, revision):
    url = 'https://huggingface.co/api/models/{}/tree/{}?recursive=true&expand=true'.format(
        urllib.parse.quote(repo, safe='/'), urllib.parse.quote(revision, safe=''))
    return get_json(url)[0]

def resolve(repo, revision, filename):
    return 'https://huggingface.co/{}/resolve/{}/{}'.format(repo, revision, filename)

def safetensors_header(repo, revision, filename):
    # Fetch only the 8-byte header length then the JSON header; never model tensor payload.
    url = resolve(repo, revision, filename)
    first, _, _ = get_bytes(url, {'Range': 'bytes=0-7'})
    if len(first) != 8:
        raise RuntimeError('expected 8 header-length bytes, got %d' % len(first))
    n = int.from_bytes(first, 'little')
    if n <= 0 or n > 100_000_000:
        raise RuntimeError('unsafe safetensors header length %d' % n)
    raw, _, _ = get_bytes(url, {'Range': 'bytes=8-%d' % (7+n)})
    if len(raw) != n:
        raise RuntimeError('expected %d header bytes, got %d' % (n, len(raw)))
    head = json.loads(raw)
    tensors = {k: {'dtype': v.get('dtype'), 'shape': v.get('shape'), 'offsets': v.get('data_offsets')}
               for k, v in head.items() if k != '__metadata__'}
    return {'file': filename, 'header_bytes': n, 'header_sha256': hashlib.sha256(raw).hexdigest(),
            'metadata': head.get('__metadata__', {}), 'tensor_count': len(tensors), 'tensors': tensors}

stock_repo = 'mlx-community/Qwen3.6-35B-A3B-4bit'
carnice_repo = 'samuelcardillo/Carnice-Qwen3.6-MoE-35B-A3B'
stock_rev = '38740b847e4cb78f352aba30aa41c76e08e6eb46'

stock_api = model_api(stock_repo)
carnice_api = model_api(carnice_repo)
carnice_rev = carnice_api.get('sha')
stock_tree = tree(stock_repo, stock_rev)
carnice_tree = tree(carnice_repo, carnice_rev)

# Keep an exact raw remote response set for reproducibility.
for name, obj in [('stock-api.json', stock_api), ('carnice-api.json', carnice_api),
                  ('stock-tree.json', stock_tree), ('carnice-tree.json', carnice_tree)]:
    (SOURCE / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')

files = ['config.json', 'generation_config.json', 'tokenizer_config.json', 'tokenizer.json', 'chat_template.jinja', 'README.md', 'adapter_config.json']
for stem, repo, rev in [('stock', stock_repo, stock_rev), ('carnice', carnice_repo, carnice_rev)]:
    d = SOURCE / stem
    d.mkdir(exist_ok=True)
    for f in files:
        record = safe_get(resolve(repo, rev, f), f)
        # Save response metadata; payload stored separately only for small textual source/config data.
        (d / (f.replace('/', '__') + '.meta.json')).write_text(json.dumps({k:v for k,v in record.items() if k != 'text'}, indent=2, sort_keys=True)+'\n')
        if record.get('ok') and f != 'tokenizer.json':
            (d / f.replace('/', '__')).write_text(record['text'])

# Identify safetensors files and obtain headers only. Cap to known shards; all results recorded.
def paths(t):
    return [x.get('path') for x in t if x.get('type') == 'file']
stock_paths, carnice_paths = paths(stock_tree), paths(carnice_tree)
stock_st = [p for p in stock_paths if p.endswith('.safetensors')]
carnice_st = [p for p in carnice_paths if p.endswith('.safetensors')]
headers, header_errors = {}, {}
for label, repo, rev, fs in [('stock', stock_repo, stock_rev, stock_st), ('carnice', carnice_repo, carnice_rev, carnice_st)]:
    headers[label] = []
    for f in fs:
        try:
            headers[label].append(safetensors_header(repo, rev, f))
        except Exception as e:
            header_errors.setdefault(label, []).append({'file': f, 'error': repr(e)})
(SOURCE / 'safetensors-headers.json').write_text(json.dumps({'headers':headers, 'errors':header_errors}, indent=2, sort_keys=True)+'\n')

# A fresh reference freeze contains checksums/pointers, not duplicated model data.
phase = json.loads((ROOT / 'results/raw/EXP-005/phase1-freeze.json').read_text())
verified = json.loads((ROOT / 'results/raw/EXP-005/model/qwen36.gturbo/verified-install.json').read_text())
prefill = json.loads((ROOT / 'results/raw/EXP-005/prefill-sweep-clean/summary.json').read_text())
hermes = json.loads((ROOT / 'results/raw/EXP-005/hermes-tool-test-clean-reboot-result.json').read_text())
kv = json.loads((ROOT / 'results/raw/EXP-005/kv-snapshot-clean/summary.json').read_text())
ref = {
 'experiment': 'EXP-007', 'phase': 'phase1_stock_reference_freeze',
 'created_at_utc': datetime.now(timezone.utc).isoformat(),
 'method': 'Pointer-and-checksum freeze: existing EXP-005 installation is neither copied nor modified.',
 'stock_runtime': phase['runtime'], 'stock_model': phase['model'],
 'stock_install_verification': {'path': 'results/raw/EXP-005/model/qwen36.gturbo/verified-install.json',
                                'manifest_sha256': verified['manifestSha256'],
                                'model_weights_sha256': verified['files']['model_weights.bin']['sha256'],
                                'all_expert_layer_sha256': {k:v['sha256'] for k,v in verified['files'].items() if k.startswith('packed_experts/layer_')},
                                'tokenizer_sha256': {k:v['sha256'] for k,v in verified['files'].items() if k.startswith('tokenizer/')}},
 'launch_and_api_contract': {'cli_baseline': {'expert_cache_slots': 16, 'max_context': 4096, 'temperature': 0, 'seed': 12345, 'prefill_chunk': 'auto'},
                             'server': phase['gate']['api'], 'prefix_cache': phase['gate']['persistent_kv'],
                             'isolated_profile': 'exp005'},
 'benchmarks': {'prefill_decode_clean': prefill, 'disk_kv_clean': kv, 'hermes_terminal_tool_clean': hermes},
 'source_artifacts': ['results/raw/EXP-005/phase1-freeze.json', 'results/raw/EXP-005/model/qwen36.gturbo/verified-install.json', 'results/raw/EXP-005/prefill-sweep-clean/summary.json', 'results/raw/EXP-005/kv-snapshot-clean/summary.json', 'results/raw/EXP-005/hermes-tool-test-clean-reboot-result.json'],
 'invariant': 'EXP-005 source/model/profile/defaults were not modified by this freeze.'
}
(OUT / 'stock-reference-freeze.json').write_text(json.dumps(ref, indent=2, sort_keys=True)+'\n')

summary = {'stock': {'repo':stock_repo, 'revision':stock_rev, 'api_sha':stock_api.get('sha'), 'safetensor_files':stock_st},
           'carnice': {'repo':carnice_repo, 'revision':carnice_rev, 'api_sha':carnice_api.get('sha'), 'safetensor_files':carnice_st},
           'headers_obtained': {k:len(v) for k,v in headers.items()}, 'header_errors': header_errors}
(OUT / 'metadata-acquisition-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
print(json.dumps(summary, indent=2))
