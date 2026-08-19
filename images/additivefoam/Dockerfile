ARG OPENFOAM_IMAGE=openfoam/openfoam10-paraview510@sha256:d6ff1f9a2e7bc3c9177f373bebbdeb542fd8b49144afc24d5e3a3cd9bfae253d
FROM ${OPENFOAM_IMAGE}
ARG OPENFOAM_IMAGE
ARG ADDITIVEFOAM_REF=b8f6d48c53555c303fa8186c895aee5712b6ea02
ARG GIT_REVISION=local
ARG RELEASE_TAG=unreleased

ENV MDF_USER=mdf
ENV MDF_UID=1000
ENV MDF_GID=1000
ENV MDF_WORKDIR=/workspace

USER root

SHELL ["/bin/bash", "-lc"]

ENV ADDITIVEFOAM_DIR=/opt/AdditiveFOAM

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends git; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*; \
    git init "${ADDITIVEFOAM_DIR}"; \
    git -C "${ADDITIVEFOAM_DIR}" remote add origin https://github.com/ORNL/AdditiveFOAM.git; \
    git -C "${ADDITIVEFOAM_DIR}" fetch origin "${ADDITIVEFOAM_REF}"; \
    git -C "${ADDITIVEFOAM_DIR}" fetch --tags origin; \
    git -C "${ADDITIVEFOAM_DIR}" checkout --detach FETCH_HEAD; \
    additivefoam_revision="$(git -C "${ADDITIVEFOAM_DIR}" rev-parse HEAD)"; \
    additivefoam_version="$(git -C "${ADDITIVEFOAM_DIR}" describe --tags --abbrev=0)"; \
    for candidate in /opt/openfoam10/etc/bashrc /usr/lib/openfoam/openfoam10/etc/bashrc /usr/lib/openfoam/openfoam*/etc/bashrc; do \
      if [ -f "$candidate" ]; then \
        set +u; \
        . "$candidate" || true; \
        set -u; \
        break; \
      fi; \
    done; \
    cd "${ADDITIVEFOAM_DIR}"; \
    ./Allwmake; \
    rm -rf "${ADDITIVEFOAM_DIR}/.git"; \
    if ! getent group "${MDF_USER}" >/dev/null; then \
      if getent group "${MDF_GID}" >/dev/null; then \
        groupadd "${MDF_USER}"; \
      else \
        groupadd --gid "${MDF_GID}" "${MDF_USER}"; \
      fi; \
    fi; \
    if ! id -u "${MDF_USER}" >/dev/null 2>&1; then \
      if getent passwd "${MDF_UID}" >/dev/null; then \
        useradd --create-home --gid "${MDF_USER}" --shell /bin/bash "${MDF_USER}"; \
      else \
        useradd --create-home --uid "${MDF_UID}" --gid "${MDF_USER}" --shell /bin/bash "${MDF_USER}"; \
      fi; \
    fi; \
    home_dir="$(getent passwd "${MDF_USER}" | cut -d: -f6)"; \
    if [ -z "${home_dir}" ]; then \
      echo "Unable to resolve home directory for ${MDF_USER}" >&2; \
      exit 1; \
    fi; \
    mkdir -p "${home_dir}" "${MDF_WORKDIR}"; \
    chown -R "${MDF_USER}:${MDF_USER}" "${ADDITIVEFOAM_DIR}" "${home_dir}" "${MDF_WORKDIR}"; \
    mkdir -p /usr/share/ornl-mdf/inventory/additivefoam; \
    { \
      echo "image=additivefoam"; \
      echo "base_image=${OPENFOAM_IMAGE}"; \
      echo "additivefoam_version=${additivefoam_version}"; \
      echo "additivefoam_revision=${additivefoam_revision}"; \
      echo "additivefoam_source_ref=${ADDITIVEFOAM_REF}"; \
      echo "release_tag=${RELEASE_TAG}"; \
      echo "repository_revision=${GIT_REVISION}"; \
    } > /usr/share/ornl-mdf/inventory/additivefoam/metadata.env; \
    dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort > /usr/share/ornl-mdf/inventory/additivefoam/apt.tsv

USER mdf
WORKDIR /workspace
