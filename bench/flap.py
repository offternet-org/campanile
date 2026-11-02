# DEVELOPED BY CARROTSTUDIO software house
"""A link that comes and goes: down for DOWN seconds every PERIOD, on the clock all the
containers share, so both ends drop at the same instant. While down nothing gets through.

    flap.py IFACE PERIOD DOWN T0 NETEM_ARGS...
"""

import subprocess
import sys
import time

iface, period, down, t0 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
base = sys.argv[5:]
state = None
while True:
    phase = (time.time() - t0) % period
    is_down = phase < down
    if is_down != state:
        extra = ["loss", "100%"] if is_down else []
        subprocess.run(
            ["tc", "qdisc", "change", "dev", iface, "root", "netem", *base, *extra], check=True
        )
        state = is_down
    time.sleep(max(0.002, min(0.05, (down - phase) if is_down else (period - phase))))
