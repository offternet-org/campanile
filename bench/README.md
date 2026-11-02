<!-- DEVELOPED BY CARROTSTUDIO software house -->
# The bench: three Campaniles on one computer

Can two Campaniles in two flats swap their boards in the few seconds a visit leaves, intact,
and pass a message on to a third? This bench answers on Wi-Fi measured in a real building, with
the real Campanile behind the real nginx of a Raspberry Pi. What it found, and what it can't
tell: [docs/BENCH.md](../docs/BENCH.md) · in italiano [docs/BANCO.md](../docs/BANCO.md).

```sh
python3 bench/chain.py            # the whole bench, about 90 minutes
python3 bench/chain.py --quick    # every step once, about 15 minutes
python3 bench/chain.py --ci       # the short check CI runs on every change, about 2 minutes
```

Needs Docker on a Linux kernel with netem (Linux, or Docker Desktop / Colima on a Mac) and
nothing else: the image is built from [Dockerfile](Dockerfile), Debian 13 like Raspberry Pi OS
Trixie. Each run writes its report, raw data and configuration to `bench/runs/`; the published
ones are in [results/](results/).

| File | What it is |
|---|---|
| [chain.py](chain.py) | The run: containers, walls, controls, exchanges, the chain, the report |
| [agent.py](agent.py) | Stand-in for the board exchange Campanile doesn't do yet |
| [probe.py](probe.py) | Campanile's coverage test, as a phone runs it, to tune the walls |
| [board.py](board.py) | What a Campanile holds, asked on its own loopback |
| [seed.py](seed.py) | Boards filled as people would, every post with a mark of its own |
| [proxy.py](proxy.py) | Flips one bit on the way: the control for the check itself |
| [flap.py](flap.py) | A link that comes and goes |
| [profiles.json](profiles.json) | The walls tuned by the published run, used by `--ci` |
