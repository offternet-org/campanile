#!/usr/bin/env python3
# DEVELOPED BY CARROTSTUDIO software house
"""Three Campaniles on one computer, A - B - C, each the real Campanile behind the real nginx of
a Raspberry Pi, in its own container, joined by links that behave like Wi-Fi measured in a
building with Campanile's own coverage test. A reaches C only through B.

Real: Campanile and its answers, nginx as raspberry/nginx-site.sh writes it, the boards, the
link numbers (five spots measured on 30 Oct 2026 with an iPhone and the coverage test), the
verdict function. Standing in: the board exchange between Campaniles, which Campanile doesn't
do yet (agent.py, uncompressed: the worst case); each link, a delay and a speed tuned until the
same test gives the phone's numbers (probe.py); the window of a visit, 30 s minus 10 s to join
the neighbour's Wi-Fi.

Nothing counts until it has been seen failing. Before and after measuring, the bench checks that
a closed wall stops everything, a flipped bit is caught, a window too short fails, each wall
sits on its own link and A cannot reach C directly. A run that misses a control, or stops
halfway, says NON VALIDA.

    python3 bench/chain.py            the whole bench, about 90 minutes
    python3 bench/chain.py --quick    every step once, about 15 minutes
    python3 bench/chain.py --ci       the short check for every change, on the walls in
                                      bench/profiles.json, about 5 minutes
    python3 bench/chain.py --report bench/runs/RUN    write the report again from the data

Needs Docker on a Linux kernel with netem: Linux, or Docker Desktop / Colima on a Mac.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import secrets
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path

H = Path(__file__).resolve().parent.parent  # the repository, mounted as /h in the containers
sys.path.insert(0, str(H / "campanile"))
import api  # noqa: E402 - the thresholds of the coverage verdict, from Campanile itself
import store  # noqa: E402

IMAGE = "campanile-bench"
RUNS = H / "bench" / "runs"
PROFILES = H / "bench" / "profiles.json"
WINDOW = 20.0  # s: a visit of 30 s, minus 10 s to join the neighbour's Wi-Fi (declared)
UNLIMITED = 1_000_000  # kbit/s: no speed limit, the delay alone
BOARD, BIG = 80, 81  # nginx in front of the realistic board and of the largest one
INSIDE = {BOARD: 8080, BIG: 8090}  # where each Campanile listens behind nginx
LINKS = {"ab": ("chain_ab", "172.31.71"), "bc": ("chain_bc", "172.31.72")}
HOSTS = {"a": {"ab": 10}, "b": {"ab": 20, "bc": 20}, "c": {"bc": 30}}
# The coverage test allows a phone 6 pieces a minute and Campanile knows a phone by its MAC, so
# extra addresses don't help. The tuning talks to six copies of B's Campanile, each counting for
# itself: same container, same wall.
TUNING_PORTS = range(8100, 8106)
PER_PORT = 5  # tests a minute on each copy
PASSWORD = secrets.token_hex(12)
CLOSED = {"delay": 0.0, "rate": UNLIMITED, "loss": 100}

# The walk of 30 Oct 2026, from Campanile's own table: name, place, median, worst, kbit/s.
WALK = [
    ("P1", "6 metri dal Campanile", 17, 73, 17332),
    ("P2", "porta di casa", 44, 77, 14170),
    ("P3", "corridoio, porta chiusa", 18, 75, 24385),
    ("P4", "davanti all'ascensore", 23, 64, 12633),
    ("P5", "3 m oltre l'ascensore (bordo)", 35, 763, 8066),
]
# The poorest spots the coverage test still calls good and fair, 5% inside the line so the
# verdict doesn't flip from one test to the next. The fair rule sets no limit on the slowest
# ping: three times the median is a choice.
EDGE = 0.95
LIMITS = [
    (
        "G",
        "appena dentro 'buono'",
        round(api.GOOD_MS * EDGE),
        round(api.GOOD_WORST_MS * EDGE),
        round(api.GOOD_KBPS / EDGE),
    ),
    (
        "F",
        "appena dentro 'discreto'",
        round(api.FAIR_MS * EDGE),
        round(3 * api.FAIR_MS * EDGE),
        round(api.FAIR_KBPS / EDGE),
    ),
]
SAMPLE_BITS = 256 * 1024 * 8  # the coverage test's piece


class Fault(Exception):
    """The bench itself went wrong: never a measurement."""


# --- docker -----------------------------------------------------------------------------------


def sh(*cmd, timeout=120, check=True, stdin=None):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=stdin)
    if check and r.returncode != 0:
        raise Fault(f"{' '.join(cmd)[:300]}\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
    return r


def dx(box, *cmd, timeout=120, check=True, stdin=None):
    flags = ["-i"] if stdin is not None else []
    return sh(
        "docker", "exec", *flags, f"camp-{box}", *cmd, timeout=timeout, check=check, stdin=stdin
    )


def jx(box, *cmd, timeout=120):
    out = dx(box, *cmd, timeout=timeout).stdout.strip().splitlines()
    return json.loads(out[-1])


def ip(box, link, n=None):
    return f"{LINKS[link][1]}.{n or HOSTS[box][link]}"


def boxes_on(link):
    return [b for b, links in HOSTS.items() if link in links]


def teardown():
    sh("docker", "rm", "-f", *(f"camp-{b}" for b in HOSTS), check=False)
    for net, _ in LINKS.values():
        sh("docker", "network", "rm", net, check=False)


DEV: dict = {}


def setup(seed, log):
    sh("docker", "build", "-q", "-t", IMAGE, str(H / "bench"), timeout=1800)
    teardown()
    for net, prefix in LINKS.values():
        sh("docker", "network", "create", "--internal", "--subnet", f"{prefix}.0/24", net)
    for box, links in HOSTS.items():
        first, *others = links
        # A Campanile carries boards, it doesn't route: B must not pass packets from A to C.
        sh(
            "docker",
            "run",
            "-d",
            "--name",
            f"camp-{box}",
            "--hostname",
            f"camp-{box}",
            "--network",
            LINKS[first][0],
            "--ip",
            ip(box, first),
            "--cap-add",
            "NET_ADMIN",
            "--sysctl",
            "net.ipv4.ip_forward=0",
            "-v",
            f"{H}:/h:ro",
            "--entrypoint",
            "sleep",
            IMAGE,
            "infinity",
        )
        for link in others:
            sh("docker", "network", "connect", "--ip", ip(box, link), LINKS[link][0], f"camp-{box}")
    for box, links in HOSTS.items():
        lines = dx(box, "ip", "-o", "-4", "addr", "show").stdout.splitlines()
        for link in links:
            for line in lines:
                parts = line.split()
                if parts[3].split("/")[0] == ip(box, link):
                    DEV[(box, link)] = parts[1].split("@")[0]
    for (box, _link), dev in DEV.items():
        # One packet per frame, as on the air: offloads would make a wall drop 44 at a time.
        dx(box, "ethtool", "-K", dev, "tso", "off", "gso", "off", "gro", "off")
    # Neighbours known once and for all, as after joining a Wi-Fi: a closed wall would also
    # swallow the address requests and fail in 3 s with a different error.
    macs = {
        key: dx(key[0], "cat", f"/sys/class/net/{dev}/address").stdout.strip()
        for key, dev in DEV.items()
    }
    for link in LINKS:
        for box in boxes_on(link):
            for peer in boxes_on(link):
                if peer != box:
                    dx(
                        box,
                        "ip",
                        "neigh",
                        "replace",
                        ip(peer, link),
                        "lladdr",
                        macs[(peer, link)],
                        "dev",
                        DEV[(box, link)],
                        "nud",
                        "permanent",
                    )
    for i, box in enumerate(HOSTS):
        log(
            dx(
                box,
                "python3",
                "/h/bench/seed.py",
                "/data/campanile.db",
                box.upper(),
                "120",
                str(seed + i),
            ).stdout.strip()
        )
        if box in "ab":
            log(
                dx(
                    box,
                    "python3",
                    "/h/bench/seed.py",
                    "/big/campanile.db",
                    box.upper() + "X",
                    "500",
                    str(seed + 10 + i),
                    "max",
                ).stdout.strip()
            )
    for box in HOSTS:
        serve(box, INSIDE[BOARD], "/data", proxied=True)
        if box in "ab":
            serve(box, INSIDE[BIG], "/big", proxied=True)
        front(box)
    for port in TUNING_PORTS:
        serve("b", port, f"/tuning-{port}", proxied=False)
    coverage_on()


def serve(box, port, data, proxied):
    where = ["--host", "127.0.0.1", "--behind-proxy"] if proxied else ["--host", "0.0.0.0"]
    sh(
        "docker",
        "exec",
        "-d",
        "-e",
        f"CAMPANILE_ADMIN_PASSWORD={PASSWORD}",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        f"camp-{box}",
        "sh",
        "-c",
        "exec python3 /h/campanile/server.py "
        + " ".join(where)
        + f" --port {port} --data {data} --kiwix-port 0 > /tmp/server-{port}.log 2>&1",
    )
    wait_for(box, f"http://127.0.0.1:{port}/api/status", f"/tmp/server-{port}.log")


def front(box):
    """nginx as a Raspberry Pi runs it: the site raspberry/nginx-site.sh writes, without a
    hotspot. The largest board gets the same site on port 81."""
    site = dx(
        box,
        "env",
        "CAMPANILE_CODE=/h",
        "CAMPANILE_DATA=/data",
        "bash",
        "/h/raspberry/nginx-site.sh",
        "",
        "campanile",
    ).stdout
    dx(box, "sh", "-c", "cat > /etc/nginx/sites-enabled/campanile", stdin=site)
    if box in "ab":
        big = site.split("# Wikipedia on its own port")[0]  # no second Kiwix server
        big = "\n".join(
            line
            for line in big.splitlines()
            if not line.startswith(("limit_conn_zone", "limit_req_zone"))
        )
        big = big.replace("listen 80", "listen 81").replace("[::]:80", "[::]:81")
        big = big.replace("127.0.0.1:8080", f"127.0.0.1:{INSIDE[BIG]}")
        dx(box, "sh", "-c", "cat > /etc/nginx/sites-enabled/campanile-big", stdin=big)
    dx(box, "nginx", "-t")
    dx(box, "nginx")
    wait_for(box, "http://127.0.0.1/api/status", "/var/log/nginx/error.log")


def wait_for(box, url, logfile):
    for _ in range(100):
        r = dx(
            box,
            "curl",
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "--max-time",
            "2",
            url,
            check=False,
        )
        if r.stdout.strip() == "200":
            return
        time.sleep(0.3)
    raise Fault(f"{box}: {url} not answering\n" + dx(box, "cat", logfile, check=False).stdout)


_coverage_since = [0.0]


def coverage_on():
    # The copies directly, the main Campanile through nginx (which says the call is local).
    urls = [f"http://127.0.0.1:{port}" for port in TUNING_PORTS] + ["http://127.0.0.1"]
    for url in urls:
        dx(
            "b",
            "curl",
            "-s",
            "-f",
            "--max-time",
            "5",
            "-X",
            "POST",
            "-H",
            "Content-Type: application/json",
            "--data",
            json.dumps({"password": PASSWORD}),
            f"{url}/api/admin/coverage/start",
        )
    _coverage_since[0] = time.monotonic()


# --- the walls --------------------------------------------------------------------------------


def netem_args(p):
    args = ["delay", f"{p['delay']:.3f}ms", "rate", f"{p['rate']}kbit"]
    if p.get("loss"):
        args += ["loss", f"{p['loss']}%"]
    return [*args, "limit", "1000"]


def shape(link, p):
    """p None: no wall at all. The rate is always set: netem then keeps packets in order."""
    for box in boxes_on(link):
        dev = DEV[(box, link)]
        if p is None:
            dx(box, "tc", "qdisc", "del", "dev", dev, "root", check=False)
        else:
            dx(box, "tc", "qdisc", "replace", "dev", dev, "root", "netem", *netem_args(p))


def counters(link):
    out = {}
    for box in boxes_on(link):
        text = dx(box, "tc", "-s", "qdisc", "show", "dev", DEV[(box, link)]).stdout
        m = re.search(r"Sent (\d+) bytes (\d+) pkt \(dropped (\d+)", text)
        out[box] = [int(x) for x in m.groups()] if m else [0, 0, 0]
    return out


def flap_start(link, p, period, down):
    t0 = time.time() + 1
    for box in boxes_on(link):
        sh(
            "docker",
            "exec",
            "-d",
            f"camp-{box}",
            "sh",
            "-c",
            f"echo $$ > /tmp/flap.pid; exec python3 /h/bench/flap.py {DEV[(box, link)]} "
            f"{period} {down} {t0} " + " ".join(netem_args(p)),
        )
    time.sleep(1.5)


def flap_stop(link):
    for box in boxes_on(link):
        dx(
            box,
            "sh",
            "-c",
            "kill $(cat /tmp/flap.pid) 2>/dev/null; rm -f /tmp/flap.pid",
            check=False,
        )


# --- the stand-in and the instruments ---------------------------------------------------------


def reference(box, port=BOARD):
    return jx(box, "python3", "/h/bench/board.py", "reference", f"127.0.0.1:{INSIDE[port]}")


def find(box, mark):
    return jx(box, "python3", "/h/bench/board.py", "find", f"127.0.0.1:{INSIDE[BOARD]}", mark)


def pull(box, peer, link, port, budget, ref, merge=None, address=None):
    """box downloads peer's board over link, through peer's nginx; ref is what peer holds."""
    cmd = [
        "python3",
        "/h/bench/agent.py",
        address or f"{ip(peer, link)}:{port}",
        f"{budget:.4f}",
        ref["posts"],
        ref["notices"],
    ]
    if merge:
        cmd += ["--merge", merge]
    return jx(box, *cmd, timeout=budget + 90)


def exchange(port=BOARD, refs=None, budget=WINDOW):
    """B visits A: it takes A's board, then A takes B's, in one window. Wi-Fi is half duplex,
    the two directions share the air, so they go one after the other."""
    first = pull("b", "a", "ab", port, budget, refs["a"])
    second = None
    if first["ok"]:
        second = pull("a", "b", "ab", port, max(0.0, budget - first["seconds"]), refs["b"])
    ok = first["ok"] and bool(second and second["ok"])
    return {
        "ok": ok,
        "seconds": round(first["seconds"] + second["seconds"], 4) if ok else None,
        "first": first,
        "second": second,
        "wall": time.time(),
    }


class Prober:
    """The coverage test from one box to B over one link, taking turns among B's copies so
    that none goes past Campanile's per-phone limit."""

    def __init__(self, box, link):
        self.box, self.link = box, link
        self.used = {port: [] for port in TUNING_PORTS}

    def run(self, mode, target=None):
        while True:
            now = time.monotonic()
            free = [p for p in TUNING_PORTS if sum(now - t < 61 for t in self.used[p]) < PER_PORT]
            if free:
                break
            time.sleep(0.5)
        port = min(free, key=lambda p: max(self.used[p], default=0))
        self.used[port].append(now)
        if time.monotonic() - _coverage_since[0] > 1800:
            coverage_on()  # it turns itself off after two hours
        out = jx(
            self.box,
            "python3",
            "/h/bench/probe.py",
            mode,
            target or f"{ip('b', self.link)}:{port}",
            timeout=180,
        )
        refused = {k: v for k, v in out["statuses"].items() if k not in ("200", "none")}
        if refused:
            raise Fault(f"Campanile refused the probe: {refused}")
        return out


