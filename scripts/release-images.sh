#!/usr/bin/env bash
# Build every release plan, test the complete set, then optionally publish it.
set -euo pipefail

publish=false
if [ "${1:-}" = "--publish" ]; then
  publish=true
  shift
fi
if [ "$#" -ne 0 ]; then
  echo "Usage: $0 [--publish]" >&2
  exit 2
fi

release_mode="${RELEASE_MODE:?RELEASE_MODE must be version or tracker}"
case "$release_mode" in
  version|tracker) ;;
  *) echo "Unknown release mode: ${release_mode}" >&2; exit 2 ;;
esac

additivefoam_ref="${ADDITIVEFOAM_REF:-b8f6d48c53555c303fa8186c895aee5712b6ea02}"
release_created="${RELEASE_CREATED:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
resolve_args=(python3 scripts/resolve_image_tags.py --mode "$release_mode" --additivefoam-ref "$additivefoam_ref")
for target in ${TARGETS:-}; do
  resolve_args+=(--target "$target")
done
plans="$("${resolve_args[@]}")"
echo "$plans"

# Do not expose a tag until every selected image has completed its smoke tests.
while IFS= read -r plan; do
  image="$(jq -r '.image' <<< "$plan")"
  tag="$(jq -r '.tag' <<< "$plan")"
  kind="$(jq -r '.kind' <<< "$plan")"
  build_args_file="$(mktemp)"
  jq -r '.build_args | to_entries[] | "\(.key)=\(.value)"' <<< "$plan" > "$build_args_file"

  build_cmd=(docker buildx bake "$image")
  while IFS='=' read -r key value; do
    [ -n "$key" ] || continue
    build_cmd+=(--set "${image}.args.${key}=${value}")
  done < "$build_args_file"
  rm -f "$build_args_file"

  export OUTPUT_TYPE=docker
  export PUSH=false
  export RELEASE_TAG="$tag"
  export RELEASE_CREATED="$release_created"
  export GIT_REVISION="${GIT_REVISION:?GIT_REVISION is required}"
  echo "Building ${image}:${tag} (${kind})"
  "${build_cmd[@]}"
  REGISTRY=ghcr.io/ornl-mdf/containers RELEASE_TAG="$tag" scripts/container-smoke-tests.sh "$image"
done < <(jq -c '.plans[]' <<< "$plans")

if [ "$publish" != true ]; then
  exit 0
fi

while IFS= read -r plan; do
  image="$(jq -r '.image' <<< "$plan")"
  tag="$(jq -r '.tag' <<< "$plan")"
  kind="$(jq -r '.kind' <<< "$plan")"
  base_tag="$(jq -r '.base_tag // empty' <<< "$plan")"
  lockfile="$(jq -r '.lockfile // empty' <<< "$plan")"
  reference="ghcr.io/ornl-mdf/containers/${image}:${tag}"
  docker image push "$reference"
  digest="sha256:$(docker buildx imagetools inspect "$reference" --raw | sha256sum | cut -d' ' -f1)"

  inventory_root="$RUNNER_TEMP/release-inventories/${image}"
  mkdir -p "${inventory_root}/${image}"
  container="$(docker create "$reference")"
  docker cp "${container}:/usr/share/ornl-mdf/inventory/${image}/." "${inventory_root}/${image}"
  docker rm -f "$container" >/dev/null

  base_args=()
  if [ -n "$base_tag" ]; then
    base_reference="ghcr.io/ornl-mdf/containers/ubuntu:${base_tag}"
    base_root="$RUNNER_TEMP/release-inventories/ubuntu-${base_tag}"
    mkdir -p "${base_root}/ubuntu"
    base_container="$(docker create "$base_reference")"
    docker cp "${base_container}:/usr/share/ornl-mdf/inventory/ubuntu/." "${base_root}/ubuntu"
    docker rm -f "$base_container" >/dev/null
    base_args=(--base-inventory "$base_root" --base-tag "$base_tag")
  fi

  python3 scripts/generate-container-docs.py --image "$image" --tag "$tag" --digest "$digest" \
    --inventory "$inventory_root" --output-root docs/containers "${base_args[@]}"
  if [ "$kind" = version ]; then
    snapshot_tag="${tag}-$(date -u +%Y%m%d)-${GIT_REVISION::7}"
  else
    snapshot_tag="${tag}-$(date -u +%Y-%m)"
  fi
  python3 scripts/generate-container-docs.py --image "$image" --tag "$snapshot_tag" \
    --published-tag "$tag" --digest "$digest" --inventory "$inventory_root" \
    --output-root docs/containers "${base_args[@]}"

  if [ -n "$lockfile" ] && [ -f "${inventory_root}/${image}/spack.lock" ]; then
    cp "${inventory_root}/${image}/spack.lock" "config/spack/${image}.lock"
  fi
done < <(jq -c '.plans[]' <<< "$plans")
