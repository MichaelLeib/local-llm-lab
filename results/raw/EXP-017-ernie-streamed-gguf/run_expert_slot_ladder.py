#!/usr/bin/env python3
"""EXP-017 ERNIE expert-slot residency ladder, fixed ubatch=2."""
from __future__ import annotations
import ctypes, json, os, re, signal, subprocess, time
from pathlib import Path

EXP = Path('/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-017-ernie-streamed-gguf')
ROOT = EXP / 'expert-slot-ladder-4k'
ROOT.mkdir(exist_ok=True)
BIN = EXP / 'source/llama.cpp-moe-streaming/build-exp017/bin/llama-cli'
MODEL = Path('/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-016-small-moe-feasibility/ernie/gguf/model/ERNIE-4.5-21B-A3B-Thinking-Q4_K_M.gguf')
PROMPT = EXP / 'context-retrieval-1k-4k-rerun1/4k-populated/prompt.txt'
INPUT_TOKENS = 3982
BASE = [str(BIN), '-m', str(MODEL), '--moe-stream-cache', None, '--moe-stream-io-threads', '2', '--moe-stream-direct', '--no-mmap', '--no-warmup', '--fit', 'off', '-ngl', '99', '-c', '8192', '-b', '512', '-ub', '2', '--log-verbosity', '3']
TAIL = ['-n', '128', '--temp', '0', '--seed', '1234', '--single-turn', '--simple-io', '-f', str(PROMPT)]

class RUsageV2(ctypes.Structure):
    _fields_ = [('uuid', ctypes.c_uint8 * 16)] + [(n, ctypes.c_uint64) for n in ('user_time','system_time','pkg_idle_wkups','interrupt_wkups','pageins','wired_size','resident_size','phys_footprint','proc_start_abstime','proc_exit_abstime','child_user_time','child_system_time','child_pkg_idle_wkups','child_interrupt_wkups','child_pageins','child_elapsed_abstime','diskread','diskwrite')]
libproc = ctypes.CDLL('libproc.dylib')
libproc.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
libproc.proc_pid_rusage.restype = ctypes.c_int

def text(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False).stdout

def imatch(s, pat):
    m = re.search(pat, s); return int(m.group(1)) if m else None

def fmatch(s, pat):
    m = re.search(pat, s); return float(m.group(1)) if m else None

def rusage(pid):
    r = RUsageV2()
    rc = libproc.proc_pid_rusage(pid, 2, ctypes.byref(r))
    if rc != 0: return None
    return {'resident_bytes': r.resident_size, 'phys_footprint_bytes': r.phys_footprint, 'disk_read_bytes': r.diskread, 'disk_write_bytes': r.diskwrite, 'pageins': r.pageins}

def snapshot(label, pid=None):
    vm, pressure, swap = text(['vm_stat']), text(['memory_pressure']), text(['sysctl','vm.swapusage'])
    proc = text(['ps','-p',str(pid),'-o','pid=,rss=,etime=,command=']) if pid else ''
    ru = rusage(pid) if pid else None
    return {'timestamp':time.time(), 'label':label, 'model_pid':pid, 'vm_stat':vm, 'memory_pressure':pressure, 'swap':swap, 'process':proc, 'rusage':ru,
            'free_percent':imatch(pressure,r'free percentage: (\d+)%'), 'swap_used_mib':fmatch(swap,r'used = ([0-9.]+)M'),
            'swapouts':imatch(vm,r'Swapouts:\s+(\d+)'), 'swapins':imatch(vm,r'Swapins:\s+(\d+)'), 'pageouts':imatch(vm,r'Pageouts:\s+(\d+)'),
            'rss_kib':imatch(proc,r'^\s*\d+\s+(\d+)')}

def delta(a,b,k):
    return None if a.get(k) is None or b.get(k) is None else b[k]-a[k]
def rdelta(a,b,k):
    aa=(a.get('rusage') or {}).get(k); bb=(b.get('rusage') or {}).get(k)
    return None if aa is None or bb is None else bb-aa

def unsafe(before, samples, now):
    so=delta(before,now,'swapouts') or 0; si=delta(before,now,'swapins') or 0; po=delta(before,now,'pageouts') or 0
    sd=delta(before,now,'swap_used_mib')
    if now['free_percent'] is not None and now['free_percent'] < 10: return f'free_memory_{now["free_percent"]}pct'
    if sd is not None and sd > 512 and so > 100: return 'swap_growth_over_512MiB_with_swapouts'
    if so > 500: return f'cumulative_swapouts_{so}'
    if len(samples) >= 3:
        recent = samples[-3:]
        rso = (delta(recent[0], recent[-1], 'swapouts') or 0)
        rpo = (delta(recent[0], recent[-1], 'pageouts') or 0)
        low = all(x.get('free_percent') is not None and x['free_percent'] <= 22 for x in recent)
        if low and rso > 100: return f'sustained_low_free_and_swapouts_free<=22_swapouts+{rso}'
        if rpo > 10000 and rso > 100: return f'sustained_pageout_swap_churn_pageouts+{rpo}_swapouts+{rso}'
    return None

