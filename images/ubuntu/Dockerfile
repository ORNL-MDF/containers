# Repository-owned Ubuntu Noble base for ORNL-MDF workflow images.
ARG SPACK_UBUNTU_NOBLE_IMAGE=spack/ubuntu-noble:develop
FROM ${SPACK_UBUNTU_NOBLE_IMAGE}
ARG SPACK_UBUNTU_NOBLE_IMAGE
ARG GIT_REVISION=local

ENV MDF_USER=mdf
ENV MDF_UID=1000
ENV MDF_GID=1000
ENV MDF_WORKDIR=/workspace
ENV MAKEFLAGS=

COPY config/spack/base.yaml /opt/spack-environment/spack.yaml

RUN apt-get update \
&&  apt-get install -y --no-install-recommends \
    python3-full \
    python3-dev \
    python3-pip \
    python-is-python3 \
    build-essential \
    cmake \
    vim \
    emacs \
    wget \
    libssl-dev \
    libffi-dev \
    libxrender1 \
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
    cd /opt/spack-environment; \
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
      echo "repository_revision=${GIT_REVISION}"; \
    } > /usr/share/ornl-mdf/inventory/ubuntu/metadata.env; \
    dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort > /usr/share/ornl-mdf/inventory/ubuntu/apt.tsv

ENTRYPOINT ["/entrypoint.sh"]
USER mdf
WORKDIR /workspace
CMD ["/bin/bash"]
