"""Exercise build orchestration without downloading packages or running a build."""

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch
import uuid

from scripts import build as builder


class BuildTests(unittest.TestCase):
    def setUp(self):
        # Python 3.13's mode=0700 temporary folders can exclude a Windows sandbox.
        self.test_parent = (Path(__file__).resolve().parents[1] / 'build').resolve()
        self.temporary = self.test_parent / f'test build {uuid.uuid4().hex}'
        self.root = self.temporary / 'project'
        self.root.mkdir(parents=True)
        self.addCleanup(self.cleanup_directory)
        self.calls = []
        self.missing = '[]'
        self.fail_stage = None
        self.create_output = True

    def cleanup_directory(self):
        target = self.temporary.resolve()
        if not target.is_relative_to(self.test_parent) or target == self.test_parent:
            raise RuntimeError(f'Refusing to remove directory outside the test workspace: {target}')
        shutil.rmtree(target)

    def create_python(self):
        python = builder.environment_python(self.root)
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()

    def fake_run(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if command[1:3] == ['-m', 'venv']:
            self.create_python()
        if command[1:3] == ['-m', self.fail_stage]:
            raise subprocess.CalledProcessError(17, command)
        if command[1:3] == ['-m', 'PyInstaller'] and self.create_output:
            output = Path(command[command.index('--distpath') + 1]) / 'GNSS-Time-Converter'
            output.mkdir(parents=True, exist_ok=True)
            name = 'GNSS-Time-Converter.exe' if os.name == 'nt' else 'GNSS-Time-Converter'
            (output / name).touch()
        return subprocess.CompletedProcess(command, 0, stdout=self.missing, stderr='')

    def run_build(self, arguments=()):
        with patch.object(builder.subprocess, 'run', side_effect=self.fake_run), redirect_stdout(io.StringIO()):
            builder.build(builder.parse_args(arguments), self.root)

    def test_existing_environment_never_installs_or_upgrades_dependencies(self):
        self.create_python()
        self.run_build()
        self.assertFalse(any(command[1:3] == ['-m', 'pip'] for command, _ in self.calls))
        command, options = self.calls[-1]
        self.assertNotIn('--clean', command)
        self.assertEqual(options['cwd'], self.root)
        self.assertEqual(command[-1], str(self.root / 'GNSS-Time-Converter.spec'))

    def test_first_build_creates_environment_and_installs_only_missing_packages(self):
        self.missing = '["PyQt5", "PyQt5-sip"]'
        self.run_build()
        self.assertEqual(self.calls[0][0][1:3], ['-m', 'venv'])
        install = next(command for command, _ in self.calls if command[1:3] == ['-m', 'pip'])
        self.assertEqual(install[3:], ['install', 'PyQt5', 'PyQt5-sip'])
        self.assertEqual(install[0], str(builder.environment_python(self.root)))

    def test_environment_from_another_platform_is_not_overwritten(self):
        (self.root / '.venv').mkdir()
        with self.assertRaisesRegex(RuntimeError, 'no usable interpreter'):
            self.run_build()
        self.assertEqual(self.calls, [])

    def test_dependency_install_failure_stops_before_pyinstaller(self):
        self.create_python()
        self.missing = '["PyQt5"]'
        self.fail_stage = 'pip'
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_build()
        self.assertFalse(any(command[1:3] == ['-m', 'PyInstaller'] for command, _ in self.calls))

    def test_build_failure_is_not_reported_as_success(self):
        self.create_python()
        self.fail_stage = 'PyInstaller'
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_build()

    def test_missing_executable_is_not_reported_as_success(self):
        self.create_python()
        self.create_output = False
        with self.assertRaisesRegex(RuntimeError, 'without producing'):
            self.run_build()

    def test_clean_is_explicit_and_accepts_legacy_argument(self):
        self.create_python()
        for argument in ['clean', '--clean']:
            with self.subTest(argument=argument):
                self.run_build([argument])
                self.assertIn('--clean', self.calls[-1][0])

    def test_default_paths_do_not_depend_on_working_directory(self):
        self.create_python()
        original_cwd = Path.cwd()
        try:
            os.chdir(self.temporary)
            self.run_build()
        finally:
            os.chdir(original_cwd)
        command = self.calls[-1][0]
        self.assertEqual(command[command.index('--distpath') + 1], str(self.root / 'dist'))
        self.assertEqual(command[command.index('--workpath') + 1], str(self.root / 'build'))

    @unittest.skipUnless(os.name == 'nt', 'Windows launcher integration test')
    def test_windows_launcher_preserves_failure_exit_code(self):
        result = subprocess.run(
            ['cmd', '/c', str(builder.PROJECT_ROOT / 'build_windows.bat'), '--unsupported-option'],
            cwd=self.temporary, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
