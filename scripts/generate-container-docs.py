#!/usr/bin/env python3
"""Render a repository catalog from inventory files embedded in a container."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def read_metadata(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def extract_inventory(image: str) -> Path:
    tempdir = Path(tempfile.mkdtemp(prefix="container-inventory-"))
    container = subprocess.check_output(["docker", "create", image], text=True).strip()
    try:
        subprocess.run(
            ["docker", "cp", f"{container}:/usr/share/ornl-mdf/inventory", str(tempdir)],
            check=True,
        )
    finally:
        subprocess.run(["docker", "rm", "-f", container], check=True, stdout=subprocess.DEVNULL)
    return tempdir / "inventory"


def software_rows(inventory: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for apt_file in sorted(inventory.glob("*/apt.tsv")):
        rows.extend(tuple(line.split("\t", 1)) for line in apt_file.read_text().splitlines() if "\t" in line)
    for spack_file in sorted(inventory.glob("*/spack.json")):
        try:
            packages = json.loads(spack_file.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(packages, dict):
            packages = packages.get("specs", [])
        if not isinstance(packages, list):
            continue
        for package in packages:
            name = package.get("name", "unknown")
            version = package.get("version", "unknown")
            rows.append((f"spack:{name}", str(version)))
    return sorted(set(rows))


def render(image: str, tag: str, digest: str, inventory: Path) -> str:
    metadata = {}
    for metadata_file in sorted(inventory.glob("*/metadata.env")):
        metadata.update(read_metadata(metadata_file))
    lines = [
        f"# {image}:{tag}",
        "",
        f"- Image: `ghcr.io/ornl-mdf/containers/{image}:{tag}`",
        f"- Digest: `{digest}`",
        f"- Repository revision: `{metadata.get('repository_revision', 'not recorded')}`",
        "",
        "## Build Inputs",
        "",
    ]
    for key in sorted(key for key in metadata if key not in {"image", "repository_revision"}):
        lines.append(f"- {key.replace('_', ' ')}: `{metadata[key]}`")
    for lock_file in sorted(inventory.glob("*/spack.lock")):
        lock_digest = hashlib.sha256(lock_file.read_bytes()).hexdigest()
        lines.append(f"- {lock_file.parent.name} Spack lock SHA-256: `{lock_digest}`")
    rows = software_rows(inventory)
    lines.extend(["", "## Installed Software", "", "| Package | Version |", "| --- | --- |"])
    lines.extend(f"| `{name}` | `{version}` |" for name, version in rows)
    lines.append("")
    return "\n".join(lines)


def update_index(root: Path) -> None:
    entries = sorted(root.glob("*/*.md"))
    lines = ["# Container Software Inventory", "", "Generated from artifacts embedded in published images.", ""]
    for entry in entries:
        if entry.name == "README.md":
            continue
        lines.append(f"- [{entry.parent.name}:{entry.stem}]({entry.relative_to(root).as_posix()})")
    lines.append("")
    (root / "README.md").write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--output-root", type=Path, default=Path("docs/containers"))
    parser.add_argument("--inventory", type=Path)
    args = parser.parse_args()

    inventory = args.inventory or extract_inventory(f"ghcr.io/ornl-mdf/containers/{args.image}:{args.tag}")
    output_dir = args.output_root / args.image
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{args.tag}.md").write_text(render(args.image, args.tag, args.digest, inventory))
    update_index(args.output_root)
    if args.inventory is None:
        shutil.rmtree(inventory.parent)


if __name__ == "__main__":
    main()
