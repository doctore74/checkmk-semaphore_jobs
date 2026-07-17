#!/usr/bin/env python3
"""Reproducibly build the Semaphore Jobs Checkmk MKP."""
from pathlib import Path
import json
import pprint
import tarfile
import tempfile

NAME = "semaphore_jobs"
VERSION = "1.2.0"
BASE = Path(__file__).resolve().parent
PLUGIN_BASE = BASE / "local/lib/python3/cmk_addons/plugins"
FAMILY = PLUGIN_BASE / NAME
OUTPUT = BASE / f"{NAME}-{VERSION}.mkp"

files = sorted(
    str(path.relative_to(PLUGIN_BASE))
    for path in FAMILY.rglob("*")
    if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts
)
info = {
    "author": "Christian Wirtz <doc[at]snowheaven.de>",
    "description": (
        "Special agent for monitoring Semaphore UI jobs, queue states, task ages, "
        "recent failures, and API data quality."
    ),
    "download_url": "",
    "files": {"cmk_addons_plugins": files},
    "name": NAME,
    "title": "Semaphore UI Jobs",
    "version": VERSION,
    "version.min_required": "2.5.0p1",
    "version.packaged": "2.5.0p1",
    "version.usable_until": "2.5.99",
}

with tempfile.TemporaryDirectory() as temporary:
    build = Path(temporary)
    with (build / "info").open("w", encoding="utf-8") as handle:
        pprint.pprint(info, stream=handle, sort_dicts=False, width=100)
    with (build / "info.json").open("w", encoding="utf-8") as handle:
        json.dump(info, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    with tarfile.open(build / "cmk_addons_plugins.tar", "w") as archive:
        for relative in files:
            archive.add(PLUGIN_BASE / relative, arcname=relative, recursive=False)
    with tarfile.open(OUTPUT, "w:gz") as archive:
        for name in ("info", "info.json", "cmk_addons_plugins.tar"):
            archive.add(build / name, arcname=name, recursive=False)
print(OUTPUT)
