# DEVELOPED BY CARROTSTUDIO software house
"""The phone's coverage test as close as a script gets to it: the same requests to the same
Campanile, with the gaps, deadlines and arithmetic of coverage.js as it was on the walk (20
pings, then the 256 kB piece), and the verdict from the Campanile's own function. The bench
uses it to tune the simulated walls until they give the numbers the phone gave.

    probe.py cov HOST:PORT       the whole test
    probe.py pings HOST:PORT     its 20 pings alone, to tune the delay
    probe.py sample HOST:PORT    one ping to open the connection, then the piece, to tune the speed
"""

import http.client
import json
import math
import sys
import time

sys.path.insert(0, "/h/campanile")
import api

PINGS, FIRST, GAP = 20, 3, 0.100
PING_WAIT, SAMPLE_WAIT = 2.0, 30.0


def js_round(x):
    return math.floor(x + 0.5)  # Math.round, not Python's round-half-even


class Browser:
    """One keep-alive connection, like the phone's. A request that isn't back by its deadline
    is abandoned with its connection, as an aborted fetch is."""

    def __init__(self, peer):
        self.host, port = peer.rsplit(":", 1)
        self.port = int(port)
        self.conn = None
        self.statuses = {}

    def get(self, path, wait):
        started = time.monotonic()
        deadline = started + wait
        status = "none"
        try:
            if self.conn is None:
                self.conn = http.client.HTTPConnection(self.host, self.port, timeout=wait)
            if self.conn.sock is None:
                self.conn.timeout = wait
                self.conn.connect()
            self.conn.sock.settimeout(wait)
            self.conn.request("GET", path, headers={"Cache-Control": "no-store"})
            response = self.conn.getresponse()
            body = b""
            while True:
                rest = deadline - time.monotonic()
                if rest <= 0:
                    raise TimeoutError("deadline")
                if self.conn.sock is not None:
                    self.conn.sock.settimeout(rest)
                chunk = response.read(65536)
                if not chunk:
                    break
                body += chunk
            status = response.status
            return status, (time.monotonic() - started) * 1000, body
        except (OSError, http.client.HTTPException):
            if self.conn:
                self.conn.close()
            self.conn = None
            return None
        finally:
            self.statuses[status] = self.statuses.get(status, 0) + 1


def pings(browser):
    for _ in range(FIRST):
        if browser.get("/api/coverage/ping", PING_WAIT):
            break
    else:
        return None
    times = []
    for i in range(1, PINGS + 1):
        answer = browser.get(f"/api/coverage/ping?n={i}", PING_WAIT)
        if answer and 200 <= answer[0] < 300:
            times.append(answer[1])
        time.sleep(GAP)
    return sorted(times)


def coverage(browser, with_sample=True):
    times = pings(browser)
    if times is None:
        return {
            "sent": FIRST,
            "lost": FIRST,
            "median_ms": None,
            "worst_ms": None,
            "kbps": None,
            "times": [],
        }
    kbps = sample(browser) if with_sample else None
    return {
        "sent": PINGS,
        "lost": PINGS - len(times),
        "median_ms": js_round(times[len(times) // 2]) if times else None,
        "worst_ms": js_round(times[-1]) if times else None,
        "kbps": kbps,
        "times": [round(t, 2) for t in times],
    }


def sample(browser):
    answer = browser.get(f"/api/coverage/sample?n={time.time_ns()}", SAMPLE_WAIT)
    if answer and 200 <= answer[0] < 300:
        return js_round(len(answer[2]) * 8 / answer[1])  # bits a millisecond: kbit/s
    return None


def main():
    mode, peer = sys.argv[1], sys.argv[2]
    browser = Browser(peer)
    if mode == "cov":
        out = coverage(browser)
        out["verdict"] = api.coverage_verdict(
            out["sent"], out["lost"], out["median_ms"], out["worst_ms"], out["kbps"]
        )
    elif mode == "pings":
        out = coverage(browser, with_sample=False)
    else:
        browser.get("/api/coverage/ping", PING_WAIT)
        time.sleep(GAP)
        out = {"kbps": sample(browser)}
    out["statuses"] = {str(k): v for k, v in browser.statuses.items()}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
