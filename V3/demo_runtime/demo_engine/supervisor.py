from __future__ import annotations
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from .common import ProcessLock,atomic_json,load_config


def main(root):
    root=Path(root).resolve()
    cfg=load_config(root/'config.demo.json')
    runtime=root/cfg['runtime_dir']
    logs=runtime/'logs'; logs.mkdir(parents=True,exist_ok=True)
    with ProcessLock(runtime/'supervisor.lock'):
        children={}; handles={}; exits={}; next_restart={}
        modules={'trader':'demo_engine.run','research':'demo_engine.research','dashboard':'demo_engine.dashboard'}
        try:
            while True:
                stop=(runtime/'STOP').exists()
                for name,module in modules.items():
                    process=children.get(name)
                    if process and process.poll() is not None:
                        exits[name]=process.returncode
                        children.pop(name)
                        handles.pop(name).close()
                        next_restart[name]=time.monotonic()+30
                    if name not in children and not stop and time.monotonic()>=next_restart.get(name,0):
                        output=(logs/(name+'.log')).open('a',encoding='utf-8')
                        flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
                        children[name]=subprocess.Popen([sys.executable,'-m',module,'--root',str(root)],
                             cwd=str(root),stdout=output,stderr=subprocess.STDOUT,creationflags=flags)
                        handles[name]=output
                atomic_json(runtime/'supervisor.json',dict(pid=os.getpid(),observed_ms=time.time_ns()//1_000_000,
                    status='STOPPING' if stop else 'RUNNING',children={k:p.pid for k,p in children.items()},last_exits=exits))
                # Keep the dashboard and research available while a protected position is flattened.
                if stop and 'trader' not in children:
                    break
                time.sleep(2)
        finally:
            # A graceful stop waits for the trader to finish; it never force-kills an owned position.
            for name,process in children.items():
                if name!='trader':
                    process.terminate()
            for file in handles.values(): file.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    main(p.parse_args().root)
