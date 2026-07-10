#!/usr/bin/env python3
"""Allocate immutable daily release tags from the registry state."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import subprocess
from typing import Callable, Iterable


@dataclass(frozen=True)
class RegistryEntry:
    revision: str | None


Probe = Callable[[str, str], RegistryEntry | None]


def suffix_for_index(index: int) -> str:
    """Return a, b, ..., z, aa, ab, ... for a zero-based index."""
    if index < 0:
        raise ValueError("suffix index must be non-negative")

    characters: list[str] = []
    while True:
        index, remainder = divmod(index, 26)
        characters.append(chr(ord("a") + remainder))
        if index == 0:
            return "".join(reversed(characters))
        index -= 1


def tag_for_index(date: str, index: int) -> str:
    """Return the bare date first, followed by alphabetically suffixed tags."""
    if index == 0:
        return date
    return f"{date}-{suffix_for_index(index - 1)}"


def select_release_tag(
    date: str,
    catalog_targets: Iterable[str],
    selected_targets: Iterable[str],
    revision: str,
    probe: Probe,
) -> tuple[str, bool]:
    """Return the next global tag, or reuse a complete matching prior release."""
    catalog = sorted(set(catalog_targets))
    selected = sorted(set(selected_targets))
    if not catalog or not selected:
        raise ValueError("catalog and selected targets must both be non-empty")
    if not set(selected).issubset(catalog):
        raise ValueError("selected targets must be in the package catalog")

    for index in range(26**3):
        tag = tag_for_index(date, index)
        entries = {target: probe(target, tag) for target in catalog}

        selected_match = all(
            entries[target] is not None and entries[target].revision == revision
            for target in selected
        )
        batch_consistent = all(entry is None or entry.revision == revision for entry in entries.values())
        if selected_match and batch_consistent:
            return tag, True

        if all(entry is None for entry in entries.values()):
            return tag, False

    raise RuntimeError("could not find an available release suffix")


def registry_probe(registry: str) -> Probe:
    def probe(target: str, tag: str) -> RegistryEntry | None:
        reference = f"{registry}/{target}:{tag}"
        result = subprocess.run(
            ["docker", "buildx", "imagetools", "inspect", reference, "--format", "{{json .Config.Labels}}"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        try:
            labels = json.loads(result.stdout)
        except json.JSONDecodeError:
            labels = {}
        if not isinstance(labels, dict):
            labels = {}
        return RegistryEntry(labels.get("org.opencontainers.image.revision"))

    return probe


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--catalog-target", action="append", required=True)
    parser.add_argument("--selected-target", action="append", required=True)
    args = parser.parse_args()

    tag, reuse = select_release_tag(
        args.date,
        args.catalog_target,
        args.selected_target,
        args.revision,
        registry_probe(args.registry),
    )
    print(json.dumps({"reuse": reuse, "tag": tag}, sort_keys=True))


if __name__ == "__main__":
    main()
