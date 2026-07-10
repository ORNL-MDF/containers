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

## Validate Release Inputs

Use `--print` with representative immutable inputs when modifying Bake variables,
Docker build arguments, or OCI labels:

```sh
RELEASE_DATE=2026-07-10 \
RELEASE_CREATED=2026-07-10T12:00:00Z \
GIT_REVISION=abc123 \
SPACK_UBUNTU_NOBLE_IMAGE='spack/ubuntu-noble@sha256:<digest>' \
OPENFOAM_IMAGE='openfoam/openfoam10-paraview510@sha256:<digest>' \
ADDITIVEFOAM_REF=<commit> \
docker buildx bake --print ubuntu additivefoam
```

Confirm the rendered output has date-only tags and OCI `source`, `version`,
`revision`, and `created` labels. Do not substitute a real published date and push
from a local machine.

## Change-Specific Coverage

| Change | Minimum validation |
| --- | --- |
| `scripts/` or `docs/` generation | Unit test and inspect generated Markdown fixture output. |
| `docker-bake.hcl` | Bake print with defaults and injected immutable inputs. |
| Dockerfile | Bake print; use CI for a real build when external images are required. |
| `config/spack/exaca.yaml` | Verify `exaca` is selected; CI refreshes `exaca.lock`. |
| `config/spack/thesis.yaml` | Verify `thesis` is selected; CI refreshes `thesis.lock`. |
| `config/spack/base.yaml` or `images/ubuntu/` | Verify `ubuntu`, `exaca`, and `thesis` are selected. |
| Workflow | Run the fast checks and review shell quoting, permissions, and push-only steps. |

## CI-Only Validation

GitHub Actions is the release test for registry-dependent behavior. On a `main` push
it resolves external image digests and AdditiveFOAM's commit, rejects an existing
same-day tag, publishes affected images, extracts embedded inventory from stopped
containers, and commits catalog pages and new Spack locks. Validate the workflow log
and resulting `docs/containers/` pages after such a release.

If DNS, registry authentication, or external network access is unavailable locally,
do not treat a failed full Docker build as a Dockerfile failure; report the limitation
and run the fast local checks instead.
