from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from select_build_targets import select_targets


BAKE = {
    "target": {
        "_common": {"dockerfile": "ignored"},
        "ubuntu": {"dockerfile": "images/ubuntu/Dockerfile"},
        "exaca": {
            "dockerfile": "images/exaca/Dockerfile",
            "contexts": {"ubuntu-base": "target:ubuntu"},
        },
        "thesis": {
            "dockerfile": "images/thesis/Dockerfile",
            "contexts": {"ubuntu-base": "target:ubuntu"},
        },
        "tooling": {"dockerfile": "images/not-tooling/Dockerfile"},
    }
}


class SelectBuildTargetsTests(unittest.TestCase):
    def test_base_change_includes_reverse_dependencies(self):
        self.assertEqual(
            select_targets(BAKE, ["config/spack/base.yaml"]),
            (["exaca", "thesis", "ubuntu"], ["exaca", "thesis", "ubuntu"]),
        )

    def test_manifest_change_selects_package_and_lock(self):
        self.assertEqual(
            select_targets(BAKE, ["config/spack/exaca.yaml"]),
            (["exaca", "ubuntu"], ["exaca"]),
        )

    def test_shared_toolchain_manifest_rebuilds_dependents_and_lock(self):
        self.assertEqual(
            select_targets(BAKE, ["config/spack/ubuntu.yaml"]),
            (["exaca", "thesis", "ubuntu"], ["exaca", "thesis", "ubuntu"]),
        )

    def test_tracker_manifest_change_selects_package_without_refreshing_lock(self):
        self.assertEqual(
            select_targets(BAKE, ["config/spack/exaca-main.yaml"]),
            (["exaca", "ubuntu"], []),
        )

    def test_lockfile_change_selects_package_without_replacing_the_lock(self):
        self.assertEqual(
            select_targets(BAKE, ["config/spack/exaca.lock"]),
            (["exaca", "ubuntu"], []),
        )

    def test_image_change_selects_package(self):
        self.assertEqual(
            select_targets(BAKE, ["images/thesis/Dockerfile"]),
            (["thesis", "ubuntu"], []),
        )

    def test_bake_change_includes_all_public_packages(self):
        self.assertEqual(
            select_targets(BAKE, ["docker-bake.hcl"]),
            (["exaca", "thesis", "ubuntu"], []),
        )

    def test_image_tag_config_change_includes_all_public_packages(self):
        self.assertEqual(
            select_targets(BAKE, ["config/image-tags.json"]),
            (["exaca", "thesis", "ubuntu"], []),
        )

    def test_new_bake_package_is_discovered(self):
        bake = {"target": {**BAKE["target"], "newsolver": {"dockerfile": "images/newsolver/Dockerfile"}}}
        self.assertEqual(
            select_targets(bake, ["docker-bake.hcl"]),
            (["exaca", "newsolver", "thesis", "ubuntu"], []),
        )

    def test_unrelated_change_selects_nothing(self):
        self.assertEqual(select_targets(BAKE, ["README.md"]), ([], []))


if __name__ == "__main__":
    unittest.main()
