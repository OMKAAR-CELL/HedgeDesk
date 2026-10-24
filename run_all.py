"""Start all five agents as separate processes. Ctrl+C stops them."""
import subprocess
import sys
import time

NAMES = ["exposure", "forecast", "pricing", "recommender", "coordinator"]

procs = [subprocess.Popen([sys.executable, "-m", f"agents.{n}"]) for n in NAMES]
try:
    while True:
        time.sleep(1)
        dead = [n for n, p in zip(NAMES, procs) if p.poll() is not None]
        if dead:
            print(f"Agent(s) exited: {dead}. Stopping the rest.")
            break
except KeyboardInterrupt:
    pass
finally:
    for p in procs:
        p.terminate()