# --- tuning the walls -------------------------------------------------------------------------


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def kbps_at(prober, p, n):
    shape(prober.link, p)
    return med([prober.run("sample")["kbps"] for _ in range(n)])


def validate(prober, p, n):
    shape(prober.link, p)
    runs = [prober.run("cov") for _ in range(n)]
    return {
        "median_ms": med([r["median_ms"] for r in runs]),
        "worst_ms": med([r["worst_ms"] for r in runs]),
        "kbps": med([r["kbps"] for r in runs]),
        "lost": sum(r["lost"] for r in runs),
        "sent": sum(r["sent"] for r in runs),
        "verdicts": [r["verdict"] for r in runs],
    }


def twin_walls(prober, p):
    """The same wall on both links, measured side by side and in turns: B-C must give A-B's
    numbers. (Against a measure taken minutes earlier, two noisy tests once failed it.)"""
    other = Prober("c", "bc")
    shape("ab", p)
    shape("bc", p)
    times = {"a-b": [], "b-c": []}
    speeds = {"a-b": [], "b-c": []}
    for _ in range(3):
        for side, probe in (("a-b", prober), ("b-c", other)):
            times[side] += probe.run("pings")["times"]
            speeds[side].append(probe.run("sample")["kbps"])
    shape("bc", None)
    got = {s: {"median_ms": round(med(times[s]), 2), "kbps": med(speeds[s])} for s in times}
    a, b = got["a-b"], got["b-c"]
    same = (
        abs(a["median_ms"] - b["median_ms"]) <= max(2.0, 0.05 * a["median_ms"])
        and abs(a["kbps"] - b["kbps"]) <= 0.15 * a["kbps"]
    )
    return {"same": same, **got}


