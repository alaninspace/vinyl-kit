"""Check that a VinylKit release is consistent end to end.

Compares the versions in the repo with the git tags, the GitHub release and
its assets, the Homebrew/Scoop checksums on origin/main and the live docs
site. Prints PASS/FAIL per check and exits 1 if anything fails.

Usage (from the repo root):
    uv run python .claude/skills/release/verify_release.py
    uv run python .claude/skills/release/verify_release.py --docs-only
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPO = "alaninspace/vinyl-kit"
DOCS_URL = "https://vinylkit.app"
WORKFLOW = "release_vinylkit-cli.yml"
ARCHIVES = (
    "vinylkit-macos-arm64.zip",
    "vinylkit-linux-amd64.tar.gz",
    "vinylkit-windows-amd64.zip",
)
PYAPP_BINARIES = (
    "vinylkit-pyapp-macos-arm64",
    "vinylkit-pyapp-linux-amd64",
    "vinylkit-pyapp-windows-amd64.exe",
)

failures: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}{f'  ({detail})' if detail else ''}")
    if not ok:
        failures.append(label)


def run(*args: str) -> str:
    result = subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "vinylkit-release"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, ""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_repo(cli_ver: str, docs_ver: str) -> None:
    main_py = (ROOT / "src" / "docs_web" / "main.py").read_text(encoding="utf-8")
    check(f'cli_ver = "{cli_ver}"' in main_py, "docs_web cli_ver fallback matches")
    check(f'docs_ver = "{docs_ver}"' in main_py, "docs_web docs_ver fallback matches")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    check(f"## [v{cli_ver}]" in changelog, f"CHANGELOG has a v{cli_ver} entry")

    run("git", "fetch", "--quiet", "--tags", "origin")
    check(
        run("git", "status", "--porcelain", "--untracked-files=no").strip() == "",
        "no uncommitted tracked changes",
    )
    local = run("git", "rev-parse", "HEAD").strip()
    remote = run("git", "rev-parse", "origin/main").strip()
    behind = run("git", "rev-list", "--count", f"{local}..{remote}").strip()
    ahead = run("git", "rev-list", "--count", f"{remote}..{local}").strip()
    check(ahead == "0", "everything is pushed to origin/main", f"{ahead} ahead")
    if behind != "0":
        print(f"note  local main is {behind} commit(s) behind origin (git pull)")

    remote_tags = run("git", "ls-remote", "--tags", "origin")
    for tag in (f"v{cli_ver}", f"docs-v{docs_ver}"):
        check(f"refs/tags/{tag}\n" in remote_tags + "\n", f"tag {tag} is on origin")


def check_release(cli_ver: str) -> None:
    tag = f"v{cli_ver}"
    runs = json.loads(
        run(
            "gh",
            "run",
            "list",
            "--repo",
            REPO,
            "--workflow",
            WORKFLOW,
            "--limit",
            "20",
            "--json",
            "headBranch,status,conclusion,url",
        )
    )
    tag_runs = [r for r in runs if r["headBranch"] == tag]
    latest = tag_runs[0] if tag_runs else None
    check(
        latest is not None and latest["conclusion"] == "success",
        f"release workflow for {tag} succeeded",
        latest["url"] if latest else "no run found",
    )

    try:
        release = json.loads(
            run(
                "gh",
                "release",
                "view",
                tag,
                "--repo",
                REPO,
                "--json",
                "assets,isDraft,body",
            )
        )
    except RuntimeError as err:
        check(False, f"GitHub release {tag} exists", str(err))
        return
    names = {a["name"] for a in release["assets"]}
    check(not release["isDraft"], f"GitHub release {tag} is published")
    missing = [n for n in (*ARCHIVES, *PYAPP_BINARIES) if n not in names]
    check(not missing, "release has all 6 assets", ", ".join(missing))
    check(bool(release["body"].strip()), "release notes are not empty")

    formula = run("git", "show", "origin/main:Formula/vinyl-kit.rb")
    scoop = json.loads(run("git", "show", "origin/main:scoop/vinylkit.json"))
    check(f'version "{cli_ver}"' in formula, "Homebrew formula version matches")
    check(scoop.get("version") == cli_ver, "Scoop manifest version matches")

    with tempfile.TemporaryDirectory() as tmp:
        run(
            "gh",
            "release",
            "download",
            tag,
            "--repo",
            REPO,
            "--dir",
            tmp,
            *(arg for name in ARCHIVES for arg in ("--pattern", name)),
        )
        for name in ARCHIVES[:2]:
            match = re.search(
                rf'url "[^"]*/{tag}/{re.escape(name)}"\s+sha256 "([^"]*)"', formula
            )
            actual = sha256(Path(tmp) / name)
            check(
                bool(match) and match.group(1) == actual,
                f"Homebrew sha256 for {name} matches the release asset",
                "" if match and match.group(1) == actual else f"expected {actual}",
            )
        actual_win = sha256(Path(tmp) / ARCHIVES[2])
        check(
            scoop.get("hash") == actual_win
            and f"/{tag}/{ARCHIVES[2]}" in scoop.get("url", ""),
            f"Scoop url and hash match {ARCHIVES[2]}",
        )


def check_docs_site(cli_ver: str, docs_ver: str) -> None:
    status, body = fetch(f"{DOCS_URL}/docs/readme")
    check(status == 200, "docs site answers 200", str(status))
    check(f"v{docs_ver}" in body, f"docs site shows docs v{docs_ver}")
    check(f"v{cli_ver}" in body, f"docs site shows CLI v{cli_ver}")
    status, _ = fetch(f"{DOCS_URL}/metrics")
    check(status == 404, "public /metrics is still 404", str(status))


def main() -> int:
    docs_only = "--docs-only" in sys.argv[1:]
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    cli_ver = pyproject["project"]["version"]
    docs_ver = pyproject["tool"]["vinylkit"]["docs"]["version"]
    print(f"Checking CLI v{cli_ver}, docs v{docs_ver}\n")

    check_repo(cli_ver, docs_ver)
    if not docs_only:
        check_release(cli_ver)
    check_docs_site(cli_ver, docs_ver)

    print(f"\n{len(failures)} check(s) failed" if failures else "\nAll checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
