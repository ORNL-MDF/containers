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
local builds and CI. Published tag derivation and tracker manifests are declared
in [`config/image-tags.json`](config/image-tags.json).

## Image Layout

```text
spack/ubuntu-noble@sha256:<digest> -> ghcr.io/ornl-mdf/containers/ubuntu:<version-tag>
openfoam/openfoam10-paraview510@sha256:<digest> + AdditiveFOAM commit -> ghcr.io/ornl-mdf/containers/additivefoam:<version-tag>
ubuntu target/image -> exaca target
ubuntu target/image -> thesis target
optional tracker manifests -> moving tags such as exaca:main
```

`ubuntu:<version-tag>` is the repo-owned Spack base image. It contains the shared
GCC, MPICH, and Kokkos toolchain used by the solver images, together with their
Spack activation. ExaCA and Thesis reuse this installed store and add only their
solver-specific packages. This is intended to be the base image for other
Spack-derived containers; use a different base only when a software environment
has a specific compatibility constraint.

`exaca:<version-tag>` and `thesis:<version-tag>` reuse the `ubuntu` container as their build base.

`additivefoam:<version-tag>` repackages the OpenFOAM Foundation v10 image and layers
an upstream AdditiveFOAM release such as `1.2.0` on top of it. CI also publishes
`additivefoam:main` as a moving monthly tracker using an OpenFOAM 14 base.

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

When building a single target buildx resolves additional context needed to build a target from
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

Published tags are derived from repo inputs instead of calendar dates:

- `ubuntu`: normalized top-level Spack spec versions such as `mpich4.3.0-kokkos4.7.04`
- `exaca` and `thesis`: top-level solver version such as `2.0.1`
- `additivefoam`: normalized upstream release tag such as `1.1.0`

These public tags are convenience locators and may move when CI rebuilds a changed
image from `main`. Workflows that require fixed behavior should pin the image digest,
for example `ghcr.io/ornl-mdf/containers/exaca@sha256:<digest>`.

The exact installed package versions, base-image digests, source revisions, and
published digests are listed in [`docs/containers/`](docs/containers/README.md),
so no container needs to be started to inspect its software.

When configured in `config/image-tags.json`, CI also publishes moving tracker tags
such as `main` from explicit manifests like `config/spack/exaca-main.yaml`. Those
tracker tags are rebuilt monthly, and the same digest-pinning guidance applies.

To inspect the tags that the current repo state would publish without building any
images, run:

```sh
python3 scripts/resolve_image_tags.py --mode version
python3 scripts/resolve_image_tags.py --mode tracker
```

Limit the output to specific images when needed:

```sh
python3 scripts/resolve_image_tags.py --mode version --target ubuntu --target additivefoam
python3 scripts/resolve_image_tags.py --mode tracker --target additivefoam --target exaca
python3 scripts/resolve_image_tags.py --mode tracker-targets
```

The Spack-derived images resolve entirely from repo state. `additivefoam` also
consults the upstream AdditiveFOAM repository to determine the current release tag,
so that lookup is slower and requires network access.

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
RELEASE_TAG=2.0.1 \
docker buildx bake
```

The default user for the containers is `mdf`. If a debugging session requires
root inside a container, override the runtime user explicitly:

```sh
docker run --user root -it ghcr.io/ornl-mdf/containers/ubuntu:<version-tag> /bin/bash
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
rebuild every discovered package. Tracker manifest changes such as
`config/spack/exaca-main.yaml` rebuild the matching image without refreshing the
release lockfile.

The Ubuntu Spack manifest is the shared toolchain contract. Changing
`config/spack/ubuntu.yaml` rebuilds `ubuntu`, refreshes its lockfile, and rebuilds
all of its dependent solver images and lockfiles. Changes to the shared
`config/spack/base.yaml` receive the same treatment.

`config/spack/ubuntu.lock` is a build input when present, just like the solver
lockfiles. CI removes it only when the shared environment manifests require a new
concrete solution. Monthly tracker rebuilds do not overwrite these release lockfiles.

CI completes every selected image build and smoke test before it pushes any image
tag. Pull-request builds use read-only repository credentials; package publishing
and generated-record commits run only for trusted `main` pushes and scheduled runs.
