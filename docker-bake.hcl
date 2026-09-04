variable "REGISTRY" {
  default = "ghcr.io/ornl-mdf/containers"
}

variable "RELEASE_TAG" {
  # CI supplies a resolved version or tracker tag. Local builds use unreleased.
  default = "unreleased"
}

variable "SPACK_UBUNTU_MANIFEST" {
  default = "ubuntu.yaml"
}

variable "SPACK_UBUNTU_LOCK" {
  default = "ubuntu.lock"
}

variable "SPACK_EXACA_MANIFEST" {
  default = "exaca.yaml"
}

variable "SPACK_EXACA_LOCK" {
  default = "exaca.lock"
}

variable "SPACK_THESIS_MANIFEST" {
  default = "thesis.yaml"
}

variable "SPACK_THESIS_LOCK" {
  default = "thesis.lock"
}

variable "SPACK_UBUNTU_NOBLE_IMAGE" {
  default = "spack/ubuntu-noble@sha256:c5286e543f226f2c36a6a5ae4c845bc1cd78fad9ece2704dd16256ae774a5d4f"
}

variable "OPENFOAM_IMAGE" {
  default = "openfoam/openfoam10-paraview510@sha256:d6ff1f9a2e7bc3c9177f373bebbdeb542fd8b49144afc24d5e3a3cd9bfae253d"
}

variable "ADDITIVEFOAM_REF" {
  default = "b8f6d48c53555c303fa8186c895aee5712b6ea02"
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
    RELEASE_TAG = "${RELEASE_TAG}"
  }
  labels = {
    "org.opencontainers.image.source" = "https://github.com/ORNL-MDF/containers"
    "org.opencontainers.image.version" = "${RELEASE_TAG}"
    "org.opencontainers.image.revision" = "${GIT_REVISION}"
    "org.opencontainers.image.created" = "${RELEASE_CREATED}"
  }
}

target "ubuntu" {
  inherits = ["_common"]
  dockerfile = "images/ubuntu/Dockerfile"
  tags = ["${REGISTRY}/ubuntu:${RELEASE_TAG}"]
  args = {
    SPACK_UBUNTU_MANIFEST = "${SPACK_UBUNTU_MANIFEST}"
    SPACK_UBUNTU_LOCK = "${SPACK_UBUNTU_LOCK}"
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
  tags = ["${REGISTRY}/additivefoam:${RELEASE_TAG}"]
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
  tags = ["${REGISTRY}/exaca:${RELEASE_TAG}"]
  contexts = {
    ubuntu-base = "target:ubuntu"
  }
  labels = {
    "org.opencontainers.image.description" = "ORNL-MDF ExaCA simulation environment. Full inventory: repository docs/containers."
  }
  args = {
    SPACK_EXACA_MANIFEST = "${SPACK_EXACA_MANIFEST}"
    SPACK_EXACA_LOCK = "${SPACK_EXACA_LOCK}"
  }
}

target "thesis" {
  inherits = ["_common"]
  dockerfile = "images/thesis/Dockerfile"
  tags = ["${REGISTRY}/thesis:${RELEASE_TAG}"]
  contexts = {
    ubuntu-base = "target:ubuntu"
  }
  labels = {
    "org.opencontainers.image.description" = "ORNL-MDF 3DThesis simulation environment. Full inventory: repository docs/containers."
  }
  args = {
    SPACK_THESIS_MANIFEST = "${SPACK_THESIS_MANIFEST}"
    SPACK_THESIS_LOCK = "${SPACK_THESIS_LOCK}"
  }
}
