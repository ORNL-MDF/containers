# Containers for ORNL-MDF Myna workflows

## Usage

See available containers at https://github.com/orgs/ORNL-MDF/packages

Options to install are listed for each package. A local Docker installation is
necessary. Once installed, the container can be started with, e.g.:
```
docker run -it ghcr.io/ornl-mdf/containers/[os]:[version] /bin/bash
```


## Updating

If a new package is needed, add it to the `spack.yaml` and run `./build.sh`