def ping_median(prober, p, n):
    shape(prober.link, p)
    return med([t for _ in range(n) for t in prober.run("pings")["times"]])


def tune(prober, base, name, place, m, w, k, quick, log):
    """The delay first, corrected on what the test measures until its median is the phone's
    (the server and the timers add a little); then the speed, halving until the 256 kB piece
    arrives as fast as it did for the phone; then the delay once more at that speed. A wall that
    can't be made fast enough keeps no speed limit and is marked 'prudente': slower than the
    real one, never faster."""
    n = 1 if quick else 3
    d, delays = max(0.0, (m - base) / 2), []

    def settle(rate):
        nonlocal d
        for _ in range(3):
            got = ping_median(prober, {"delay": d, "rate": rate}, n)
            delays.append([round(d, 3), rate, round(got, 2)])
            if abs(got - m) <= max(0.03 * m, 1.0):
                return
            d = max(0.0, d - (got - m) / 2)

    settle(UNLIMITED)
    k_open = kbps_at(prober, {"delay": d, "rate": UNLIMITED}, n)
    if k_open is None:
        raise Fault(f"{name}: no piece arrived with the delay alone")
    speeds, rate = [[UNLIMITED, k_open]], UNLIMITED
    if k_open > k * 1.08:
        lo, hi = float(k), float(UNLIMITED)
        # First guess: the time the phone's piece took beyond the delay alone, spent on the wire.
        extra = SAMPLE_BITS / k - SAMPLE_BITS / k_open
        mid = min(max(SAMPLE_BITS / extra, lo * 1.01), hi / 1.01)
        best = (abs(k_open - k), UNLIMITED)
        for _ in range(5 if quick else 10):
            got = kbps_at(prober, {"delay": d, "rate": round(mid)}, n)
            if got is None:
                raise Fault(f"{name}: no piece arrived at {round(mid)} kbit/s")
            speeds.append([round(mid), got])
            best = min(best, (abs(got - k), round(mid)))
            if abs(got - k) <= 0.05 * k:
                break
            lo, hi = (mid, hi) if got < k else (lo, mid)
            mid = math.sqrt(lo * hi)
        rate = best[1]
        settle(rate)  # a slower wire adds a little to every ping
    p = {"delay": round(d, 3), "rate": rate}
    v = validate(prober, p, 2 if quick else 5)
    ok_median = abs(v["median_ms"] - m) <= max(0.10 * m, 2)
    if abs(v["kbps"] - k) <= 0.15 * k:
        speed = "uguale"
    elif rate == UNLIMITED and v["kbps"] < k:
        speed = "prudente"
    else:
        speed = "fuori"
    fit = {
        "name": name,
        "place": place,
        "target": {"median_ms": m, "worst_ms": w, "kbps": k},
        "profile": p,
        "delays": delays,
        "speeds": speeds,
        "validation": v,
        "median_ok": ok_median,
        "speed": speed,
        "ok": ok_median and speed != "fuori" and v["lost"] == 0,
    }
    log(
        f"  {name}: delay {p['delay']} ms per side, rate {rate} kbit/s -> median "
        f"{v['median_ms']} (target {m}), kbps {v['kbps']} (target {k}), worst {v['worst_ms']}, "
        f"lost {v['lost']}/{v['sent']}, {speed}, {'OK' if fit['ok'] else 'NOT OK'}"
    )
    return fit


