"""Exercise the README installers without network or real skill-directory writes."""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "venturemorph"
BASH = shutil.which("bash")
POWERSHELL = shutil.which("powershell")
PWSH = shutil.which("pwsh")

BASH_SETUP = """audit_fixture=$1
audit_home=$2
audit_clone_status=$3
git() {
  if [ "$#" -ne 2 ] || [ "$1" != clone ]; then
    return 99
  fi
  if [ "$audit_clone_status" = fail ]; then
    return 128
  fi
  cp -R "$audit_fixture" venturemorph
}
"""

POWERSHELL_SETUP = """param([string]$auditFixture, [string]$auditHome, [string]$auditCloneStatus)
function git {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    if ($Arguments.Count -ne 2 -or $Arguments[0] -ne 'clone') {
        $global:LASTEXITCODE = 99
        return
    }
    if ($auditCloneStatus -eq 'fail') {
        $global:LASTEXITCODE = 128
        return
    }
    Copy-Item -LiteralPath $auditFixture -Destination 'venturemorph' -Recurse -ErrorAction Stop
    $global:LASTEXITCODE = 0
}
"""


def file_contents(directory):
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*") if path.is_file()
    }


class _InstallerCases:
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="venturemorph install ")
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        self.fixture = directory / "clone fixture"
        shutil.copytree(
            SKILL, self.fixture / "skills" / "venturemorph",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        self.work = directory / "working directory with spaces"
        self.work.mkdir()
        self.home = directory / "home with spaces"
        self.home.mkdir()
        self.target = self.home / ".claude" / "skills" / "venturemorph"

        language = "bash" if self.shell_kind == "bash" else "powershell"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        match = re.search(r"```" + language + r"\n(.*?)\n```", readme, re.DOTALL)
        self.assertIsNotNone(match, "README must contain the documented installer")
        # Keep the real HOME untouched; execute every other part of the snippet.
        snippet = match.group(1).replace("$HOME", "$audit_home" if language == "bash" else "$auditHome")
        self.script = directory / ("install.sh" if language == "bash" else "install.ps1")
        setup = BASH_SETUP if language == "bash" else POWERSHELL_SETUP
        self.script.write_text(setup + snippet + "\n", encoding="utf-8" if language == "bash" else "utf-8-sig")

    def install(self, clone_fails=False):
        command = [self.shell]
        if self.shell_kind != "bash":
            command += ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"]
        command += [str(self.script), str(self.fixture), str(self.home), "fail" if clone_fails else "ok"]
        return subprocess.run(
            command, cwd=str(self.work), capture_output=True, text=True,
            timeout=30, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_failure(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_installs_complete_skill_with_spaces_and_license(self):
        self.assert_success(self.install())
        expected = file_contents(self.fixture / "skills" / "venturemorph")
        self.assertTrue("LICENSE" in expected, "The installable skill must include LICENSE")
        actual = file_contents(self.target)
        self.assertEqual(sorted(actual), sorted(expected))
        for name, content in expected.items():
            self.assertTrue(actual[name] == content, "Installed file differs: " + name)
        self.assertEqual((self.target / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())

    def test_existing_directory_is_untouched(self):
        self.target.mkdir(parents=True)
        (self.target / "sentinel.txt").write_bytes(b"existing installation")
        before = file_contents(self.target)
        self.assert_failure(self.install())
        self.assertEqual(file_contents(self.target), before)

    def test_existing_file_is_untouched(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b"existing file")
        self.assert_failure(self.install())
        self.assertEqual(self.target.read_bytes(), b"existing file")

    def test_clone_failure_aborts_before_installation(self):
        self.assert_failure(self.install(clone_fails=True))
        self.assertFalse((self.home / ".claude").exists())


@unittest.skipIf(os.name == "nt", "Bash is tested on POSIX; Windows MSYS is not assumed")
@unittest.skipUnless(BASH, "bash is not installed")
class BashInstallationTests(_InstallerCases, unittest.TestCase):
    shell = BASH
    shell_kind = "bash"


@unittest.skipUnless(os.name == "nt", "Windows PowerShell installer is tested on Windows")
@unittest.skipUnless(POWERSHELL, "Windows PowerShell is not installed")
class WindowsPowerShellInstallationTests(_InstallerCases, unittest.TestCase):
    shell = POWERSHELL
    shell_kind = "powershell"


@unittest.skipUnless(os.name == "nt", "PowerShell installer is tested on Windows")
@unittest.skipUnless(PWSH, "pwsh is not installed")
class PwshInstallationTests(_InstallerCases, unittest.TestCase):
    shell = PWSH
    shell_kind = "pwsh"


if __name__ == "__main__":
    unittest.main()
