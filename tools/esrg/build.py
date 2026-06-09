"""esrg PyInstaller build script.

Detects host architecture, auto-downloads missing binaries (es.exe / rg.exe),
and runs PyInstaller to produce a standalone esrg.exe.

Usage:
    python build.py               # onefile build (auto-download if needed)
    python build.py --dir         # onedir build (faster startup, easier debug)
    python build.py --download    # download binaries only, skip build
"""

import io
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BINS = ROOT / "bins"
DIST = ROOT / "dist"
BUILD = ROOT / "build"

# ── Binary versions & URLs ────────────────────────────────────────────
ES_VERSION = "1.1.0.30"
ES_URL_TEMPLATE = f"https://www.voidtools.com/ES-{ES_VERSION}.{{arch}}.zip"

RG_VERSION = "15.1.0"
RG_URLS = {
    "x64": f"https://github.com/BurntSushi/ripgrep/releases/download/{RG_VERSION}/ripgrep-{RG_VERSION}-x86_64-pc-windows-msvc.zip",
    "ARM64": f"https://github.com/BurntSushi/ripgrep/releases/download/{RG_VERSION}/ripgrep-{RG_VERSION}-aarch64-pc-windows-msvc.zip",
    # x86 / ARM: no official ripgrep Windows binary — esrg can still use es.exe only
}

# ── Architecture mapping ──────────────────────────────────────────────
_ARCH_MAP = {
    "AMD64": "x64",
    "x86_64": "x64",
    "x86": "x86",
    "i386": "x86",
    "i686": "x86",
    "ARM64": "ARM64",
    "aarch64": "ARM64",
    "ARM": "ARM",
    "armv7l": "ARM",
}


def _detect_arch() -> str:
    machine = platform.machine()
    arch = _ARCH_MAP.get(machine)
    if arch is None:
        print(f"!  Unknown architecture: {machine}, falling back to x64")
        return "x64"
    return arch


# ── Download helpers ──────────────────────────────────────────────────

def _download_file(url: str, dest: Path, label: str) -> None:
    """Download a file with progress indication."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  ↓ downloading {label}...")
    print(f"    {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "esrg-build/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        dest.write_bytes(data)
        size_kb = len(data) / 1024
        print(f"    ✓ {label} ({size_kb:.0f} KB)")
    except Exception as e:
        sys.exit(f"    ✘ Failed to download {label}: {e}")


def _extract_es(zip_path: Path, dest_dir: Path) -> Path:
    """Extract es.exe from a downloaded zip. Returns path to es.exe."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    es_exe = dest_dir / "es.exe"
    if not es_exe.exists():
        sys.exit(f"    ✘ es.exe not found in {zip_path}")
    zip_path.unlink()  # clean up zip after extraction
    return es_exe


