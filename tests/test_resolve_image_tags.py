from pathlib import Path
from unittest import mock
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from resolve_image_tags import (
    additivefoam_release_tag,
    build_args_for,
    load_config,
    normalize_tag,
    normalize_release_tag,
    resolve_tracker_plans,
    resolve_version_plans,
    spack_composite_tag,
    spack_top_spec_tag,
    tracker_targets,
)


class ResolveImageTagsTests(unittest.TestCase):
    def test_spack_top_spec_tag_uses_primary_spec_version(self):
        self.assertEqual(spack_top_spec_tag("config/spack/exaca.yaml"), "2.0.1")

    def test_spack_composite_tag_uses_all_top_level_specs(self):
        self.assertEqual(spack_composite_tag("config/spack/ubuntu.yaml"), "mpich4.3.0-kokkos4.7.04")

    def test_normalize_tag_rewrites_git_describe_output(self):
        self.assertEqual(normalize_tag("v1.2.0-4-gABC123"), "v1.2.0-4-gabc123")

    def test_normalize_release_tag_strips_leading_v(self):
        self.assertEqual(normalize_release_tag("v1.2.0"), "1.2.0")

    @mock.patch("resolve_image_tags.shutil.rmtree")
    @mock.patch("resolve_image_tags.subprocess.check_output", return_value="v1.2.0\n")
    @mock.patch("resolve_image_tags.subprocess.run")
    def test_additivefoam_release_tag_uses_upstream_release(self, run_mock, output_mock, rmtree_mock):
        self.assertEqual(
            additivefoam_release_tag("https://example.invalid/repo.git", "deadbeef"),
            "1.2.0",
        )
        self.assertEqual(run_mock.call_count, 2)

    def test_version_plans_resolve_primary_tags(self):
        config = load_config()
        with mock.patch("resolve_image_tags.additivefoam_release_tag", return_value="1.2.0"):
            plans = {
                plan.image: plan
                for plan in resolve_version_plans(["ubuntu", "exaca", "thesis", "additivefoam"], config, "deadbeef")
            }
        self.assertEqual(plans["ubuntu"].tag, "mpich4.3.0-kokkos4.7.04")
        self.assertEqual(plans["exaca"].tag, "2.0.1")
        self.assertEqual(plans["thesis"].tag, "4.0.0")
        self.assertEqual(plans["additivefoam"].tag, "1.2.0")
        self.assertEqual(plans["exaca"].base_tag, "mpich4.3.0-kokkos4.7.04")

    def test_tracker_plan_uses_tracker_manifest_without_lock(self):
        config = load_config()
        plans = resolve_tracker_plans(["exaca"], config, "deadbeef")
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].tag, "main")
        self.assertEqual(plans[0].build_args["SPACK_EXACA_MANIFEST"], "exaca-main.yaml")
        self.assertEqual(plans[0].build_args["SPACK_EXACA_LOCK"], "")
        self.assertIsNone(plans[0].lockfile)

    def test_tracker_targets_lists_images_with_tracker_manifests(self):
        self.assertEqual(tracker_targets(load_config()), ["additivefoam", "exaca", "thesis"])

    def test_additivefoam_tracker_uses_main_ref(self):
        config = load_config()
        plans = resolve_tracker_plans(["additivefoam"], config, "deadbeef")
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].tag, "main")
        self.assertEqual(plans[0].build_args["ADDITIVEFOAM_REF"], "main")

    def test_thesis_tracker_uses_master_manifest(self):
        config = load_config()
        plans = resolve_tracker_plans(["thesis"], config, "deadbeef")
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].tag, "master")
        self.assertEqual(plans[0].build_args["SPACK_THESIS_MANIFEST"], "thesis-master.yaml")
        self.assertEqual(plans[0].build_args["SPACK_THESIS_LOCK"], "")

    def test_build_args_for_primary_manifest_uses_lockfile(self):
        build_args, manifest_name, lockfile_name = build_args_for("thesis", load_config(), None)
        self.assertEqual(build_args["SPACK_THESIS_MANIFEST"], "thesis.yaml")
        self.assertEqual(build_args["SPACK_THESIS_LOCK"], "thesis.lock")
        self.assertEqual(manifest_name, "thesis.yaml")
        self.assertEqual(lockfile_name, "thesis.lock")


if __name__ == "__main__":
    unittest.main()
