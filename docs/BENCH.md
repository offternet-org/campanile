# Three Campaniles on one computer

Italian version: [BANCO.md](BANCO.md).

Two Campaniles in two flats, and a visit of a few seconds: does the board get across, intact,
and does a message go on to a third Campanile? Campanile doesn't sync yet. This bench measures
whether the Wi-Fi of a real building would carry it, before anyone writes the sync.

**In short:** wherever a phone had signal in the building, two Campaniles swapped their boards
in under 0.4 s, 50 times out of 50. A message crossed from A to C through B intact, 20 times out
of 20. Two limits show up well before the radio does: a full board doesn't fit in a visit at
the edge of "fair", and links that lose a fifth of their packets start to fail.

Run of 2 November 2026, valid: 27 of 27 controls passed.
[Report](../bench/results/2026-11-02/REPORT.md) · [raw data](../bench/results/2026-11-02/).

## What is real, what stands in

| Real | Standing in |
|---|---|
| Campanile and its answers, behind nginx written by `raspberry/nginx-site.sh`, on Debian 13 like Raspberry Pi OS Trixie | The board exchange, which Campanile doesn't do yet: [agent.py](../bench/agent.py) downloads the neighbour's board, checks it byte for byte (SHA-256) and adds what is missing |
| The links' numbers: five spots of a flat and its landing, measured on 30 October 2026 with an iPhone and [Campanile's coverage test](../campanile/web/coverage.js) | Each link: a delay and a speed (Linux netem), tuned until the same coverage test gives the phone's numbers |
| The boards: 120 posts per Campanile, 28 kB; and the largest a phone can be sent, 500 posts with every field full, 408 kB | The window of a visit: 30 s, minus 10 s to join the neighbour's Wi-Fi. A choice, not a measurement |
| The verdict the coverage test gives (`api.coverage_verdict`) | The exchange downloads the board uncompressed, the worst case: nginx would gzip it |

Each Campanile runs in its own container; A and C sit on two separate networks, and B on both.
A can reach C only through B, and B doesn't route packets.

## How it checks itself

Every number counts only if the bench has first been seen failing where it should. Before
measuring, and again at the end:

- with no wall the exchange works; with a closed wall nothing gets through, and it waits for the
  whole window before saying so;
- a board checked against the wrong fingerprint is refused, and a single bit flipped on the way
  is caught, while the same go-between without the fault passes everything;
- a window too short fails;
- the wall on A-B doesn't touch B-C, and the other way round; A can't reach C directly;
- for each block, the packet counters show that the boards really crossed the wall, one packet
  per frame.

The tuning is checked too: the same wall on both links gives the same numbers, measured side by
side. A run that misses a control, or stops halfway, reports NON VALIDA. On every change to
Campanile or the bench, [CI](../.github/workflows/bench.yml) runs a short version (`--ci`, about
2 minutes). With the fingerprint check planted out of the code, that CI fails.

## Results

The five measured spots, and the poorest links the coverage test still calls good and fair:

| Link | Measured by the phone | Exchanges done in 20 s | Slowest |
|---|---|---|---|
| 6 m away | 17 ms, 17.3 Mbit/s | 50/50 | 0.14 s |
| Front door | 44 ms, 14.2 Mbit/s | 50/50 | 0.36 s |
| Corridor, door shut | 18 ms, 24.4 Mbit/s | 50/50 | 0.16 s |
| By the lift | 23 ms, 12.6 Mbit/s | 50/50 | 0.19 s |
| 3 m past the lift, the edge | 35 ms, 8.1 Mbit/s | 50/50 | 0.29 s |
| Just inside "good" | 142 ms, 2.1 Mbit/s | 50/50 | 1.21 s |
| Just inside "fair" | 570 ms, 0.3 Mbit/s | 50/50 | 5.24 s |

50 of 50 means at least 93% with 95% confidence (Wilson interval). At the front door, even with
no speed limit, the simulated link stays slower than the real one: there the bench errs on the
pessimistic side.

Harder conditions, on the edge link:

| Condition | Exchanges done in 20 s | Slowest |
|---|---|---|
| Full board, 408 kB | 30/30 | 0.95 s |
| Full board at the edge of "fair" | **0/30** | never in time |
| 5% of packets lost | 30/30 | 1.44 s |
| 10% lost | 30/30 | 5.36 s |
| 20% lost | 28/30 | 13.2 s |
| 30% lost | 18/30 | 19.7 s |
| 50% lost | 0/30 | never in time |
| Link down 2 s every 4 s | 29/30 | 8.0 s |
| Link down 5 s every 10 s | 30/30 | 8.0 s |
| Link down 10 s every 20 s | 30/30 | 11.5 s |
| "Fair" with 5% lost | 30/30 | 18.3 s |

**The chain**, on the edge link both ways: the first time, B received A's 120 posts and C
received 240, A's included. The second time nothing was added twice. 20 test posts out of 20
crossed from A to C, identical field by field. With B-C cut, a post waited at B and went on as
soon as the link came back.

**The coverage test as a go/no-go:** in the blocks where it said "good" or "fair", 469 exchanges
out of 470 were done in time. Where it said "bad", some were and some weren't.

**What this means for the sync, when it is written:** send only what's new, never the whole
board; and retry by itself after a gap, rather than wait on TCP: on a link never down for more
than 2 s, exchanges took up to 8 s, most likely TCP's backoff.

## What it doesn't tell

- **Whether two Raspberry Pis see each other at all.** The links copy an iPhone and a home router
  on 5 GHz along one floor. A Raspberry Pi has a small antenna and usually works on 2.4 GHz;
  floors weren't measured. That takes two real Raspberry Pis.
- **The worst ping of the edge** (763 ms in one test) isn't reproduced: losses and gaps, harder
  than it, take its place.
- **Compression:** a real sync would ask nginx for gzip and be faster than these figures.
- **A Raspberry Pi's CPU and power:** the containers ran on a Mac, 2 CPUs.
- **The 10 s to join a neighbour's Wi-Fi** is assumed, not measured.

## Run it

```sh
python3 bench/chain.py            # the whole bench, about 90 minutes
python3 bench/chain.py --quick    # every step once, about 15 minutes
python3 bench/chain.py --ci       # the short check, about 2 minutes
```

Docker on a Linux kernel with netem is all it needs (Linux, or Docker Desktop / Colima on a
Mac). Each run writes its report, raw data and configuration, including the exact fingerprint
of the code it ran, to `bench/runs/`. More in [bench/README.md](../bench/README.md).
