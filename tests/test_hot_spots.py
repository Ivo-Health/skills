import contextlib
import importlib.util
import io
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/ivo-health/skills/improve-dotnet-architecture/scripts/hot_spots.py"


def _load():
    spec = importlib.util.spec_from_file_location("hot_spots", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HotSpotsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

    def commit(self, files: dict, message="change"):
        for name, text in files.items():
            path = self.repo / name
            if text is None:
                path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def analyse(self, **kwargs):
        return _load().analyse(self.repo, since="10 years ago", **kwargs)

    def test_follows_renames(self):
        self.commit({"Old/Thing.cs": "class Thing {}\n" * 20})
        (self.repo / "New").mkdir()
        self.git("mv", "Old/Thing.cs", "New/Thing.cs")
        self.commit({})
        self.commit({"New/Thing.cs": "class Thing {}\n" * 20 + "// more\n"})
        churn, _ = self.analyse()
        self.assertEqual(churn, {"New/Thing.cs": 3})

    def test_razor_and_code_behind_count_as_one(self):
        self.commit({"Pages/Rota.razor": "<p>a</p>\n", "Pages/Rota.razor.cs": "partial class Rota {}\n"})
        churn, pairs = self.analyse()
        self.assertEqual(churn, {"Pages/Rota.razor": 1})
        self.assertEqual(pairs, {})

    def test_leaves_out_tests_migrations_and_deleted_files(self):
        self.commit({
            "App/Service.cs": "class S {}\n",
            "App.Tests/ServiceTests.cs": "class T {}\n",
            "Db/Migrations/20260101_Init.cs": "class M {}\n",
            "App/Gone.cs": "class G {}\n",
        })
        self.commit({"App/Gone.cs": None})
        churn, _ = self.analyse()
        self.assertEqual(churn, {"App/Service.cs": 1})
        churn, _ = self.analyse(include_tests=True)
        self.assertIn("App.Tests/ServiceTests.cs", churn)

    def test_counts_pairs_and_skips_large_commits(self):
        for n in range(2):
            self.commit({"A.cs": f"// {n}\n", "B.cs": f"// {n}\n"})
        self.commit({f"Bulk{n}.cs": "// x\n" for n in range(5)} | {"A.cs": "// 9\n", "B.cs": "// 9\n"})
        _, pairs = self.analyse(max_files=4)
        self.assertEqual(pairs, {("A.cs", "B.cs"): 2})

    def test_repo_can_be_a_subfolder(self):
        self.commit({"src/web/A.cs": "// 1\n", "src/other/B.cs": "// 1\n"})
        churn, _ = _load().analyse(self.repo / "src/web", since="10 years ago")
        self.assertEqual(churn, {"src/web/A.cs": 1})

    def test_bulk_cutoff_counts_files_outside_the_subfolder(self):
        for n in range(2):
            self.commit({"src/web/A.cs": f"// {n}\n", "src/web/B.cs": f"// {n}\n"})
        self.commit({f"src/other/Bulk{n}.cs": "// x\n" for n in range(5)}
                    | {"src/web/A.cs": "// 9\n", "src/web/B.cs": "// 9\n"})
        _, pairs = _load().analyse(self.repo / "src/web", since="10 years ago", max_files=4)
        self.assertEqual(pairs, {("src/web/A.cs", "src/web/B.cs"): 2})

    def test_main_prints_both_lists(self):
        self.commit({"A.cs": "// 1\n", "B.cs": "// 1\n"})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            _load().main(["--repo", str(self.repo), "--since", "10 years ago"])
        text = out.getvalue()
        self.assertIn("Files that change most", text)
        self.assertIn("Total file changes: 2", text)
        self.assertIn("1  A.cs", text)
        self.assertIn("Files that change together", text)
        self.assertIn("1  A.cs  B.cs", text)


if __name__ == "__main__":
    unittest.main()