# --- the controls -----------------------------------------------------------------------------


def check(results, name, passed, detail, log):
    results.append({"control": name, "pass": bool(passed), "detail": detail})
    log(f"  [{'PASS' if passed else 'FAIL'}] {name}: {json.dumps(detail)[:300]}")


def controls(stage, n_pos, n_neg, log):
    """Each control comes out the way it does only if the bench sees what it claims."""
    out = []
    shape("ab", None)
    shape("bc", None)
    refs = {b: reference(b) for b in HOSTS}

    pos = [exchange(refs=refs) for _ in range(n_pos)]
    check(
        out,
        f"{stage}: senza muro lo scambio riesce",
        all(t["ok"] for t in pos),
        {
            "ok": sum(t["ok"] for t in pos),
            "n": n_pos,
            "seconds_max": max((t["seconds"] or 0) for t in pos),
        },
        log,
    )

    wrong = pull("b", "a", "ab", BOARD, WINDOW, refs["c"])
    check(out, f"{stage}: impronta sbagliata rifiutata", wrong["kind"] == "mismatch", wrong, log)

    for flip in (False, True):
        dx("b", "rm", "-f", "/tmp/proxy.log")
        sh(
            "docker",
            "exec",
            "-d",
            "camp-b",
            "sh",
            "-c",
            f"echo $$ > /tmp/proxy.pid; exec python3 -u /h/bench/proxy.py 9100 {ip('a', 'ab')} "
            f"{BOARD}{'' if flip else ' clean'} > /tmp/proxy.log 2>&1",
        )
        for _ in range(50):
            if "listening" in dx("b", "cat", "/tmp/proxy.log", check=False).stdout:
                break
            time.sleep(0.1)
        r = pull("b", "a", "ab", BOARD, WINDOW, refs["a"], address="127.0.0.1:9100")
        said = dx("b", "cat", "/tmp/proxy.log").stdout.strip().splitlines()
        dx("b", "sh", "-c", "kill $(cat /tmp/proxy.pid); rm -f /tmp/proxy.pid")
        time.sleep(0.2)
        same_size = r["bytes"] == sum(refs["a"]["bytes"])
        if flip:
            check(
                out,
                f"{stage}: un bit cambiato per strada viene scoperto",
                r["kind"] == "mismatch" and any("flipped" in s for s in said) and same_size,
                {"agent": r["kind"], "proxy": said[-1:], "same_size": same_size},
                log,
            )
        else:
            check(
                out,
                f"{stage}: lo stesso intermediario senza guasto non disturba",
                r["ok"] and same_size,
                {"agent": r["kind"], "proxy": said[-1:]},
                log,
            )

    short = pull("b", "a", "ab", BOARD, 0.0005, refs["a"])
    check(
        out, f"{stage}: una finestra troppo corta fallisce", short["kind"] == "timeout", short, log
    )

    shape("ab", CLOSED)
    neg = [exchange(refs=refs) for _ in range(n_neg)]
    kinds = [t["first"]["kind"] for t in neg]
    waited = [t["first"]["seconds"] for t in neg]
    check(
        out,
        f"{stage}: muro chiuso, nessuno scambio, e si aspetta tutta la finestra",
        not any(t["ok"] for t in neg)
        and set(kinds) == {"timeout"}
        and all(WINDOW - 0.05 <= s <= WINDOW + 2 for s in waited),
        {"kinds": kinds, "waited": waited},
        log,
    )

    # Each wall on its own link: closing A-B leaves B-C working, and the other way round.
    c_from_b = pull("c", "b", "bc", BOARD, WINDOW, refs["b"])
    check(out, f"{stage}: il muro A-B non tocca B-C", c_from_b["ok"], c_from_b, log)
    shape("ab", None)
    shape("bc", CLOSED)
    a_from_b = pull("a", "b", "ab", BOARD, WINDOW, refs["b"])
    c_cut = pull("c", "b", "bc", BOARD, 3.0, refs["b"])
    check(
        out,
        f"{stage}: il muro B-C non tocca A-B, e B-C e' davvero chiuso",
        a_from_b["ok"] and c_cut["kind"] == "timeout",
        {"a<-b": a_from_b, "c<-b": c_cut},
        log,
    )
    shape("bc", None)

    a_to_c = pull("a", "c", "bc", BOARD, 5.0, refs["c"])
    check(
        out,
        f"{stage}: A non raggiunge C da solo, solo attraverso B",
        not a_to_c["ok"] and a_to_c.get("last_error_kind") == "unreachable",
        a_to_c,
        log,
    )
    forward = dx("b", "cat", "/proc/sys/net/ipv4/ip_forward").stdout.strip()
    check(out, f"{stage}: B non instrada pacchetti", forward == "0", {"ip_forward": forward}, log)
    return out


