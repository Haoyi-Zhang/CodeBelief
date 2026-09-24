#!/usr/bin/env python3
"""One-worker Linux/Unix bounded reproduction; standard library only.
Run from a clean extraction. Fresh output is separate from published evidence.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent

def child_limits():
    resource.setrlimit(resource.RLIMIT_CPU,(30,31))
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    # Select a single available core without assuming a fixed CPU identifier.
    if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--tasks',nargs='+',default=['tests','pilot','populations','horn','family','verify','report','joint','joint-replay'],choices=['tests','pilot','populations','horn','family','verify','report','joint','joint-replay'])
    p.add_argument('--sizes',nargs='+',type=int,default=list(range(1,8)));p.add_argument('--resume',action='store_true')
    a=p.parse_args();out=a.out.resolve()
    if out==ROOT or out==ROOT/'results' or out.is_relative_to(ROOT/'inputs') or out.is_relative_to(ROOT/'src'):
        p.error('choose a fresh reproduction output directory')
    if any(n<1 or n>7 for n in a.sizes):p.error('sizes must be in 1..7')
    if out.exists() and not out.is_dir():p.error('output must be a directory')
    if out.exists() and any(out.iterdir()) and not a.resume:
        p.error('output is not empty; use a fresh directory or --resume')
    if out.exists() and any(out.iterdir()) and a.resume and not (out/'measurements.json').exists():
        p.error('resume requires retained measurements')
    out.mkdir(parents=True,exist_ok=True)
    measurement=out/'measurements.json'
    if measurement.exists() and not a.resume:p.error('output already has measurements; use a fresh directory or --resume')
    records=json.loads(measurement.read_text()) if measurement.exists() else []
    tasks=[]
    for task in a.tasks:
        if task=='tests':tasks.append(('tests',[sys.executable,'-m','unittest','discover','-s','tests','-v']))
        elif task=='report':tasks.append(('report',[sys.executable,'report.py','--results',str(out),'--out',str(out)]))
        elif task=='joint':tasks.append(('joint',[sys.executable,'-m','src.joint_benchmark','--out',str(out),'--part','all']))
        elif task=='joint-replay':tasks.append(('joint-replay',[sys.executable,'replay_joint.py','--results',str(out),'--report',str(out/'joint-replay.json')]))
        elif task=='verify':tasks.append(('verify',[sys.executable,'verify.py','--results',str(out),'--report',str(out/'independent-verification.json')]))
        elif task=='populations':
            for n in a.sizes:tasks.append((f'population-{n}',[sys.executable,'-m','src.experiment','populations','--n',str(n),'--out',str(out)]))
        else:tasks.append((task,[sys.executable,'-m','src.experiment',task,'--out',str(out)]))
    for name,cmd in tasks:
        if any(r['task']==name and r['exit_code']==0 for r in records):continue
        t=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
        with (out/f'{name}.log').open('w') as log:
            try:r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=32,preexec_fn=child_limits);exitcode=r.returncode
            except subprocess.TimeoutExpired:exitcode=124
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        records.append({'task':name,'exit_code':exitcode,'wall_seconds':time.monotonic()-t,
                        'cpu_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                        'parent_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        'child_peak_rss_kib_cumulative':after.ru_maxrss,'workers':1,
                        'address_space_limit_bytes':536870912,'wall_timeout_seconds':32})
        measurement.write_text(json.dumps(records,indent=2)+'\n')
        print(json.dumps(records[-1]),flush=True)
        if sum(r['cpu_seconds'] for r in records)>21600:raise SystemExit('campaign working allocation exhausted; repair reserve protected')
        if exitcode:raise SystemExit(f'{name} failed: inspect {out/name}.log')
    # Reproduction equality covers deterministic outputs, not machine-dependent measurements/log text.
    if (ROOT/'results'/'expected-files.json').exists():
        files=json.loads((ROOT/'results'/'expected-files.json').read_text())
        checked=[]
        for name in files:
            candidate=out/name
            if candidate.exists():
                if candidate.read_bytes()!=(ROOT/'results'/name).read_bytes():raise SystemExit('deterministic mismatch: '+name)
                checked.append(name)
        if set(a.tasks)=={'tests','pilot','populations','horn','family','verify','report','joint','joint-replay'} and set(a.sizes)==set(range(1,8)) and len(checked)!=len(files):
            raise SystemExit('full reproduction is missing deterministic output files')
        (out/'comparison.json').write_text(json.dumps({'matched_files':checked,'expected_files':len(files),
            'all_expected_present':len(checked)==len(files)},indent=2)+'\n')
    print('All requested tasks completed. This is not a general-proof or novelty verdict.')
if __name__=='__main__':main()