def _extract_rg(zip_path: Path, dest_dir: Path) -> Path:
    """Extract rg.exe from a downloaded ripgrep zip. Returns path to rg.exe."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        # ripgrep zip has a top-level directory; find rg.exe inside it
        for member in zf.namelist():
            if member.endswith("/rg.exe") or member == "rg.exe":
                # Extract to dest_dir directly (strip leading dirs)
                source = zf.open(member)
                target = dest_dir / "rg.exe"
                with open(target, "wb") as out:
                    out.write(source.read())
                zip_path.unlink()
                return target
        # Fallback: extract all and find rg.exe
        zf.extractall(dest_dir)
    zip_path.unlink()
    # Try to find rg.exe anywhere under dest_dir
    for rg in dest_dir.rglob("rg.exe"):
        if rg.parent != dest_dir:
            shutil.move(str(rg), str(dest_dir / "rg.exe"))
            # Clean up extracted directory
            for d in list(dest_dir.iterdir()):
                if d.is_dir():
                    shutil.rmtree(d)
        return dest_dir / "rg.exe"
    sys.exit(f"    ✘ rg.exe not found in {zip_path}")


def _download_es(arch: str, dest_dir: Path) -> Path:
    """Download and extract es.exe for the given architecture."""
    url = ES_URL_TEMPLATE.format(arch=arch)
    zip_path = dest_dir / f"ES-{ES_VERSION}.{arch}.zip"
    _download_file(url, zip_path, f"es.exe ({arch})")
    return _extract_es(zip_path, dest_dir)


def _download_rg(arch: str, dest_dir: Path) -> Path | None:
    """Download and extract rg.exe for the given architecture.
    Returns None if no ripgrep binary is available for this arch.
    """
    url = RG_URLS.get(arch)
    if url is None:
        print(f"  !  No ripgrep binary for {arch} — content search will use ES only")
        return None
    zip_path = dest_dir / f"ripgrep-{RG_VERSION}-{arch}.zip"
    _download_file(url, zip_path, f"rg.exe ({arch})")
    return _extract_rg(zip_path, dest_dir)


def download_binaries(arch: str | None = None) -> str:
    """Ensure es.exe and rg.exe exist for the given (or detected) arch.
    Downloads missing binaries automatically. Returns the arch used.
    """
    if arch is None:
        arch = _detect_arch()
    bin_dir = BINS / arch
    bin_dir.mkdir(parents=True, exist_ok=True)

    es_exe = bin_dir / "es.exe"
    rg_exe = bin_dir / "rg.exe"

    if not es_exe.exists():
        print("→ es.exe not found, downloading...")
        _download_es(arch, bin_dir)
    else:
        print(f"  ✓ es.exe ({arch}) — {es_exe.stat().st_size // 1024} KB")

    if not rg_exe.exists():
        if arch in RG_URLS:
            print("→ rg.exe not found, downloading...")
            _download_rg(arch, bin_dir)
        else:
            print(f"  !  No ripgrep binary for {arch}, skipping rg.exe")
    else:
        print(f"  ✓ rg.exe ({arch}) — {rg_exe.stat().st_size // 1024} KB")

    return arch


# ── Build ─────────────────────────────────────────────────────────────

def _clean():
    """Remove previous build artifacts."""
    for d in (DIST, BUILD):
        if d.exists():
            shutil.rmtree(d)
    spec = ROOT / "esrg.spec"
    if spec.exists():
        spec.unlink()


def build(onedir: bool = False):
    arch = download_binaries()
    bin_dir = BINS / arch
    es_exe = bin_dir / "es.exe"
    rg_exe = bin_dir / "rg.exe"

    if not es_exe.exists():
        sys.exit(f"✘ Missing binary: {es_exe}")
    if not rg_exe.exists():
        sys.exit(f"✘ Missing binary: {rg_exe}")

    _clean()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "esrg",
        "--add-binary", f"{es_exe};bins",
        "--add-binary", f"{rg_exe};bins",
        "--hidden-import", "textual",
        "--collect-all", "textual",
        "--clean",
        "--noconfirm",
    ]

    if onedir:
        cmd.insert(2, "--onedir")
        print(f"\n→ Building esrg (onedir, {arch})...")
    else:
        cmd.insert(2, "--onefile")
        print(f"\n→ Building esrg (onefile, {arch})...")

    print(f"  es.exe : {es_exe}")
    print(f"  rg.exe : {rg_exe}")

    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        sys.exit(f"✘ PyInstaller failed with code {result.returncode}")

    # Report
    exe = DIST / ("esrg" + (".exe" if sys.platform == "win32" else ""))
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"✓ Built: {exe} ({size_mb:.1f} MB)")
    else:
        # onedir: exe inside dist/esrg/
        inner = DIST / "esrg" / ("esrg" + (".exe" if sys.platform == "win32" else ""))
        if inner.exists():
            size_mb = inner.stat().st_size / (1024 * 1024)
            print(f"✓ Built: {inner} ({size_mb:.1f} MB)")
        else:
            print(f"✓ Build complete — see {DIST}/")


if __name__ == "__main__":
    if "--download" in sys.argv or "--download-only" in sys.argv:
        arch = _detect_arch()
        print(f"→ Downloading binaries for {arch}...")
        download_binaries(arch)
        print("✓ Binaries ready.")
    else:
        onedir = "--dir" in sys.argv or "--onedir" in sys.argv
        build(onedir=onedir)