# --- the chain --------------------------------------------------------------------------------


def chain(p, n_canary, rng, log):
    out = []
    shape("ab", p)
    shape("bc", p)

    def hop(box, peer, link):
        return pull(box, peer, link, BOARD, WINDOW, reference(peer), merge="/data/campanile.db")

    counts0 = {b: reference(b)["count"] for b in HOSTS}
    r1, r2 = hop("b", "a", "ab"), hop("c", "b", "bc")
    counts1 = {b: reference(b)["count"] for b in HOSTS}
    want = {
        "a": counts0["a"],
        "b": counts0["b"] + counts0["a"],
        "c": counts0["c"] + counts0["b"] + counts0["a"],
    }
    check(
        out,
        "prima volta: B riceve tutta la bacheca di A, C quella di B, A compreso",
        r1["ok"] and r2["ok"] and counts1 == want,
        {
            "before": counts0,
            "after": counts1,
            "expected": want,
            "merged": [r1["merged"], r2["merged"]],
            "seconds": [r1["seconds"], r2["seconds"]],
        },
        log,
    )
    r1, r2 = hop("b", "a", "ab"), hop("c", "b", "bc")
    counts2 = {b: reference(b)["count"] for b in HOSTS}
    check(
        out,
        "seconda volta: niente di doppio",
        r1["ok"] and r2["ok"] and r1["merged"] == 0 and r2["merged"] == 0 and counts2 == counts1,
        {"merged": [r1["merged"], r2["merged"]], "after": counts2},
        log,
    )

    marks = rng.sample(range(10**5, 10**6), n_canary + 1)
    category = store.CATEGORIES[0]
    arrived, times = 0, []
    for i, n in enumerate(marks[:-1]):
        mark = f"K-{n}"
        text = (
            f"Canarino {i + 1}: partito dal Campanile A, deve arrivare a C passando per B [{mark}]"
        )
        dx(
            "a",
            "python3",
            "/h/bench/board.py",
            "add",
            "/data/campanile.db",
            "need",
            category,
            text,
            "scala A",
            "prova del banco",
        )
        sent = find("a", mark)["found"]
        clean = not find("b", mark)["found"] and not find("c", mark)["found"]
        h1 = hop("b", "a", "ab")
        at_b, not_yet_c = find("b", mark)["found"], not find("c", mark)["found"]
        h2 = hop("c", "b", "bc")
        got = find("c", mark)["found"]
        fields = ("kind", "category", "text", "area", "contact")
        same = len(sent) == 1 and len(got) == 1 and all(sent[0][f] == got[0][f] for f in fields)
        good = (
            clean
            and h1["ok"]
            and h1["merged"] == 1
            and len(at_b) == 1
            and not_yet_c
            and h2["ok"]
            and h2["merged"] == 1
            and same
        )
        arrived += good
        times.append([h1["seconds"], h2["seconds"]])
        if not good:
            log(f"  canary {mark} NOT through: {h1} {h2} clean={clean} same={same}")
    check(
        out,
        "canarini: da A a C passando per B, identici campo per campo",
        arrived == n_canary,
        {"through": arrived, "n": n_canary, "hop_seconds": times},
        log,
    )

    mark = f"K-{marks[-1]}"
    dx(
        "a",
        "python3",
        "/h/bench/board.py",
        "add",
        "/data/campanile.db",
        "need",
        category,
        f"Canarino di controllo [{mark}]",
        "scala A",
        "prova del banco",
    )
    h1 = hop("b", "a", "ab")
    shape("bc", CLOSED)
    cut = hop("c", "b", "bc")
    stuck = not find("c", mark)["found"]
    shape("bc", p)
    again = hop("c", "b", "bc")
    late = len(find("c", mark)["found"]) == 1
    check(
        out,
        "con B-C chiuso il canarino si ferma a B, e passa appena si riapre",
        h1["ok"] and cut["kind"] == "timeout" and stuck and again["ok"] and late,
        {
            "a->b": h1["kind"],
            "b->c cut": cut["kind"],
            "stuck_at_b": stuck,
            "b->c reopened": again["kind"],
            "arrived_after": late,
        },
        log,
    )
    return out


