# DEVELOPED BY CARROTSTUDIO software house
"""The bench's hands on a board, never the stand-in's: what a Campanile holds, asked on its own
loopback and past nginx, so no simulated wall is in the way.

    board.py reference HOST:PORT        fingerprints of the two answers the stand-in downloads
    board.py find HOST:PORT MARK        the posts carrying MARK, every field
    board.py add DATABASE KIND CATEGORY TEXT AREA CONTACT
"""

import hashlib
import json
import sys
import time
from pathlib import Path

from agent import fetch_board


def main():
    mode = sys.argv[1]
    if mode == "add":
        sys.path.insert(0, "/h/campanile")
        import store

        db = store.Store(Path(sys.argv[2]))
        try:
            post_id, _ = db.add_post(*sys.argv[3:8])
        finally:
            db.close()
        print(json.dumps({"id": post_id}))
        return
    posts, notices = fetch_board(sys.argv[2], time.monotonic() + 10)
    board = json.loads(posts)["posts"]
    if mode == "reference":
        print(
            json.dumps(
                {
                    "posts": hashlib.sha256(posts).hexdigest(),
                    "notices": hashlib.sha256(notices).hexdigest(),
                    "bytes": [len(posts), len(notices)],
                    "count": len(board),
                }
            )
        )
    elif mode == "find":
        mark = f"[{sys.argv[3]}]"
        print(json.dumps({"count": len(board), "found": [p for p in board if mark in p["text"]]}))


if __name__ == "__main__":
    main()
