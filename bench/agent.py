# DEVELOPED BY CARROTSTUDIO software house
"""Stand-in for the board exchange between two Campaniles, which Campanile doesn't have yet.
Within the time a visit leaves: download the neighbour's board on one connection, through its
nginx, check it byte for byte against what the neighbour really holds, and add the posts this
Campanile lacks. A connection that fails is tried again while the window lasts. Uncompressed on
purpose: the worst case (a real sync would ask nginx for gzip and be faster).

    agent.py PEER BUDGET EXPECT_POSTS EXPECT_NOTICES [--merge DATABASE]

PEER is host:port. One JSON line out; a failure is a result, never a crash, and "kind" says
which: ok, timeout (the window ended first), mismatch (the content isn't the neighbour's),
http, error. Only the time on the link counts against BUDGET; adding the posts comes after.
"""

import errno
import hashlib
import http.client
import json
import re
import sys
import time
from pathlib import Path

MARK = re.compile(r"\[([A-Z]+-N?\d+)\]")
PATHS = ("/api/posts", "/api/notices")
RETRY = 0.5  # s between attempts


class WindowOver(Exception):
    pass


class Refused(Exception):
    pass


def fetch_board(peer, deadline):
    """One attempt: the two answers a phone gets for the board, as bytes."""
    host, port = peer.rsplit(":", 1)

    def left():
        rest = deadline - time.monotonic()
        if rest <= 0:
            raise WindowOver("window over")
        return rest

    conn = http.client.HTTPConnection(host, int(port), timeout=left())
    bodies = []
    try:
        for path in PATHS:
            if conn.sock is None:
                conn.timeout = left()
                conn.connect()
            conn.sock.settimeout(left())
            conn.request("GET", path, headers={"Accept": "application/json"})
            response = conn.getresponse()
            if response.status != 200:
                raise Refused(f"HTTP {response.status} on {path}")
            chunks = []
            while True:
                if conn.sock is not None:
                    conn.sock.settimeout(left())
                chunk = response.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            bodies.append(b"".join(chunks))
        left()  # the last byte arriving after the window doesn't count
    finally:
        conn.close()
    return bodies


def error_kind(error):
    if isinstance(error, TimeoutError):
        return "timeout"
    if getattr(error, "errno", None) in (errno.ENETUNREACH, errno.EHOSTUNREACH):
        return "unreachable"
    if isinstance(error, (ConnectionError, http.client.HTTPException)):
        return "reset"
    return "other"


def fetch_until(peer, deadline, out):
    while True:
        out["tries"] += 1
        try:
            return fetch_board(peer, deadline)
        except (OSError, http.client.HTTPException) as error:
            out["last_error"] = f"{type(error).__name__}: {error}"[:160]
            out["last_error_kind"] = error_kind(error)
            if deadline - time.monotonic() <= RETRY:
                raise WindowOver("window over") from error
            time.sleep(RETRY)


def merge_into(path, posts):
    sys.path.insert(0, "/h/campanile")
    import store

    db = store.Store(Path(path))
    try:
        have = {m for p in db.list_posts(limit=100_000) for m in MARK.findall(p["text"])[:1]}
        added = 0
        for p in reversed(posts):  # oldest first, as they were written
            marks = MARK.findall(p["text"])
            if marks and marks[0] not in have:
                db.add_post(p["kind"], p["category"], p["text"], p["area"], p["contact"])
                have.add(marks[0])
                added += 1
        return added
    finally:
        db.close()


def main():
    peer, budget, want_posts, want_notices = sys.argv[1:5]
    merge = sys.argv[sys.argv.index("--merge") + 1] if "--merge" in sys.argv else None
    out = {
        "ok": False,
        "kind": "",
        "why": "",
        "seconds": None,
        "bytes": 0,
        "tries": 0,
        "merged": None,
        "wall": time.time(),
    }
    started = time.monotonic()
    try:
        posts, notices = fetch_until(peer, started + float(budget), out)
        out["seconds"] = round(time.monotonic() - started, 4)
        out["bytes"] = len(posts) + len(notices)
        got = (hashlib.sha256(posts).hexdigest(), hashlib.sha256(notices).hexdigest())
        if got != (want_posts, want_notices):  # checked before the content is even read
            out.update(kind="mismatch", why="content differs from the neighbour's")
        else:
            if merge:
                begun = time.monotonic()
                out["merged"] = merge_into(merge, json.loads(posts)["posts"])
                out["merge_seconds"] = round(time.monotonic() - begun, 4)
            out.update(ok=True, kind="ok")
    except WindowOver:
        out.update(kind="timeout", why="window over")
    except Refused as error:
        out.update(kind="http", why=str(error))
    except Exception as error:  # every failure is counted, never dropped
        out.update(kind="error", why=f"{type(error).__name__}: {error}"[:200])
    if out["seconds"] is None:
        out["seconds"] = round(time.monotonic() - started, 4)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