# --- the run ----------------------------------------------------------------------------------


def git(*args):
    r = sh("git", "-C", str(H), *args, check=False)
    return r.stdout.strip()


def plan(fits, mode):
    """The blocks of exchanges: (name, wall, flapping, port, trials)."""
    walls = {f["name"]: f["profile"] for f in fits}
    p5, fair = walls["P5"], walls["F"]
    if mode == "ci":
        return [("P5", p5, None, BOARD, 5), ("P5 + 10% persi", {**p5, "loss": 10}, None, BOARD, 3)]
    main, side = (3, 2) if mode == "quick" else (50, 30)
    blocks = [(n, walls[n], None, BOARD, main) for n, *_ in WALK + LIMITS]
    blocks += [
        ("P5 bacheca piena", p5, None, BIG, side),
        ("F bacheca piena", fair, None, BIG, side),
    ]
    blocks += [
        (f"P5 + {loss}% persi", {**p5, "loss": loss}, None, BOARD, side)
        for loss in (5, 10, 20, 30, 50)
    ]
    blocks += [
        (f"P5 + buchi di {down} s ogni {period} s", p5, (period, down), BOARD, side)
        for down, period in ((2, 4), (5, 10), (10, 20))
    ]
    blocks.append(("F + 5% persi", {**fair, "loss": 5}, None, BOARD, side))
    return blocks


def run(args):
    mode = "ci" if args.ci else "quick" if args.quick else "full"
    n_pos, n_neg = {"full": (10, 5), "quick": (2, 1), "ci": (2, 1)}[mode]
    n_canary = {"full": 20, "quick": 2, "ci": 2}[mode]
    n_verdict = {"full": 3, "quick": 1, "ci": 1}[mode]
    rng = random.Random(args.seed)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = RUNS / (stamp + ("" if mode == "full" else f"-{mode}"))
    out.mkdir(parents=True)
    logfile = (out / "log.txt").open("a", encoding="utf-8")
    results = (out / "results.jsonl").open("a", encoding="utf-8")

    def log(text):
        line = f"{time.strftime('%H:%M:%S')} {text}"
        print(line, flush=True)
        logfile.write(line + "\n")
        logfile.flush()

    def record(kind, data):
        results.write(json.dumps({"type": kind, **data}) + "\n")
        results.flush()

    meta = {
        "mode": mode,
        "seed": args.seed,
        "window_s": WINDOW,
        "started": stamp,
        "commit": git("rev-parse", "--short", "HEAD"),
        "uncommitted_files": len(git("status", "--porcelain").splitlines()),
        "docker": sh(
            "docker",
            "info",
            "--format",
            "{{.ServerVersion}} kernel {{.KernelVersion}} cpus {{.NCPU}}",
        ).stdout.strip(),
        "bench_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            for p in sorted((H / "bench").glob("*.py"))
        },
        "campanile_sha256": hashlib.sha256(
            b"".join(p.read_bytes() for p in sorted((H / "campanile").glob("*.py")))
        ).hexdigest()[:16],
    }
    log(f"run {out.name} ({mode}), commit {meta['commit']}, {meta['docker']}")
    try:
        setup(args.seed, log)
        meta["image_id"] = sh(
            "docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"
        ).stdout.strip()
        meta["versions"] = dx(
            "a", "sh", "-c", "python3 --version; nginx -v 2>&1; cat /etc/debian_version"
        ).stdout.split("\n")
        meta["boards"] = {
            f"{b}:{port}": reference(b, port)
            for b in HOSTS
            for port in ((BOARD, BIG) if b in "ab" else (BOARD,))
        }
        (out / "meta.json").write_text(json.dumps(meta, indent=1))

        log("controls before measuring")
        for c in controls("prima", n_pos, n_neg, log):
            record("control", c)

        prober = Prober("a", "ab")
        shape("ab", None)
        bare = [prober.run("cov") for _ in range(1 if mode == "ci" else 3)]
        base = med([t for r in bare for t in r["times"]])
        via = [prober.run("pings", f"{ip('b', 'ab')}:{BOARD}") for _ in range(2)]
        nginx_ms = med([t for r in via for t in r["times"]])
        log(f"  no wall: http ping median {base:.2f} ms, {nginx_ms:.2f} ms through nginx")
        record("base", {"median_ms": base, "nginx_median_ms": nginx_ms, "runs": bare})

        if mode == "ci":
            fits = json.loads(PROFILES.read_text())["fits"]
            log(
                f"walls from {PROFILES.name}, measured on {json.loads(PROFILES.read_text())['run']}"
            )
            p5 = next(f for f in fits if f["name"] == "P5")
            now = validate(prober, p5["profile"], 2)
            c = {
                "control": "il muro P5 da' ancora i numeri del giro",
                "pass": abs(now["median_ms"] - p5["target"]["median_ms"]) <= 5 and now["lost"] == 0,
                "detail": now,
            }
            log(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['control']}: {now}")
            record("control", c)
        else:
            log("tuning the walls on the coverage test")
            fits = []
            for name, place, m, w, k in WALK + LIMITS:
                fits.append(tune(prober, base, name, place, m, w, k, mode == "quick", log))
                record("fit", fits[-1])
            (out / "profiles.json").write_text(
                json.dumps(
                    {
                        "run": out.name,
                        "fits": [
                            {k: f[k] for k in ("name", "place", "target", "profile")} for f in fits
                        ],
                    },
                    indent=1,
                )
            )
            p5 = next(f for f in fits if f["name"] == "P5")
            twin = twin_walls(prober, p5["profile"])
            c = {
                "control": "il muro P5 sul collegamento B-C da' gli stessi numeri che su A-B",
                "pass": twin["same"],
                "detail": twin,
            }
            log(f"  [{'PASS' if twin['same'] else 'FAIL'}] {c['control']}: {twin}")
            record("control", c)

        blocks = plan(fits, mode)
        rng.shuffle(blocks)
        meta["blocks_planned"] = len(blocks)
        (out / "meta.json").write_text(json.dumps(meta, indent=1))
        log(f"exchanges: {len(blocks)} blocks in random order")
        for name, p, flap, port, n in blocks:
            shape("ab", None)
            sentinel = exchange(refs={b: reference(b) for b in "ab"})
            record("sentinel", {"before": name, **sentinel})
            if not sentinel["ok"]:
                log(f"  SENTINEL FAILED before {name}: {sentinel}")
            refs = {b: reference(b, port) for b in "ab"}
            shape("ab", p)
            if flap:
                flap_start("ab", p, *flap)
            verdicts = [prober.run("cov") for _ in range(n_verdict)] if port == BOARD else []
            before = counters("ab")
            trials = []
            for i in range(n):
                if flap:
                    time.sleep(rng.uniform(0, flap[0]))  # a random moment of the cycle
                t = exchange(port=port, refs=refs)
                t.update(block=name, i=i)
                record("trial", t)
                trials.append(t)
            after = counters("ab")
            if flap:
                flap_stop("ab")
            record(
                "block",
                {
                    "name": name,
                    "profile": p,
                    "flap": flap,
                    "port": port,
                    "n": n,
                    "verdicts": verdicts,
                    "counters": [before, after],
                    "board_bytes": {b: sum(refs[b]["bytes"]) for b in refs},
                },
            )
            ok = sum(t["ok"] for t in trials)
            secs = sorted(t["seconds"] for t in trials if t["ok"])
            log(
                f"  {name}: {ok}/{n} within {WINDOW:.0f} s, slowest {secs[-1] if secs else '-'} s, "
                f"verdict {[v['verdict'] for v in verdicts]}"
            )

        log("the chain: A -> B -> C on the edge wall")
        for c in chain(p5["profile"], n_canary, rng, log):
            record("chain", c)

        log("controls at the end")
        for c in controls("dopo", n_pos, n_neg, log):
            record("control", c)
    except BaseException as error:  # Ctrl-C too: a run stopped halfway must say so
        log(f"STOPPED: {type(error).__name__}: {error}")
        record("stopped", {"error": f"{type(error).__name__}: {error}"})
        raise
    finally:
        results.close()
        try:
            report(out)
            log(f"report: {out / 'REPORT.md'}")
        except Exception as error:  # the data stay; the report can be written again
            log(f"report failed: {type(error).__name__}: {error}")
        if not args.keep:
            teardown()


