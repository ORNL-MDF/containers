variable "REGISTRY" {
  default = "ghcr.io/ornl-mdf/containers"
}

variable "RELEASE_DATE" {
  # CI supplies an immutable UTC date. This fallback is only for local builds.
  default = "unreleased"
}

variable "SPACK_UBUNTU_NOBLE_IMAGE" {
  default = "spack/ubuntu-noble:develop"
}

variable "OPENFOAM_IMAGE" {
  default = "openfoam/openfoam10-paraview510"
}

variable "ADDITIVEFOAM_REF" {
  default = "1.2.0"
}

variable "GIT_REVISION" {
  default = "local"
}

variable "RELEASE_CREATED" {
  default = ""
}

variable "OUTPUT_TYPE" {
  default = "docker"
}

variable "PUSH" {
  default = "false"
}

group "default" {
  targets = ["ubuntu", "additivefoam", "exaca", "thesis"]
}

group "base" {
  targets = ["ubuntu", "additivefoam"]
}

group "solvers" {
  targets = ["exaca", "thesis"]
}

target "_common" {
  context = "."
  output = ["type=${OUTPUT_TYPE},push=${PUSH}"]
  args = {
    GIT_REVISION = "${GIT_REVISION}"
  }
  labels = {
    "org.opencontainers.image.source" = "https://github.com/ORNL-MDF/containers"
    "org.opencontainers.image.version" = "${RELEASE_DATE}"
    "org.opencontainers.image.revision" = "${GIT_REVISION}"
    "org.opencontainers.image.created" = "${RELEASE_CREATED}"
  }
}

target "ubuntu" {
  inherits = ["_common"]
  dockerfile = "images/ubuntu/Dockerfile"
  tags = ["${REGISTRY}/ubuntu:${RELEASE_DATE}"]
  args = {
    SPACK_UBUNTU_NOBLE_IMAGE = "${SPACK_UBUNTU_NOBLE_IMAGE}"
  }
  labels = {
    "org.opencontainers.image.description" = "ORNL-MDF Ubuntu and Spack base environment. Full inventory: repository docs/containers."
  }
  pull = true
}

target "additivefoam" {
  inherits = ["_common"]
  dockerfile = "images/additivefoam/Dockerfile"
  tags = ["${REGISTRY}/additivefoam:${RELEASE_DATE}"]
  args = {
    OPENFOAM_IMAGE = "${OPENFOAM_IMAGE}"
    ADDITIVEFOAM_REF = "${ADDITIVEFOAM_REF}"
  }
  labels = {
    "org.opencontainers.image.description" = "ORNL-MDF AdditiveFOAM environment. Full inventory: repository docs/containers."
  }
  pull = true
}

target "exaca" {
  inherits = ["_common"]
  dockerfile = "images/exaca/Dockerfile"
  tags = ["${REGISTRY}/exaca:${RELEASE_DATE}"]
  contexts = {
    ubuntu-base = "target:ubuntu"
  }
  labels = {
    "org.opencontainers.image.description" = "ORNL-MDF ExaCA simulation environment. Full inventory: repository docs/containers."
  }
}

target "thesis" {
  inherits = ["_common"]
  dockerfile = "images/thesis/Dockerfile"
  tags = ["${REGISTRY}/thesis:${RELEASE_DATE}"]
  contexts = {
    ubuntu-base = "target:ubuntu"
  }
  labels = {
    "org.opencontainers.image.description" = "ORNL-MDF 3DThesis simulation environment. Full inventory: repository docs/containers."
  }
}
