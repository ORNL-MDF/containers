# Containers for ORNL-MDF Myna workflows

This repository builds Docker images primarily intended for use with Myna workflows and
other workflows that require containerized ORNL-MDF simulation tools.

> [!NOTE]
> Myna itself is expected to be installed in CI or user environments with `uv` or
> other Python package managers, so it does not have a dedicated container here.

## Repository Layout

Each image has its own directory in `images`, as well as some configuration options within `config`:

- Shared Spack environment definitions that are used by some of the images live under [`config/spack`](config/spack)
- Images not using spack are currently defined in their Dockerfile, but if another shared build system is introduced then it should live in a separate directory within `config/`
- Published tag derivation and tracker manifests are declared in [`config/image-tags.json`](config/image-tags.json). CI is set to check and publish any changes to the tracked branches (e.g., `main`) monthly.

The Docker bake file, `docker-bake.hcl`, is intended to be the single source of truth for local builds and CI.

## Image Layout

`ubuntu:<version-tag>` is the repo-owned Spack base image. It contains the shared
GCC, MPICH, and Kokkos toolchain used by the solver images, together with their
Spack activation. ExaCA and Thesis reuse this installed store and add only their
solver-specific packages. This is intended to be the base image for other
Spack-derived containers; use a different base only when a software environment
has a specific compatibility constraint. 

Spack-based installations, e.g., `exaca:<version-tag>` and `thesis:<version-tag>`,
reuse the `ubuntu` container as their build base, which speeds container build time
and provides common dependencies. As of now, this base is somewhat arbitrary--
it is not optimized for performance for any one code.

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

The default user for the containers is `mdf`. If a debugging session requires
root inside a container, override the runtime user explicitly:

```sh
docker run --user root -it ghcr.io/ornl-mdf/containers/ubuntu:<version-tag> /bin/bash
```

### Tagging and Local Testing of Containers

Published tags are derived from repo inputs:

- Base Spack images: normalized Spack spec versions such as `mpich4.3.0-kokkos4.7.04`
- Spack-based containers: Spack solver version such as `2.0.1` deriving from `exaca@2.0.1`
- Non-Spack containers: normalized upstream release tag such as `1.1.0` from AdditiveFOAM tag `1.1.0`
- Currently, there are no non-Spack shared base images, so there is no explicit policy for those tags.

These public tags are convenience locators and may move when CI rebuilds a changed
image from `main`. Workflows that require fixed behavior should pin the image digest,
for example `ghcr.io/ornl-mdf/containers/exaca@sha256:<digest>`.

When configured in `config/image-tags.json`, CI also publishes moving tracker tags
such as `main` from explicit manifests like `config/spack/exaca-main.yaml`. Those
tracker tags are rebuilt monthly if there are changes on the tracked branch,
and the same digest-pinning guidance applies.

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

Local builds default to `unreleased`.

After a successful build, smoke test the locally loaded images:

```sh
scripts/container-smoke-tests.sh
```

To smoke test only the solver images, pass their target names:

```sh
scripts/container-smoke-tests.sh exaca thesis
```

### Container Documentation and Local Testing of Auto-document Generation

The exact installed package versions, base-image digests, source revisions, and
published digests are listed in [`docs/containers/`](docs/containers/README.md),
so no container needs to be started to inspect its software. This is intended to
be a convenience tool for when newer versions of containers are published and older
versions lose the public convenience tags with version information--users should
ultimately inspect packages themselves to confirm container software meets
and requirements they have.

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

## Continuous Integration (CI)

The same build and smoke tests run in CI for every affected image before a PR can be merged into
`main`. This is intended to ensure that containers build successfully on the GitHub runners before
they are published. The actual publishing does not happen until the PR is merged into main.
Package publishing and generated-record commits run only for trusted `main`
pushes and scheduled runs.

### CI Rebuild Policy

CI discovers packages from public Bake targets whose Dockerfile is
`images/<target>/Dockerfile`. It rebuilds the changed target and every target that
depends on it through a Bake `target:` context. `config/spack/<target>.yaml` changes
rebuild that target and refresh its generated lockfile; `config/spack/base.yaml`
rebuilds `ubuntu` and its dependents. Changes to `docker-bake.hcl` or `.dockerignore`
rebuild every discovered package. Tracker manifest changes such as
`config/spack/exaca-main.yaml` rebuild the matching image without refreshing the
release lockfile.

Images using base containers defined in this repo, such as the `ubuntu` container manifest,
have a shared toolchain contract with dependent containers. For example, changing
`config/spack/ubuntu.yaml` rebuilds `ubuntu`, refreshes its lockfile, and rebuilds
all of its dependent solver images and lockfiles. Changes to the shared
`config/spack/base.yaml` receive the same treatment.

`config/spack/ubuntu.lock` is a build input when present, just like the solver
lockfiles. CI removes it only when the shared environment manifests require a new
concrete solution. Monthly tracker rebuilds do not overwrite these release lockfiles.