# --- the report -------------------------------------------------------------------------------


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def nearest_rank(xs, q):
    return xs[max(0, math.ceil(q * len(xs)) - 1)] if xs else None


def witness(block, trials):
    """What each side's wall really carried, against the boards that arrived through it. Above
    1: the boards went through the wall (headers and TCP acknowledgements are the rest)."""
    b0, b1 = block["counters"]
    out = {}
    for box, leg in (("a", "first"), ("b", "second")):  # A's wall carries A's board to B
        dbytes, dpkt = b1[box][0] - b0[box][0], b1[box][1] - b0[box][1]
        arrived = sum(t[leg]["bytes"] for t in trials if t[leg] and t[leg]["ok"])
        out[box] = {
            "ratio": dbytes / arrived if arrived else None,
            "packet": dbytes / dpkt if dpkt else None,
        }
    return out


def report(out):
    rows = [json.loads(line) for line in (out / "results.jsonl").read_text().splitlines()]
    meta = json.loads((out / "meta.json").read_text()) if (out / "meta.json").exists() else {}
    controls_ = [r for r in rows if r["type"] == "control"]
    chain_ = [r for r in rows if r["type"] == "chain"]
    fits = [r for r in rows if r["type"] == "fit"]
    blocks = [r for r in rows if r["type"] == "block"]
    trials = [r for r in rows if r["type"] == "trial"]
    sentinels = [r for r in rows if r["type"] == "sentinel"]
    stopped = [r for r in rows if r["type"] == "stopped"]
    base = next((r for r in rows if r["type"] == "base"), None)
    odd = [
        t
        for t in trials
        for leg in (t["first"], t["second"])
        if leg and leg["kind"] not in ("ok", "timeout")
    ]
    seen = {b["name"]: witness(b, [t for t in trials if t["block"] == b["name"]]) for b in blocks}
    carried = all(
        w["ratio"] is None or w["ratio"] >= 1.0 for ws in seen.values() for w in ws.values()
    )
    single = all(
        w["packet"] is None or w["packet"] <= 1514 for ws in seen.values() for w in ws.values()
    )
    witnessed = [
        {
            "control": "testimone: ogni muro ha portato davvero le bacheche arrivate",
            "pass": carried,
        },
        {"control": "testimone: un pacchetto per trama, mai pacchi da 64 kB", "pass": single},
    ]
    checks = controls_ + witnessed + chain_
    stages = {c["control"].split(":")[0] for c in controls_}
    complete = (
        {"prima", "dopo"} <= stages
        and bool(chain_)
        and len(blocks) == meta.get("blocks_planned", -1)
    )
    valid = (
        not stopped
        and complete
        and all(c["pass"] for c in checks)
        and all(s["ok"] for s in sentinels)
        and not odd
        and all(f["ok"] for f in fits)
    )
    boards = meta.get("boards", {})
    kb = lambda key: f"{sum(boards[key]['bytes']) / 1000:.0f} kB" if key in boards else "?"  # noqa: E731
    fmt = lambda x: f"{x:.2f}" if x is not None else "-"  # noqa: E731
    L = [f"# Tre Campanili, corsa {out.name}", ""]
    L.append(
        f"**Esito: {'VALIDA' if valid else 'NON VALIDA'}.** Controlli "
        f"{sum(c['pass'] for c in checks)}/{len(checks)} superati, sentinelle "
        f"{sum(s['ok'] for s in sentinels)}/{len(sentinels)}, anomalie {len(odd)}, blocchi "
        f"{len(blocks)}/{meta.get('blocks_planned', '?')}"
        + (f", taratura {sum(f['ok'] for f in fits)}/{len(fits)} nei limiti." if fits else ".")
    )
    if stopped:
        L.append(f"\nInterrotta: `{stopped[0]['error']}`")
    L += [
        "",
        f"Modalita' {meta.get('mode')}, commit `{meta.get('commit')}`"
        + (
            f" con {meta['uncommitted_files']} file non salvati"
            if meta.get("uncommitted_files")
            else ""
        )
        + f", seme {meta.get('seed')}, finestra {meta.get('window_s', WINDOW):.0f} s. "
        f"Docker {meta.get('docker', '?')}. "
        + " · ".join(v for v in meta.get("versions", []) if v)
        + ".",
        "",
    ]
    L += [
        f"Bacheche: realistica {kb('a:80')}, piena {kb('a:81')} (500 annunci, ogni campo pieno). "
        "Lo scambio le scarica senza compressione: il caso peggiore."
    ]
    if base:
        L.append(
            f"Senza muro: ping {fmt(base['median_ms'])} ms diretto, "
            f"{fmt(base.get('nginx_median_ms'))} ms attraverso nginx."
        )
    L += ["", "## Controlli", "", "| Controllo | Esito |", "|---|---|"]
    L += [
        f"| {c['control']} | {'PASS' if c['pass'] else '**FAIL**'} |" for c in controls_ + witnessed
    ]
    if fits:
        L += [
            "",
            "## Taratura dei muri sulla prova di copertura",
            "",
            "| Punto | Misurato: mediana / peggiore ms, kbit/s | Simulato | Ritardo per lato | "
            "Velocita' del filo | Esito |",
            "|---|---|---|---|---|---|",
        ]
        for f in fits:
            t, v, p = f["target"], f["validation"], f["profile"]
            rate = "senza limite" if p["rate"] == UNLIMITED else f"{p['rate']} kbit/s"
            L.append(
                f"| {f['name']} {f['place']} | {t['median_ms']} / {t['worst_ms']}, "
                f"{t['kbps']} | {v['median_ms']} / {v['worst_ms']}, {v['kbps']} | "
                f"{p['delay']} ms | {rate} | {'ok' if f['ok'] else 'NO'}, {f['speed']} |"
            )
        L += [
            "",
            "'prudente': anche senza limite di velocita' il muro simulato e' piu' lento di "
            "quello vero, quindi il banco sbaglia dalla parte del pessimismo. Il ping peggiore "
            "isolato non si riproduce: al suo posto, perdite e buchi qui sotto.",
            "",
        ]
    L += [
        "## Scambio delle bacheche in una visita",
        "",
        "| Blocco | Riusciti | 95% (Wilson) | Mediana s | p95 s | Max s | Bacheca | "
        "Verdetto della prova | Testimone A/B |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for b in blocks:
        ts = [t for t in trials if t["block"] == b["name"]]
        ok = sum(t["ok"] for t in ts)
        lo, hi = wilson(ok, len(ts))
        secs = sorted(t["seconds"] for t in ts if t["ok"])
        board = f"{sum(b['board_bytes'].values()) / 2000:.0f} kB"
        verdicts = {}
        for v in b["verdicts"]:
            verdicts[v["verdict"]] = verdicts.get(v["verdict"], 0) + 1
        said = ", ".join(f"{k} {n}" for k, n in verdicts.items()) or "-"
        w = seen[b["name"]]
        ratio = "/".join(f"{w[x]['ratio']:.2f}x" if w[x]["ratio"] else "-" for x in "ab")
        L.append(
            f"| {b['name']} | {ok}/{len(ts)} | {lo:.0%}-{hi:.0%} | "
            f"{fmt(statistics.median(secs) if secs else None)} | "
            f"{fmt(nearest_rank(secs, 0.95))} | {fmt(secs[-1] if secs else None)} | {board} | "
            f"{said} | {ratio} |"
        )
    L += [
        "",
        "Secondi: lo scambio intero, andata e ritorno. Testimone: byte passati dal muro di "
        "ciascun lato diviso byte delle bacheche arrivate.",
        "",
    ]
    if chain_:
        L += ["## Catena A -> B -> C, sul muro del bordo (P5) in tutti e due i collegamenti", ""]
        L += [f"- {'PASS' if c['pass'] else '**FAIL**'}: {c['control']}" for c in chain_]
        L.append("")
    if odd:
        L += ["## Anomalie (errori che non sono il tempo scaduto)", ""]
        L += [
            f"- {t['block']} #{t['i']}: {t['first']['kind']} {t['first']['why']} / "
            f"{(t['second'] or {}).get('kind')}"
            for t in odd[:20]
        ]
    (out / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return valid


def stopped(signum, _frame):
    raise KeyboardInterrupt(signal.Signals(signum).name)


def main():
    # Stopped by hand, by the CI or by the system, the run says so and cleans up: even started
    # in the background, where a shell hands it Ctrl-C ignored.
    signal.signal(signal.SIGINT, stopped)
    signal.signal(signal.SIGTERM, stopped)
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true", help="every step once, about 15 minutes")
    p.add_argument("--ci", action="store_true", help="the short check, on bench/profiles.json")
    p.add_argument("--seed", type=int, default=20261030)
    p.add_argument("--keep", action="store_true", help="leave the containers up afterwards")
    p.add_argument("--report", type=Path, help="write the report of RUN again")
    a = p.parse_args()
    if a.report:
        valid = report(a.report)
        print((a.report / "REPORT.md").read_text())
        sys.exit(0 if valid else 1)
    run(a)
    newest = max(RUNS.iterdir(), key=lambda d: d.stat().st_mtime)
    sys.exit(0 if report(newest) else 1)


if __name__ == "__main__":
    main()
