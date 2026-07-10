# Containers for ORNL-MDF Myna workflows

This repository builds Docker images primarily intended for use with Myna workflows and
other workflows that require containerized ORNL-MDF simulation tools.

> [!NOTE]
> Myna itself is expected to be installed in CI or user environments with `uv` or
> other Python package managers, so it does not have a dedicated container here.

## Repository Layout

```text
images/
  <container_name>/
    Dockerfile
  ...
config/
  spack/
    base.yaml
    exaca.yaml
    ...
docker-bake.hcl
```

Each image has its own directory, while shared Spack environment definitions
live under `config/spack`. `docker-bake.hcl` is the single source of truth for
local builds and CI.

## Image Layout

```text
spack/ubuntu-noble:develop -> ghcr.io/ornl-mdf/containers/ubuntu:develop
openfoam/openfoam10-paraview510 + AdditiveFOAM 1.2.0 -> ghcr.io/ornl-mdf/containers/additivefoam:1.2.0
ubuntu target/image -> exaca target
ubuntu target/image -> thesis target
```

`ubuntu:<YYYY-MM-DD>` is the repo-owned base image with apt packages and shared Spack
activation. This is intended to the base image for other containers and different
base images for software should only be used if there a specific environment constraint.

`exaca:<YYYY-MM-DD>` and `thesis:<YYYY-MM-DD>` reuse the `ubuntu` container as their build base.

`additivefoam:<YYYY-MM-DD>` repackages the OpenFOAM Foundation v10 image and layers
AdditiveFOAM 1.2.0 on top of it.

All repo-owned images default to the non-root `mdf` runtime user. Build steps
that need elevated privileges still run as `root` inside the Dockerfile, but
interactive shells and normal container commands start as `mdf`.
They start in `/workspace`, which is owned by `mdf`.

## Building Locally

Build all images and load them into the local Docker daemon:

```sh
mkdir -p logs
for target in ubuntu additivefoam exaca thesis; do
  docker buildx bake "$target" 2>&1 | tee "logs/${target}.log"
done
```

When buildign a single target buildx resolves additional context needed to a build a target from
definitions in `docker-bake.hcl`. Run one target and write its log:

```sh
mkdir -p logs
docker buildx bake additivefoam 2>&1 | tee logs/additivefoam.log
```

Override the published namespace or tag:

```sh
mkdir -p logs
for target in ubuntu additivefoam exaca thesis; do
  REGISTRY=ghcr.io/ornl-mdf/containers \
    docker buildx bake "$target" 2>&1 | tee "logs/${target}.log"
done
```

`docker-bake.hcl` defaults to `type=docker`, so successful local builds are
loaded directly into the local Docker image store.

Published tags are immutable UTC release dates. The exact installed package versions,
base-image digest, and source revisions for each tag are listed in
[`docs/containers/`](docs/containers/README.md), so no container needs to be started
to inspect its software.

Local builds default to `unreleased`:

```text
ubuntu:unreleased
additivefoam:unreleased
exaca:unreleased
thesis:unreleased
```

Override them individually when needed:

```sh
REGISTRY=ghcr.io/ornl-mdf/containers \
RELEASE_DATE="$(date -u +%F)" \
docker buildx bake
```

The deafult user for the containers is `mdf`. If a debugging session requires
root inside a container, override the runtime user explicitly:

```sh
docker run --user root -it ghcr.io/ornl-mdf/containers/ubuntu:<YYYY-MM-DD> /bin/bash
```

To generate a local-only copy of the container documentation after building
local unreleased images with the default Bake settings, run:

```sh
mkdir -p logs/container-docs

for image in ubuntu additivefoam exaca thesis; do
  ref="ghcr.io/ornl-mdf/containers/${image}:unreleased"
  digest="$(docker image inspect --format '{{.Id}}' "$ref")"

  python3 scripts/generate-container-docs.py \
    --image "$image" \
    --tag unreleased \
    --digest "$digest" \
    --output-root logs/container-docs
done
```

## CI Rebuild Policy

CI rebuilds only affected targets. Changes under `images/ubuntu/`,
`config/spack/base.yaml`, or `docker-bake.hcl` rebuild `ubuntu`, `exaca`, and
`thesis`. Changes under a solver image directory rebuild only that image unless
it depends on `ubuntu`.
