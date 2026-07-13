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
    ubuntu.yaml
    exaca.yaml
    ...
docker-bake.hcl
```

Each image has its own directory, while shared Spack environment definitions
live under `config/spack`. `docker-bake.hcl` is the single source of truth for
local builds and CI.

## Image Layout

```text
spack/ubuntu-noble@sha256:<digest> -> ghcr.io/ornl-mdf/containers/ubuntu:<release-tag>
openfoam/openfoam10-paraview510@sha256:<digest> + AdditiveFOAM commit -> ghcr.io/ornl-mdf/containers/additivefoam:<release-tag>
ubuntu target/image -> exaca target
ubuntu target/image -> thesis target
```

`ubuntu:<release-tag>` is the repo-owned Spack base image. It contains the shared
GCC, MPICH, and Kokkos toolchain used by the solver images, together with their
Spack activation. ExaCA and Thesis reuse this installed store and add only their
solver-specific packages. This is intended to be the base image for other
Spack-derived containers; use a different base only when a software environment
has a specific compatibility constraint.

`exaca:<release-tag>` and `thesis:<release-tag>` reuse the `ubuntu` container as their build base.

`additivefoam:<release-tag>` repackages the OpenFOAM Foundation v10 image and layers
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

Published tags are immutable UTC release identifiers. The first daily batch uses
`YYYY-MM-DD`; CI assigns later same-day batches `YYYY-MM-DD-<suffix>`, progressing
from `a` through `z`, then `aa`. The exact installed package versions, base-image
digest, and source revisions for each tag are listed in
[`docs/containers/`](docs/containers/README.md), so no container needs to be started
to inspect its software.

A date-based tag is a completed public release only after it appears in that catalog.
CI first stages verified images in a private GHCR package, then promotes their exact
digests to public tags and commits the catalog and generated Spack locks. A failed
release is resumed only from that same private candidate; CI never rebuilds a
different image under an allocated public tag.
The `ghcr.io/ornl-mdf/containers-staging/<image>` packages must remain private and
grant the repository workflow package write/delete access.

Local builds default to `unreleased`:

```text
ubuntu:unreleased
additivefoam:unreleased
exaca:unreleased
thesis:unreleased
```

After a successful build, smoke test the locally loaded images:

```sh
scripts/container-smoke-tests.sh
```

To smoke test only the solver images, pass their target names:

```sh
scripts/container-smoke-tests.sh exaca thesis
```

The same tests run in CI for every affected image before it can be published.

Override them individually when needed:

```sh
REGISTRY=ghcr.io/ornl-mdf/containers \
RELEASE_TAG="$(date -u +%F)" \
docker buildx bake
```

The deafult user for the containers is `mdf`. If a debugging session requires
root inside a container, override the runtime user explicitly:

```sh
docker run --user root -it ghcr.io/ornl-mdf/containers/ubuntu:<release-tag> /bin/bash
```

To generate a local-only copy of the container documentation after building
local unreleased images with the default Bake settings, run:

```sh
mkdir -p logs/container-docs

for image in ubuntu additivefoam exaca thesis; do
  ref="ghcr.io/ornl-mdf/containers/${image}:unreleased"
  digest="$(docker image inspect --format '{{.Id}}' "$ref")"

  base_args=()
  if [ "$image" = exaca ] || [ "$image" = thesis ]; then
    base_args=(--base-image "ghcr.io/ornl-mdf/containers/ubuntu:unreleased")
  fi
  python3 scripts/generate-container-docs.py \
    --image "$image" \
    --tag unreleased \
    --digest "$digest" \
    --output-root logs/container-docs \
    "${base_args[@]}"
done
```

ExaCA and Thesis pages link to the matching Ubuntu page for shared package names
and versions; their Installed Software tables list only software added or changed
by the solver image.

## CI Rebuild Policy

CI discovers packages from public Bake targets whose Dockerfile is
`images/<target>/Dockerfile`. It rebuilds the changed target and every target that
depends on it through a Bake `target:` context. `config/spack/<target>.yaml` changes
rebuild that target and refresh its generated lockfile; `config/spack/base.yaml`
rebuilds `ubuntu` and its dependents. Changes to `docker-bake.hcl` or `.dockerignore`
rebuild every discovered package.

The Ubuntu Spack manifest is the shared toolchain contract. Changing
`config/spack/ubuntu.yaml` rebuilds `ubuntu`, refreshes its lockfile, and rebuilds
all of its dependent solver images and lockfiles. Changes to the shared
`config/spack/base.yaml` receive the same treatment.

`config/spack/ubuntu.lock` is a build input when present, just like the solver
lockfiles. CI removes it only when the shared environment manifests require a new
concrete solution.
