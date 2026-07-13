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

## Validate Release Inputs

Use `--print` with representative immutable inputs when modifying Bake variables,
Docker build arguments, or OCI labels:

```sh
RELEASE_TAG=2026-07-10 \
RELEASE_CREATED=2026-07-10T12:00:00Z \
RELEASE_CANDIDATE=candidate-2026-07-10-123-1 \
GIT_REVISION=abc123 \
SPACK_UBUNTU_NOBLE_IMAGE='spack/ubuntu-noble@sha256:c5286e543f226f2c36a6a5ae4c845bc1cd78fad9ece2704dd16256ae774a5d4f' \
OPENFOAM_IMAGE='openfoam/openfoam10-paraview510@sha256:d6ff1f9a2e7bc3c9177f373bebbdeb542fd8b49144afc24d5e3a3cd9bfae253d' \
ADDITIVEFOAM_REF=b8f6d48c53555c303fa8186c895aee5712b6ea02 \
docker buildx bake --print ubuntu additivefoam
```

Confirm the rendered output has a date tag, optionally followed by an alphabetic suffix,
and OCI `source`, `version`, `revision`, `created`, and candidate labels. Do not
substitute a real published date and push from a local machine.

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

GitHub Actions is the release test for registry-dependent behavior. On a `main` push
it uses the pinned external inputs, assigns the next immutable UTC release tag,
preflights embedded inventory before publication, stages candidates in the private
`ghcr.io/ornl-mdf/containers-staging` package, promotes verified digests, and commits
catalog pages and new Spack locks. The catalog commit marks release completion.
Validate the workflow log and resulting `docs/containers/` pages after such a release.
Before the first run, provision `ghcr.io/ornl-mdf/containers-staging/<image>` as a
private package namespace and grant this repository's workflow token package
write/delete access.

If DNS, registry authentication, or external network access is unavailable locally,
do not treat a failed full Docker build as a Dockerfile failure; report the limitation
and run the fast local checks instead.
