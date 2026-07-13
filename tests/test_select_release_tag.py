from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from select_release_tag import RegistryEntry, ReleaseSelection, select_release_tag, suffix_for_index, tag_for_index


class SelectReleaseTagTests(unittest.TestCase):
    def test_suffix_progression(self):
        self.assertEqual([suffix_for_index(index) for index in (0, 25, 26, 27, 701)], ["a", "z", "aa", "ab", "zz"])

    def test_release_tag_starts_with_bare_date(self):
        self.assertEqual(
            [tag_for_index("2026-07-10", index) for index in (0, 1, 2, 26, 27)],
            ["2026-07-10", "2026-07-10-a", "2026-07-10-b", "2026-07-10-z", "2026-07-10-aa"],
        )

    def test_selects_first_globally_available_tag(self):
        existing = {("ubuntu", "2026-07-10"): RegistryEntry("old-revision")}

        def probe(target, tag):
            return existing.get((target, tag))

        self.assertEqual(
            select_release_tag("2026-07-10", ["ubuntu", "exaca"], ["exaca"], "new-revision", probe),
            ReleaseSelection("2026-07-10-a", "new"),
        )

    def test_reuses_complete_matching_release(self):
        existing = {
            ("ubuntu", "2026-07-10"): RegistryEntry("revision", "candidate-1"),
            ("exaca", "2026-07-10"): RegistryEntry("revision", "candidate-1"),
        }

        def probe(target, tag):
            return existing.get((target, tag))

        self.assertEqual(
            select_release_tag("2026-07-10", ["ubuntu", "exaca"], ["ubuntu", "exaca"], "revision", probe),
            ReleaseSelection("2026-07-10", "complete", "candidate-1"),
        )

    def test_mismatched_batch_does_not_reuse_tag(self):
        existing = {
            ("ubuntu", "2026-07-10"): RegistryEntry("revision", "candidate-1"),
            ("exaca", "2026-07-10"): RegistryEntry("other-revision"),
        }

        def probe(target, tag):
            return existing.get((target, tag))

        self.assertEqual(
            select_release_tag("2026-07-10", ["ubuntu", "exaca"], ["ubuntu"], "revision", probe),
            ReleaseSelection("2026-07-10-a", "new"),
        )

    def test_resumes_a_consistent_partial_release(self):
        existing = {("ubuntu", "2026-07-10"): RegistryEntry("revision", "candidate-1")}

        def probe(target, tag):
            return existing.get((target, tag))

        self.assertEqual(
            select_release_tag("2026-07-10", ["ubuntu", "exaca"], ["ubuntu", "exaca"], "revision", probe),
            ReleaseSelection("2026-07-10", "resume", "candidate-1"),
        )

    def test_rejects_partial_release_without_candidate_metadata(self):
        existing = {("ubuntu", "2026-07-10"): RegistryEntry("revision")}

        def probe(target, tag):
            return existing.get((target, tag))

        with self.assertRaisesRegex(RuntimeError, "candidate metadata"):
            select_release_tag("2026-07-10", ["ubuntu", "exaca"], ["ubuntu", "exaca"], "revision", probe)


if __name__ == "__main__":
    unittest.main()
