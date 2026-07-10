import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate-container-docs.py"


class GenerateContainerDocsTests(unittest.TestCase):
    def test_renders_embedded_inventory_and_updates_index(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            inventory = temp_path / "inventory" / "exaca"
            inventory.mkdir(parents=True)
            (inventory / "metadata.env").write_text(
                "image=exaca\nbase_image=spack/ubuntu-noble@sha256:base\nrepository_revision=abc123\n"
            )
            (inventory / "apt.tsv").write_text("cmake\t3.28.3\n")
            (inventory / "spack.json").write_text(json.dumps([{"name": "exaca", "version": "1.2.3"}]))

            output = temp_path / "docs"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--image",
                    "exaca",
                    "--tag",
                    "2026-07-10",
                    "--digest",
                    "sha256:published",
                    "--inventory",
                    str(temp_path / "inventory"),
                    "--output-root",
                    str(output),
                ],
                check=True,
            )

            page = (output / "exaca" / "2026-07-10.md").read_text()
            self.assertIn("`sha256:published`", page)
            self.assertIn("`spack:exaca`", page)
            self.assertIn("`1.2.3`", page)
            self.assertIn("[exaca:2026-07-10](exaca/2026-07-10.md)", (output / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
