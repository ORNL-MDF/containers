#!/usr/bin/env python3
"""Resolve published tags and build overrides for repository images."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "image-tags.json"
DEFAULT_ADDITIVEFOAM_REF = "b8f6d48c53555c303fa8186c895aee5712b6ea02"
SPEC_PATTERN = re.compile(r"^(?P<name>[\w-]+)@(?P<version>[^\s+^]+)")
TAG_SANITIZE_PATTERN = re.compile(r"[^a-z0-9._-]+")


@dataclass(frozen=True)
class BuildPlan:
    image: str
    tag: str
    kind: str
    build_args: dict[str, str]
    manifest: str | None = None
    base_tag: str | None = None
    lockfile: str | None = None


def load_config(path: Path = CONFIG_PATH) -> dict[str, object]:
    return json.loads(path.read_text())


def normalize_tag(value: str) -> str:
    normalized = TAG_SANITIZE_PATTERN.sub("-", value.strip().lower()).strip("._-")
    if not normalized:
        raise ValueError(f"could not normalize tag from {value!r}")
    return normalized


def normalize_release_tag(value: str) -> str:
    normalized = normalize_tag(value)
    if normalized.startswith("v") and len(normalized) > 1 and normalized[1].isdigit():
        return normalized[1:]
    return normalized


def spec_lines(manifest_path: Path) -> list[str]:
    specs: list[str] = []
    in_specs = False
    for raw_line in manifest_path.read_text().splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped == "specs:":
            in_specs = True
            continue
        if not in_specs:
            continue
        if not stripped:
            continue
        if raw_line.startswith("  - ") or raw_line.startswith("- "):
            specs.append(stripped[2:].strip())
            continue
        if not raw_line.startswith(" "):
            break
    if not specs:
        raise ValueError(f"manifest {manifest_path} does not define any top-level specs")
    return specs


def parse_versioned_spec(spec: str) -> tuple[str, str]:
    match = SPEC_PATTERN.match(spec)
    if not match:
        raise ValueError(f"could not parse top-level spec {spec!r}")
    return match.group("name"), match.group("version")


def spack_top_spec_tag(manifest: str) -> str:
    _, version = parse_versioned_spec(spec_lines(ROOT / manifest)[0])
    return normalize_tag(version)


def spack_composite_tag(manifest: str) -> str:
    parts = []
    for spec in spec_lines(ROOT / manifest):
        name, version = parse_versioned_spec(spec)
        parts.append(normalize_tag(f"{name}{version}"))
    return "-".join(parts)


def additivefoam_repo_describe(remote: str, ref: str, *describe_args: str) -> str:
    tempdir = Path(tempfile.mkdtemp(prefix="additivefoam-describe-"))
    try:
        subprocess.run(
            ["git", "clone", "--filter=blob:none", "--quiet", remote, str(tempdir)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["git", "-C", str(tempdir), "checkout", "--detach", ref],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        describe = subprocess.check_output(
            ["git", "-C", str(tempdir), "describe", *describe_args],
            text=True,
        ).strip()
        return describe
    finally:
        shutil.rmtree(tempdir)


def additivefoam_release_tag(remote: str, ref: str) -> str:
    release_tag = additivefoam_repo_describe(remote, ref, "--tags", "--abbrev=0")
    return normalize_release_tag(release_tag)


def version_tag(image: str, config: dict[str, object], additivefoam_ref: str) -> str:
    image_config = config["images"][image]
    source = image_config["version_source"]
    source_type = source["type"]
    if source_type == "spack-top-spec":
        return spack_top_spec_tag(source["manifest"])
    if source_type == "spack-composite":
        return spack_composite_tag(source["manifest"])
    if source_type == "git-release-tag":
        return additivefoam_release_tag(source["remote"], additivefoam_ref)
    raise ValueError(f"unknown version source type {source_type!r} for {image}")


def base_tag_for(image: str, config: dict[str, object], additivefoam_ref: str) -> str | None:
    if image in {"exaca", "thesis"}:
        return version_tag("ubuntu", config, additivefoam_ref)
    return None


def build_args_for(
    image: str,
    config: dict[str, object],
    tracker_tag: str | None,
) -> tuple[dict[str, str], str | None, str | None]:
    image_config = config["images"][image]
    build = image_config.get("build")
    if not isinstance(build, dict):
        if tracker_tag is None:
            return {}, None, None
        trackers = {tracker["tag"]: tracker for tracker in image_config.get("trackers", [])}
        tracker = trackers[tracker_tag]
        return dict(tracker.get("build_args", {})), None, None

    manifest_value = build["manifest_value"]
    lock_value = build.get("lock_value")
    extra_args: dict[str, str] = {}
    if tracker_tag is not None:
        trackers = {tracker["tag"]: tracker for tracker in image_config.get("trackers", [])}
        tracker = trackers[tracker_tag]
        manifest_value = tracker["manifest_value"]
        lock_value = tracker.get("lock_value", "")
        extra_args = dict(tracker.get("build_args", {}))

    args = {build["manifest_arg"]: manifest_value, build["lock_arg"]: lock_value or "", **extra_args}
    manifest_name = manifest_value
    lockfile_name = lock_value or None
    return args, manifest_name, lockfile_name


def resolve_version_plans(
    targets: list[str],
    config: dict[str, object],
    additivefoam_ref: str,
) -> list[BuildPlan]:
    plans: list[BuildPlan] = []
    for image in targets:
        tag = version_tag(image, config, additivefoam_ref)
        build_args, manifest_name, lockfile_name = build_args_for(image, config, None)
        plans.append(
            BuildPlan(
                image=image,
                tag=tag,
                kind="version",
                build_args=build_args,
                manifest=manifest_name,
                base_tag=base_tag_for(image, config, additivefoam_ref),
                lockfile=lockfile_name,
            )
        )
    return plans


def resolve_tracker_plans(
    targets: list[str] | None,
    config: dict[str, object],
    additivefoam_ref: str,
) -> list[BuildPlan]:
    allowed = set(targets or config["images"])
    plans: list[BuildPlan] = []
    for image, image_config in sorted(config["images"].items()):
        if image not in allowed:
            continue
        for tracker in image_config.get("trackers", []):
            build_args, manifest_name, lockfile_name = build_args_for(image, config, tracker["tag"])
            plans.append(
                BuildPlan(
                    image=image,
                    tag=normalize_tag(tracker["tag"]),
                    kind="tracker",
                    build_args=build_args,
                    manifest=manifest_name,
                    base_tag=base_tag_for(image, config, additivefoam_ref),
                    lockfile=lockfile_name,
                )
            )
    return plans


def tracker_targets(config: dict[str, object]) -> list[str]:
    return sorted(image for image, image_config in config["images"].items() if image_config.get("trackers"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("version", "tracker", "tracker-targets"), required=True)
    parser.add_argument("--target", action="append")
    parser.add_argument("--additivefoam-ref", default=DEFAULT_ADDITIVEFOAM_REF)
    args = parser.parse_args()

    config = load_config()
    if args.mode == "tracker-targets":
        print(json.dumps({"targets": tracker_targets(config)}, sort_keys=True))
        return

    targets = args.target or sorted(config["images"])
    if args.mode == "version":
        plans = resolve_version_plans(targets, config, args.additivefoam_ref)
    else:
        plans = resolve_tracker_plans(targets, config, args.additivefoam_ref)
    print(
        json.dumps(
            {
                "plans": [
                    {
                        "base_tag": plan.base_tag,
                        "build_args": plan.build_args,
                        "image": plan.image,
                        "kind": plan.kind,
                        "lockfile": plan.lockfile,
                        "manifest": plan.manifest,
                        "tag": plan.tag,
                    }
                    for plan in plans
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
