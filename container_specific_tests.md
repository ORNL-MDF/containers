additivefoam
```
# Launch container
docker run -it --rm ghcr.io/ornl-mdf/containers/additivefoam:unreleased

# Check OpenFOAM is on path
which checkMesh # should not be blank

# Check AdditiveFOAM tutorial works
cd /opt/AdditiveFOAM/tutorials/AMB2018-02-B
tail -n 1 log.additiveFoam # should say "Finalising parallel run"
```

exaca
```
# Launch container
docker run -it --rm ghcr.io/ornl-mdf/containers/exaca:unreleased

# Ensure executable is found and launches
which ExaCA
ExaCA # should throw an error saying "must provide path to input file" but should also contain "ExaCA version:" line
mpirun -n 2 ExaCA # should throw input file error, but should also contain "ExaCA version:" line
```

thesis
```
# Launch container
docker run -it --rm ghcr.io/ornl-mdf/containers/thesis:unreleased

# Ensure executable is found and launches
which 3DThesis
3DThesis # should throw an error saying "must provide path to input file"
mpirun -n 2 3DThesis # should throw input file error
```