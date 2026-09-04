#!/usr/bin/env bash
# Exercise the essential runtime interfaces of images built by docker-bake.hcl.
set -euo pipefail

registry="${REGISTRY:-ghcr.io/ornl-mdf/containers}"
release_tag="${RELEASE_TAG:-unreleased}"

if [ "$#" -eq 0 ]; then
  set -- ubuntu additivefoam exaca thesis
fi

image_ref() {
  printf '%s/%s:%s' "$registry" "$1" "$release_tag"
}

expect_failure() {
  local description="$1"
  shift
  local output status

  set +e
  output="$("$@" 2>&1)"
  status=$?
  set -e
  printf '%s\n' "$output"
  if [ "$status" -eq 0 ]; then
    echo "Expected ${description} to fail without an input file" >&2
    return 1
  fi
  printf '%s' "$output"
}

for target in "$@"; do
  image="$(image_ref "$target")"
  echo "Smoke testing ${image}"

  case "$target" in
    ubuntu)
      docker run --rm "$image" /bin/bash -lc \
        'test "$(id -un)" = mdf && test "$PWD" = /workspace && test -f /usr/share/ornl-mdf/inventory/ubuntu/metadata.env'
      ;;
    additivefoam)
      docker run --rm "$image" /bin/bash -lc \
        'command -v checkMesh >/dev/null && cd /opt/AdditiveFOAM/tutorials/AMB2018-02-B && test "$(tail -n 1 log.additiveFoam)" = "Finalising parallel run"'
      ;;
    exaca)
      output="$(expect_failure 'ExaCA serial invocation' docker run --rm "$image" ExaCA)"
      case "$output" in
        *"ExaCA version:"*) ;;
        *) echo 'ExaCA did not print its version banner' >&2; exit 1 ;;
      esac
      output="$(expect_failure 'ExaCA MPI invocation' docker run --rm "$image" mpirun -n 2 ExaCA)"
      case "$output" in
        *"ExaCA version:"*) ;;
        *) echo 'ExaCA MPI invocation did not print its version banner' >&2; exit 1 ;;
      esac
      ;;
    thesis)
      expect_failure '3DThesis serial invocation' docker run --rm "$image" 3DThesis >/dev/null
      expect_failure '3DThesis MPI invocation' docker run --rm "$image" mpirun -n 2 3DThesis >/dev/null
      ;;
    *)
      echo "Unknown smoke-test target: ${target}" >&2
      exit 2
      ;;
  esac
done
