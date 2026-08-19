from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DockerfileTests(unittest.TestCase):
    def test_ubuntu_uses_a_committed_lock_when_available(self):
        dockerfile = (ROOT / "images" / "ubuntu" / "Dockerfile").read_text()
        self.assertIn("COPY config/spack/ /tmp/spack-config/", dockerfile)
        self.assertIn(
            'if [ -n "${SPACK_UBUNTU_LOCK}" ] && [ -f "/tmp/spack-config/${SPACK_UBUNTU_LOCK}" ]; then cp "/tmp/spack-config/${SPACK_UBUNTU_LOCK}" /opt/spack-environment/spack.lock; fi;',
            dockerfile,
        )

    def test_additivefoam_fetches_tag_references_before_describing_the_revision(self):
        dockerfile = (ROOT / "images" / "additivefoam" / "Dockerfile").read_text()
        self.assertIn('git -C "${ADDITIVEFOAM_DIR}" fetch origin "${ADDITIVEFOAM_REF}";', dockerfile)
        self.assertIn('git -C "${ADDITIVEFOAM_DIR}" fetch --tags origin;', dockerfile)
        self.assertNotIn('fetch --depth 1 origin "${ADDITIVEFOAM_REF}"', dockerfile)


if __name__ == "__main__":
    unittest.main()
