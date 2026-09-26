import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent


def _run(cmd: list[str], cwd: Path) -> None:
    p = subprocess.run(cmd, cwd=str(cwd))
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def _find_iscc() -> Path:
    env_path = os.environ.get("INNOSETUP_ISCC")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))

    candidates.extend(
        [
            Path(r"C:\Program Files\Inno Setup 7\ISCC.exe"),
            Path(r"C:\Program Files (x86)\Inno Setup 7\ISCC.exe"),
            Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
            Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        ]
    )

    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(
        "ISCC.exe não encontrado. Defina a variável INNOSETUP_ISCC ou instale o Inno Setup."
    )


def _read_version_from_installer(installer_iss: Path) -> str:
    text = installer_iss.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^#define\s+MyAppVersion\s+\"([^\"]+)\"\s*$", text, re.MULTILINE)
    if not m:
        raise ValueError("Não foi possível localizar MyAppVersion no installer.iss")
    return m.group(1)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args(argv)

    installer_iss = REPO_ROOT / "installer.iss"
    version_info = REPO_ROOT / "version_info.py"
    app_py = REPO_ROOT / "app.py"

    _read_version_from_installer(installer_iss)

    py = Path(sys.executable)
    pyinstaller = REPO_ROOT / ".venv" / "Scripts" / "pyinstaller.exe"
    if not pyinstaller.exists():
        pyinstaller = py.parent / "pyinstaller.exe"

    if args.clean:
        for d in [REPO_ROOT / "build", REPO_ROOT / "dist"]:
            if d.exists():
                for p in sorted(d.rglob("*"), reverse=True):
                    if p.is_file():
                        p.unlink()
                    elif p.is_dir():
                        try:
                            p.rmdir()
                        except OSError:
                            pass
                try:
                    d.rmdir()
                except OSError:
                    pass

    _run(
        [
            str(pyinstaller),
            "--noconsole",
            "--name",
            "Lembretes",
            "--onefile",
            "--version-file",
            str(version_info),
            str(app_py),
        ],
        cwd=REPO_ROOT,
    )

    iscc = _find_iscc()
    _run([str(iscc), str(installer_iss)], cwd=REPO_ROOT)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
