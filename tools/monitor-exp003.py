#!/usr/bin/env python3
import datetime, json, os, re, subprocess, sys, time
from pathlib import Path

server_pid = int(sys.argv[1])
request_pid = int(sys.argv[2])
out_path = Path(sys.argv[3])
interval = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0

def run(cmd):
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=12).stdout
    except Exception as exc:
        return "ERR " + repr(exc)

def ps_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def parse_int(text, pattern):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None

with out_path.open("w") as out:
    started = time.time()
    while time.time() - started < 900:
        request_alive = ps_alive(request_pid)
        footprint = run(["footprint", "-p", str(server_pid), "-f", "bytes", "--noCategories"])
        ps = run(["ps", "-p", str(server_pid), "-o", "rss=,pcpu="]).strip()
        io = run(["ioreg", "-l", "-w0", "-r", "-c", "IOAccelerator"])
        memory_pressure = run(["memory_pressure", "-Q"])
        swap = run(["sysctl", "vm.swapusage"])
        record = {
            "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "request_alive": request_alive,
            "footprint_raw": footprint,
            "ps_raw": ps,
            "io_alloc_system_memory_bytes": parse_int(io, r'"Alloc system memory"=([0-9]+)'),
            "io_in_use_system_memory_bytes": parse_int(io, r'"In use system memory"=([0-9]+)'),
            "memory_pressure_raw": memory_pressure,
            "swap_raw": swap,
        }
        out.write(json.dumps(record) + "\n")
        out.flush()
        if not request_alive:
            break
        time.sleep(interval)
