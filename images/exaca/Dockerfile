FROM ubuntu-base

USER root
ARG GIT_REVISION=local

COPY config/spack/ /tmp/spack-config/

RUN cp /tmp/spack-config/base.yaml /opt/spack-environment/base.yaml \
&&  cp /tmp/spack-config/exaca.yaml /opt/spack-environment/spack.yaml \
&&  if [ -f /tmp/spack-config/exaca.lock ]; then cp /tmp/spack-config/exaca.lock /opt/spack-environment/spack.lock; fi \
&&  cd /opt/spack-environment \
&&  spack env activate . \
&&  spack external find \
&&  spack compiler find \
&&  spack install --fail-fast \
&&  find -L /opt/views/view/* -type f -exec readlink -f '{}' \; | \
    xargs file -i | \
    grep 'charset=binary' | \
    grep 'x-executable\|x-archive\|x-sharedlib' | \
    awk -F: '{print $1}' | xargs -r strip \
&&  spack gc -y \
&&  spack env activate --sh -d . > activate.sh \
&&  mkdir -p /usr/share/ornl-mdf/inventory/exaca \
&&  { \
      echo "image=exaca"; \
      echo "repository_revision=${GIT_REVISION}"; \
    } > /usr/share/ornl-mdf/inventory/exaca/metadata.env \
&&  spack find --json > /usr/share/ornl-mdf/inventory/exaca/spack.json \
&&  cp spack.lock /usr/share/ornl-mdf/inventory/exaca/spack.lock

ENTRYPOINT ["/entrypoint.sh"]
USER mdf
CMD ["/bin/bash"]
