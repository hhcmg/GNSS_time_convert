"""Build from either platform using one isolated environment and one spec file."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPENDENCY_PROBE = """
import importlib.util
import json

requirements = [
    ('PyInstaller', 'pyinstaller'),
    ('_pyinstaller_hooks_contrib', 'pyinstaller-hooks-contrib'),
    ('PyQt5', 'PyQt5'),
    ('PyQt5.sip', 'PyQt5-sip'),
]
missing = []
for module, package in requirements:
    try:
        installed = importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:
        installed = False
    if not installed:
        missing.append(package)
print(json.dumps(missing))
"""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', nargs='?', choices=['clean'], help='discard PyInstaller analysis caches')
    parser.add_argument('--clean', action='store_true', help='discard PyInstaller analysis caches')
    parser.add_argument('--distpath', type=Path, help='output directory (default: project/dist)')
    parser.add_argument('--workpath', type=Path, help='cache directory (default: project/build)')
    return parser.parse_args(argv)


def environment_python(project_root):
    relative_path = Path('Scripts/python.exe') if os.name == 'nt' else Path('bin/python')
    return project_root / '.venv' / relative_path


def build(args, project_root=PROJECT_ROOT):
    started = time.perf_counter()
    project_root = Path(project_root).resolve()
    env = os.environ.copy()
    env['PYTHONNOUSERSITE'] = '1'
    env['PIP_DISABLE_PIP_VERSION_CHECK'] = '1'
    python = environment_python(project_root)
    venv_dir = project_root / '.venv'

    if not python.is_file():
        if venv_dir.exists():
            raise RuntimeError(
                f'{venv_dir} has no usable interpreter for this platform. '
                'Move that environment aside and retry to create a new one.'
            )
        print(f'[info] Creating isolated environment: {venv_dir}', flush=True)
        subprocess.run([sys.executable, '-m', 'venv', str(venv_dir)], env=env, check=True)
        if not python.is_file():
            raise RuntimeError(f'Environment creation did not produce {python}')

    probe = subprocess.run(
        [str(python), '-c', DEPENDENCY_PROBE],
        env=env, check=True, capture_output=True, text=True,
    )
    missing = json.loads(probe.stdout)
    if missing:
        print(f'[info] Installing missing build dependencies: {", ".join(missing)}', flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', *missing], env=env, check=True)
    else:
        print('[info] Build dependencies are present; no installation needed.', flush=True)

    # Keep a DLL/import failure distinct from a missing dependency or build error.
    subprocess.run(
        [str(python), '-c', 'from PyQt5 import sip, QtCore, QtGui, QtWidgets'],
        env=env, check=True,
    )
    distpath = (args.distpath or project_root / 'dist').resolve()
    workpath = (args.workpath or project_root / 'build').resolve()
    command = [
        str(python), '-m', 'PyInstaller', '--noconfirm',
        '--distpath', str(distpath), '--workpath', str(workpath),
    ]
    if args.clean or args.mode == 'clean':
        command.append('--clean')
    command.append(str(project_root / 'GNSS-Time-Converter.spec'))
    subprocess.run(command, cwd=project_root, env=env, check=True)

    executable = distpath / 'GNSS-Time-Converter' / (
        'GNSS-Time-Converter.exe' if os.name == 'nt' else 'GNSS-Time-Converter'
    )
    if not executable.is_file():
        raise RuntimeError(f'Build returned without producing {executable}')
    print(f'[done] Output: {executable}', flush=True)
    print(f'[done] Elapsed: {time.perf_counter() - started:.2f}s', flush=True)


def main(argv=None):
    args = parse_args(argv)
    try:
        build(args)
    except subprocess.CalledProcessError as error:
        print(f'[error] Command failed with exit code {error.returncode}: {error.cmd}', file=sys.stderr)
        if error.stderr:
            print(error.stderr.rstrip(), file=sys.stderr)
        return error.returncode or 1
    except (OSError, RuntimeError, ValueError) as error:
        print(f'[error] {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
