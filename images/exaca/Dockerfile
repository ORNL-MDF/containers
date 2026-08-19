FROM ubuntu-base

USER root
ARG GIT_REVISION=local
ARG RELEASE_TAG=unreleased
ARG SPACK_EXACA_MANIFEST=exaca.yaml
ARG SPACK_EXACA_LOCK=exaca.lock

COPY config/spack/ /tmp/spack-config/

RUN cp /tmp/spack-config/base.yaml /opt/spack-environment/base.yaml \
&&  cp "/tmp/spack-config/${SPACK_EXACA_MANIFEST}" /opt/spack-environment/spack.yaml \
&&  rm -f /opt/spack-environment/spack.lock \
&&  if [ -n "${SPACK_EXACA_LOCK}" ] && [ -f "/tmp/spack-config/${SPACK_EXACA_LOCK}" ]; then cp "/tmp/spack-config/${SPACK_EXACA_LOCK}" /opt/spack-environment/spack.lock; fi \
&&  cd /opt/spack-environment \
&&  spack env activate . \
&&  spack external find \
&&  spack install --fail-fast \
&&  find -L /opt/views/view/* -type f -exec readlink -f '{}' \; | \
    xargs -r file -i | \
    grep 'charset=binary' | \
    grep 'x-executable\|x-archive\|x-sharedlib' | \
    awk -F: '{print $1}' | xargs -r strip \
&&  spack clean --stage \
&&  spack env activate --sh -d . > activate.sh \
&&  mkdir -p /usr/share/ornl-mdf/inventory/exaca \
&&  { \
      echo "image=exaca"; \
      echo "release_tag=${RELEASE_TAG}"; \
      echo "spack_manifest=${SPACK_EXACA_MANIFEST}"; \
      echo "repository_revision=${GIT_REVISION}"; \
    } > /usr/share/ornl-mdf/inventory/exaca/metadata.env \
&&  spack find --json > /usr/share/ornl-mdf/inventory/exaca/spack.json \
&&  cp spack.lock /usr/share/ornl-mdf/inventory/exaca/spack.lock

ENTRYPOINT ["/entrypoint.sh"]
USER mdf
CMD ["/bin/bash"]