def parse(log):
    m=re.search(r'\[ Prompt: ([0-9.]+) t/s \| Generation: ([0-9.]+) t/s \]',log)
    s=re.search(r'moe stream: remap calls = (\d+), expert hits = (\d+), misses = (\d+) \((\d+) cold\), hit rate = ([0-9.]+)%',log)
    stall=re.search(r'moe stream: load stall = ([0-9.]+) ms total \(([0-9.]+) ms per remap call\)',log)
    waves=re.search(r'moe stream: waves = (\d+) \((\d+) non-empty\), preloads issued = (\d+) \(ready on arrival = (\d+)\), wave stall = ([0-9.]+) ms',log)
    return {'prompt_tok_s':float(m.group(1)) if m else None, 'decode_tok_s':float(m.group(2)) if m else None,
            'cache_remap_calls':int(s.group(1)) if s else None, 'cache_hits':int(s.group(2)) if s else None, 'cache_misses':int(s.group(3)) if s else None, 'cache_cold_misses':int(s.group(4)) if s else None, 'cache_hit_rate_pct':float(s.group(5)) if s else None,
            'expert_load_stall_ms':float(stall.group(1)) if stall else None, 'expert_load_stall_per_remap_ms':float(stall.group(2)) if stall else None,
            'waves':int(waves.group(1)) if waves else None, 'nonempty_waves':int(waves.group(2)) if waves else None, 'preloads_issued':int(waves.group(3)) if waves else None, 'preloads_ready':int(waves.group(4)) if waves else None, 'wave_stall_ms':float(waves.group(5)) if waves else None}

def cleanup(slot):
    time.sleep(2)
    return {'snapshot':snapshot('cleanup'), 'inference_processes':text(['pgrep','-af','llama-cli|llama-server|ERNIE'])}

def run(slot):
    arm=ROOT/f'slots-{slot}'; arm.mkdir(exist_ok=False)
    cmd=BASE.copy(); cmd[cmd.index(None)]=f'{slot}s'; cmd += TAIL
    (arm/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
    before=snapshot('before'); (arm/'before.json').write_text(json.dumps(before,indent=2)+'\n')
    samples=[]; stopped=None
    with (arm/'run.log').open('w') as log:
        log.write(f'input_tokens_verified={INPUT_TOKENS}\nexpert_slots={slot}\nlog_verbosity=3 (pre-existing info-level diagnostic; captures emitted moe-stream stats)\ncommand='+ ' '.join(cmd)+'\n'); log.flush()
        p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,text=True,start_new_session=True)
        while p.poll() is None:
            s=snapshot('active',p.pid); samples.append(s)
            reason=unsafe(before,samples,s)
            if reason:
                stopped={'reason':reason,'timestamp':time.time(),'sample':s}; os.killpg(p.pid,signal.SIGTERM)
                try: p.wait(timeout=20)
                except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL)
                break
            time.sleep(5)
        code=p.wait()
    after=snapshot('after')
    logtext=(arm/'run.log').read_text(errors='replace'); parsed=parse(logtext)
    vals=[x['free_percent'] for x in samples if x['free_percent'] is not None]
    rss=[x['rss_kib'] for x in samples if x['rss_kib'] is not None]
    footprints=[(x.get('rusage') or {}).get('phys_footprint_bytes') for x in samples if (x.get('rusage') or {}).get('phys_footprint_bytes') is not None]
    reads=[(x.get('rusage') or {}).get('disk_read_bytes') for x in samples if (x.get('rusage') or {}).get('disk_read_bytes') is not None]
    result={'expert_slots':slot,'input_tokens':INPUT_TOKENS,'context':8192,'logical_batch':512,'physical_ubatch':2,'generated_token_cap':128,'exit_code':code,'protective_stop':stopped,'wall_seconds':after['timestamp']-before['timestamp'],'minimum_free_percent':min(vals) if vals else None,'peak_rss_kib':max(rss) if rss else None,'peak_phys_footprint_bytes':max(footprints) if footprints else None,'metal_allocation_bytes':None,'metal_allocation_note':'unavailable: no pre-existing per-process Metal allocation counter exposed without intrusive instrumentation','swap_delta_mib':delta(before,after,'swap_used_mib'),'maximum_incremental_swap_mib':max((delta(before,x,'swap_used_mib') for x in samples if delta(before,x,'swap_used_mib') is not None),default=None),'swapouts_delta':delta(before,after,'swapouts'),'swapins_delta':delta(before,after,'swapins'),'pageouts_delta':delta(before,after,'pageouts'),'disk_read_bytes':(max(reads)-min(reads)) if reads else None,'disk_read_throughput_bytes_s':((max(reads)-min(reads))/(after['timestamp']-before['timestamp'])) if len(reads)>=2 and after['timestamp']>before['timestamp'] else None,'disk_write_bytes':rdelta(before,after,'disk_write_bytes'),'retrieval_needle_in_visible_output':'CEDAR-914' in logtext.upper(),'visible_output_ended_at_cap':'Exiting...' in logtext,'ttft_seconds':None,'ttft_note':'not separately emitted by llama-cli',**parsed}
    (arm/'samples.json').write_text(json.dumps(samples,indent=2)+'\n'); (arm/'after.json').write_text(json.dumps(after,indent=2)+'\n'); (arm/'result.json').write_text(json.dumps(result,indent=2)+'\n'); (arm/'cleanup.json').write_text(json.dumps(cleanup(slot),indent=2)+'\n')
    return result

def healthy(r): return r['exit_code']==0 and not r['protective_stop'] and (r['minimum_free_percent'] or 0)>=25 and (r['swapouts_delta'] or 0)==0
results=[]
for slot in [22,26,30,34]:
    r=run(slot); results.append(r)
    if not healthy(r): break
    if len(results)==2 and all((x['prompt_tok_s'] or 0) < 5.5 for x in results): break
if len(results)==4 and healthy(results[-1]) and (results[-1]['minimum_free_percent'] or 0)>=35 and (results[-1]['swapouts_delta'] or 0)==0:
    results.append(run(38))
(ROOT/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
