#!/usr/bin/env python3
"""Split data/upstream872 into N shards for the farm tail-atsp harness.

Round-robin over the *sorted* file list, so every shard sees the same mix of
easy and heavy-tail instances: per-shard runtimes then concentrate and the wall
clock is the mean, not the worst shard. (Contiguous blocks would be the sorted-
order-bias trap in another costume.)

    python3 analysis/farm/ta_shard.py [--shards 24] [--out <dir>] [--tar]

Then ship the tarball and extract on the PC:

    COPYFILE_DISABLE=1 tar -czf shards.tgz shards      # DISABLE is mandatory:
    scp shards.tgz transcribe:/F:/superpermFarm/tailatsp/   # bsdtar otherwise
    ssh transcribe 'cd /d F:\\superpermFarm\\tailatsp && tar -xzf shards.tgz'
                                                       # ships a ._x twin per
                                                       # file and hides it from
                                                       # `tar -t`
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys

DEFAULT_SRC = pathlib.Path("data/upstream872")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=pathlib.Path, default=DEFAULT_SRC)
    ap.add_argument("--out", type=pathlib.Path, required=True,
                    help="destination dir; a 'shards/' subtree is created inside")
    ap.add_argument("--shards", type=int, default=24)
    ap.add_argument("--tar", action="store_true", help="also build shards.tgz")
    a = ap.parse_args()

    if not a.src.is_dir():
        print(f"no corpus at {a.src} — rebuild with analysis/counting/upstream872_dump.py",
              file=sys.stderr)
        return 1

    files = sorted(p.name for p in a.src.iterdir() if p.is_file() and not p.name.startswith("._"))
    root = a.out / "shards"
    if root.exists():
        shutil.rmtree(root)
    for i in range(a.shards):
        (root / f"s{i:02d}").mkdir(parents=True)

    counts = [0] * a.shards
    for k, name in enumerate(files):
        d = k % a.shards
        os.link(a.src / name, root / f"s{d:02d}" / name)   # hardlink: no copy cost
        counts[d] += 1
    print(f"{len(files)} walks -> {a.shards} shards ({min(counts)}..{max(counts)} each) at {root}")

    if a.tar:
        env = dict(os.environ, COPYFILE_DISABLE="1")
        subprocess.run(["tar", "-czf", "shards.tgz", "shards"], cwd=a.out, check=True, env=env)
        print(f"wrote {a.out / 'shards.tgz'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
