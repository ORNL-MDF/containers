# Testing

## Fast Local Checks

Run these after any change:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
docker buildx bake --print
git diff --check
```

The unit test validates Markdown catalog generation from a fixture inventory. The
Bake command validates target inheritance, build arguments, labels, and tags without
pulling or building images. `git diff --check` catches whitespace errors.

## Container Smoke Tests

After a successful local build, run the runtime smoke tests against all locally
loaded `unreleased` images:

```sh
scripts/container-smoke-tests.sh
```

Pass one or more target names to limit the test run, for example:

```sh
scripts/container-smoke-tests.sh exaca thesis
```

The script checks the non-root Ubuntu runtime environment, the AdditiveFOAM
tutorial completion marker, and the serial and MPI error paths of ExaCA and
3DThesis. It expects the solver programs to reject a missing input file; ExaCA
must also print its version banner. CI runs the same script against every
affected image after it builds and before a push can publish it.

## Inspect Resolved Tags

To quickly test which version and tracker tags the current configuration would
generate without building images, run:

```sh
python3 scripts/resolve_image_tags.py --mode version
python3 scripts/resolve_image_tags.py --mode tracker
```

Use `--target` to narrow the output to specific images. `--mode tracker-targets`
prints only the images that currently have tracker tags configured.

## Validate Release Inputs

Use `--print` with representative version-style inputs when modifying Bake variables,
Docker build arguments, or OCI labels:

```sh
RELEASE_TAG=mpich4.3.0-kokkos4.7.04 \
RELEASE_CREATED=2026-08-06T12:00:00Z \
GIT_REVISION=abc123 \
SPACK_UBUNTU_MANIFEST=ubuntu.yaml \
SPACK_UBUNTU_LOCK=ubuntu.lock \
SPACK_UBUNTU_NOBLE_IMAGE='spack/ubuntu-noble@sha256:c5286e543f226f2c36a6a5ae4c845bc1cd78fad9ece2704dd16256ae774a5d4f' \
OPENFOAM_IMAGE='openfoam/openfoam10-paraview510@sha256:d6ff1f9a2e7bc3c9177f373bebbdeb542fd8b49144afc24d5e3a3cd9bfae253d' \
ADDITIVEFOAM_REF=b8f6d48c53555c303fa8186c895aee5712b6ea02 \
docker buildx bake --print ubuntu additivefoam
```

Confirm the rendered output has the requested version tag and OCI `source`,
`version`, `revision`, and `created` labels. For solver tracker changes, also
validate representative manifest overrides, for example
`SPACK_EXACA_MANIFEST=exaca-main.yaml SPACK_EXACA_LOCK= docker buildx bake --print exaca`.
For AdditiveFOAM tracker changes, confirm the tracker plan overrides both the
AdditiveFOAM ref and the OpenFOAM base:

```sh
python3 scripts/resolve_image_tags.py --mode tracker --target additivefoam
```

## Change-Specific Coverage

| Change | Minimum validation |
| --- | --- |
| `scripts/` or `docs/` generation | Unit test and inspect generated Markdown fixture output. |
| `docker-bake.hcl` | Bake print with defaults and injected immutable inputs. |
| Dockerfile | Bake print; after a successful local build, run the relevant container smoke tests. CI runs them for every affected image. |
| `config/spack/<target>.yaml` | Verify its Bake target is selected; CI refreshes its lockfile and any dependent lockfiles. |
| `config/spack/base.yaml` or `images/ubuntu/` | Verify `ubuntu` and its Bake dependents are selected; shared-manifest changes also refresh their locks. |
| Workflow | Run the fast checks and review shell quoting, permissions, and push-only steps. |

## CI-Only Validation

GitHub Actions is the registry-dependent release test. On a `main` push it resolves
per-image version tags from repo inputs, builds affected images, smoke tests them,
pushes the resulting tags to GHCR, and commits updated inventory pages and refreshed
release lockfiles. On the monthly scheduled run it rebuilds configured tracker
manifests, republishes the moving tracker tags, and commits the updated tracker docs.
Validate the workflow log and resulting `docs/containers/` pages after such runs.

If DNS, registry authentication, or external network access is unavailable locally,
do not treat a failed full Docker build as a Dockerfile failure; report the limitation
and run the fast local checks instead.
