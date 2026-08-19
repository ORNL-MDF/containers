# Repository-owned Ubuntu Noble base for ORNL-MDF workflow images.
ARG SPACK_UBUNTU_NOBLE_IMAGE=spack/ubuntu-noble@sha256:c5286e543f226f2c36a6a5ae4c845bc1cd78fad9ece2704dd16256ae774a5d4f
FROM ${SPACK_UBUNTU_NOBLE_IMAGE}
ARG SPACK_UBUNTU_NOBLE_IMAGE
ARG GIT_REVISION=local
ARG RELEASE_TAG=unreleased
ARG SPACK_UBUNTU_MANIFEST=ubuntu.yaml
ARG SPACK_UBUNTU_LOCK=ubuntu.lock

ENV MDF_USER=mdf
ENV MDF_UID=1000
ENV MDF_GID=1000
ENV MDF_WORKDIR=/workspace
ENV MAKEFLAGS=

COPY config/spack/ /tmp/spack-config/

RUN apt-get update \
&&  apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    file \
&&  apt-get clean \
&&  rm -rf /var/lib/apt/lists/*

RUN set -eux; \
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
    mkdir -p /opt/software /opt/views "${MDF_WORKDIR}"; \
    home_dir="$(getent passwd "${MDF_USER}" | cut -d: -f6)"; \
    if [ -z "${home_dir}" ]; then \
      echo "Unable to resolve home directory for ${MDF_USER}" >&2; \
      exit 1; \
    fi; \
    mkdir -p "${home_dir}"; \
    cp /tmp/spack-config/base.yaml /opt/spack-environment/base.yaml; \
    cp "/tmp/spack-config/${SPACK_UBUNTU_MANIFEST}" /opt/spack-environment/spack.yaml; \
    if [ -n "${SPACK_UBUNTU_LOCK}" ] && [ -f "/tmp/spack-config/${SPACK_UBUNTU_LOCK}" ]; then cp "/tmp/spack-config/${SPACK_UBUNTU_LOCK}" /opt/spack-environment/spack.lock; fi; \
    cd /opt/spack-environment; \
    spack env activate .; \
    spack external find; \
    spack compiler find; \
    spack install --fail-fast; \
    find -L /opt/views/view/* -type f -exec readlink -f '{}' \; | \
      xargs -r file -i | \
      grep 'charset=binary' | \
      grep 'x-executable\|x-archive\|x-sharedlib' | \
      awk -F: '{print $1}' | xargs -r strip; \
    spack clean --stage; \
    spack env activate --sh -d . > activate.sh; \
    { \
      echo ". /opt/spack/share/spack/setup-env.sh"; \
      echo ". /opt/spack-environment/activate.sh"; \
    } > /etc/profile.d/spack-env.sh; \
    { \
      echo "#!/bin/sh"; \
      echo 'set -e'; \
      echo ". /opt/spack/share/spack/setup-env.sh"; \
      echo ". /opt/spack-environment/activate.sh"; \
      echo 'export PATH="/opt/views/view/bin:${PATH}"'; \
      echo 'export HOME="$(getent passwd "${MDF_USER}" | cut -d: -f6)"'; \
      echo 'cd "${MDF_WORKDIR}"'; \
      echo 'exec "$@"'; \
    } > /entrypoint.sh; \
    chmod a+x /entrypoint.sh; \
    { \
      echo ". /opt/spack/share/spack/setup-env.sh"; \
      echo ". /opt/spack-environment/activate.sh"; \
      echo 'export PATH="/opt/views/view/bin:${PATH}"'; \
      echo 'cd "${MDF_WORKDIR}"'; \
    } > "${home_dir}/.bashrc"; \
    chown "${MDF_USER}:${MDF_USER}" "${home_dir}/.bashrc"; \
    chown -R "${MDF_USER}:${MDF_USER}" /opt/spack-environment /opt/software /opt/views "${MDF_WORKDIR}" "${home_dir}"; \
    ln -s /opt/views/view /opt/view; \
    mkdir -p /usr/share/ornl-mdf/inventory/ubuntu; \
    { \
      echo "image=ubuntu"; \
      echo "base_image=${SPACK_UBUNTU_NOBLE_IMAGE}"; \
      echo "release_tag=${RELEASE_TAG}"; \
      echo "spack_manifest=${SPACK_UBUNTU_MANIFEST}"; \
      echo "repository_revision=${GIT_REVISION}"; \
    } > /usr/share/ornl-mdf/inventory/ubuntu/metadata.env; \
    spack find --json > /usr/share/ornl-mdf/inventory/ubuntu/spack.json; \
    cp spack.lock /usr/share/ornl-mdf/inventory/ubuntu/spack.lock; \
    dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort > /usr/share/ornl-mdf/inventory/ubuntu/apt.tsv

ENTRYPOINT ["/entrypoint.sh"]
USER mdf
WORKDIR /workspace
CMD ["/bin/bash"]
