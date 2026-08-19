#!/usr/bin/env python3
"""Select affected container packages from a rendered Bake definition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def package_targets(bake: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return public Bake targets that follow the repository package convention."""
    targets = bake.get("target", {})
    if not isinstance(targets, dict):
        raise ValueError("Bake output does not contain a target object")

    packages: dict[str, dict[str, Any]] = {}
    for name, target in targets.items():
        if not isinstance(name, str) or not isinstance(target, dict) or name.startswith("_"):
            continue
        if target.get("dockerfile") == f"images/{name}/Dockerfile":
            packages[name] = target
    return packages


def reverse_dependencies(packages: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    """Map a target to packages that consume it through target: contexts."""
    dependents = {name: set() for name in packages}
    for name, target in packages.items():
        contexts = target.get("contexts", {})
        if not isinstance(contexts, dict):
            continue
        for context in contexts.values():
            if isinstance(context, str) and context.startswith("target:"):
                dependency = context.removeprefix("target:")
                if dependency in dependents:
                    dependents[dependency].add(name)
    return dependents


def dependencies(packages: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    """Map a package to the repository targets it consumes through target: contexts."""
    result = {name: set() for name in packages}
    for name, target in packages.items():
        contexts = target.get("contexts", {})
        if not isinstance(contexts, dict):
            continue
        for context in contexts.values():
            if isinstance(context, str) and context.startswith("target:"):
                dependency = context.removeprefix("target:")
                if dependency in result:
                    result[name].add(dependency)
    return result


def select_targets(bake: dict[str, Any], changed_files: list[str]) -> tuple[list[str], list[str]]:
    """Return selected packages and Spack lockfiles to regenerate."""
    packages = package_targets(bake)
    package_names = set(packages)
    changed = set(changed_files)
    selected: set[str] = set()
    refresh_locks: set[str] = set()

    if {"docker-bake.hcl", ".dockerignore", "config/image-tags.json"} & changed:
        selected.update(package_names)

    for path in changed:
        parts = Path(path).parts
        if len(parts) >= 3 and parts[0] == "images" and parts[1] in package_names:
            selected.add(parts[1])

        if path == "config/spack/base.yaml" and "ubuntu" in package_names:
            selected.add("ubuntu")
            refresh_locks.add("ubuntu")

        if len(parts) == 3 and parts[:2] == ("config", "spack") and path.endswith(".yaml"):
            package = Path(parts[2]).stem
            tracker_package = package.split("-", 1)[0]
            if package in package_names and package != "base":
                selected.add(package)
                refresh_locks.add(package)
            elif tracker_package in package_names and tracker_package != "base":
                selected.add(tracker_package)

        # Generated lockfiles are also direct Docker build inputs. Do not refresh
        # one that was deliberately changed; validate and publish that exact lock.
        if len(parts) == 3 and parts[:2] == ("config", "spack") and path.endswith(".lock"):
            package = Path(parts[2]).stem
            if package in package_names:
                selected.add(package)

    dependents = reverse_dependencies(packages)
    pending = list(selected)
    while pending:
        dependency = pending.pop()
        for dependent in dependents[dependency]:
            if dependent not in selected:
                selected.add(dependent)
                pending.append(dependent)
            if dependency in refresh_locks:
                refresh_locks.add(dependent)

    required = list(selected)
    package_dependencies = dependencies(packages)
    while required:
        package = required.pop()
        for dependency in package_dependencies[package]:
            if dependency not in selected:
                selected.add(dependency)
                required.append(dependency)

    return sorted(selected), sorted(refresh_locks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bake-json", type=Path, required=True)
    parser.add_argument("--changed-files", type=Path, required=True)
    args = parser.parse_args()

    bake = json.loads(args.bake_json.read_text())
    changed_files = [line for line in args.changed_files.read_text().splitlines() if line]
    targets, refresh_locks = select_targets(bake, changed_files)
    print(
        json.dumps(
            {
                "catalog_targets": sorted(package_targets(bake)),
                "refresh_locks": refresh_locks,
                "targets": targets,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
