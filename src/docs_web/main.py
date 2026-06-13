from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Any

import markdown  # type: ignore[import-untyped]
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Setup paths relative to this file location
BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR.parent.parent / "docs"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


def get_versions() -> tuple[str, str]:
    """Read the CLI and docs website versions from pyproject.toml."""
    cli_ver = "0.13.10"
    docs_ver = "0.13.5"
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with pyproject_path.open("rb") as f:
                data = tomllib.load(f)
                cli_ver = data.get("project", {}).get("version", cli_ver)
                docs_ver = (
                    data.get("tool", {})
                    .get("vinylkit", {})
                    .get("docs", {})
                    .get("version", docs_ver)
                )
    except Exception:
        pass
    return cli_ver, docs_ver


CLI_VERSION, DOCS_VERSION = get_versions()

app = FastAPI(
    title="VinylKit Documentation",
    description="Documentation server for the VinylKit CLI",
    version=DOCS_VERSION,
)

# Mount static files and setup templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.middleware("http")
async def redirect_default_hostname(request: Request, call_next: Any) -> Any:
    """Redirect requests from the default Azure domain to the custom domain."""
    host = request.headers.get("host", "")
    if "azurewebsites.net" in host:
        user_agent = request.headers.get("user-agent", "").lower()
        # Exclude system probes and deployment checkers from redirection
        probes = [
            "appservice",
            "readyforrequest",
            "kube-probe",
            "azure-cli",
            "python",
            "urllib",
            "requests",
            "httpx",
        ]
        if any(probe in user_agent for probe in probes):
            return await call_next(request)

        url = request.url.replace(scheme="https", hostname="vinylkit.app")
        return RedirectResponse(url=str(url), status_code=301)
    return await call_next(request)


def extract_toc(markdown_text: str) -> list[dict[str, Any]]:
    """Extract headings for the Table of Contents sidebar."""
    toc: list[dict[str, Any]] = []
    # Skip code block contents to avoid false headings
    in_code_block = False

    for line in markdown_text.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        match = re.match(r"^(##|###)\s+(.+)$", line)
        if match:
            level = len(match.group(1))  # 2 for h2, 3 for h3
            title = match.group(2).strip()
            # Standard markdown anchor generation:
            # strip formatting, lowercase, kebab-case
            clean_title = re.sub(r"<[^>]+>", "", title)  # strip html tags if any
            clean_title = re.sub(
                r"\[([^\]]+)\]\([^)]+\)", r"\1", clean_title
            )  # strip md links
            anchor = re.sub(r"[^\w\s-]", "", clean_title).strip().lower()
            anchor = re.sub(r"[-\s]+", "-", anchor)
            toc.append(
                {
                    "level": level,
                    "title": clean_title,
                    "anchor": anchor,
                }
            )
    return toc


def get_nav_items() -> list[dict[str, str]]:
    """Get navigation links mapping to document names."""
    return [
        {"title": "Introduction", "name": "readme"},
        {"title": "Quickstart Guide", "name": "quickstart"},
        {"title": "Download & Install", "name": "download"},
        {"title": "User Guide", "name": "user-guide"},
        {"title": "Configuration Reference", "name": "configuration"},
        {"title": "Tag Mapping Guide", "name": "tag-mapping"},
        {"title": "Data Model Reference", "name": "data-model"},
        {"title": "Developer Guide", "name": "developer-guide"},
        {"title": "Authentication Guide", "name": "auth"},
        {"title": "Specification Spec", "name": "spec"},
        {"title": "Examples Guide", "name": "examples"},
    ]


@app.get("/install.sh")
def get_install_sh() -> FileResponse:
    """Serve the macOS/Linux bash installer script."""
    return FileResponse(
        path=STATIC_DIR / "install.sh",
        media_type="text/x-shellscript",
        filename="install.sh",
    )


@app.get("/install.ps1")
def get_install_ps1() -> FileResponse:
    """Serve the Windows PowerShell installer script."""
    return FileResponse(
        path=STATIC_DIR / "install.ps1",
        media_type="text/plain",
        filename="install.ps1",
    )


@app.get("/install.cmd")
def get_install_cmd() -> FileResponse:
    """Serve the Windows CMD installer script."""
    return FileResponse(
        path=STATIC_DIR / "install.cmd",
        media_type="text/plain",
        filename="install.cmd",
    )


@app.get("/", response_class=RedirectResponse)
def read_root() -> RedirectResponse:
    """Redirect root access to quickstart guide."""
    return RedirectResponse(url="/docs/quickstart")


@app.get("/docs/search")
def api_search(q: str = "") -> list[dict[str, Any]]:
    """Full-text search endpoint."""
    results: list[dict[str, Any]] = []
    query = q.strip()
    if not query:
        return results

    query_lower = query.lower()
    files = list(DOCS_DIR.glob("*.md"))
    readme_path = DOCS_DIR.parent / "README.md"
    if readme_path.exists():
        files.append(readme_path)

    for file_path in files:
        if file_path.name == "GEMINI.md":
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            continue

        # Extract title from first # header or fall back to filename
        title = file_path.stem.replace("-", " ").title()
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        if query_lower in content.lower():
            snippets: list[str] = []
            # Find indices of matches in lowercase text
            matches = [
                m.start() for m in re.finditer(re.escape(query_lower), content.lower())
            ]
            for start_idx in matches[:3]:  # Return at most 3 snippets
                start = max(0, start_idx - 60)
                end = min(len(content), start_idx + len(query) + 60)
                snippet = content[start:end]
                # Replace linebreaks with spaces
                snippet = " ".join(snippet.split())
                # Highlight matched phrase
                match_start = snippet.lower().find(query_lower)
                if match_start != -1:
                    actual_match = snippet[match_start : match_start + len(query)]
                    highlighted = (
                        snippet[:match_start]
                        + f"<mark>{actual_match}</mark>"
                        + snippet[match_start + len(query) :]
                    )
                    snippets.append(f"...{highlighted}...")

            page_name = "readme" if file_path.name == "README.md" else file_path.stem
            results.append(
                {
                    "title": title,
                    "url": f"/docs/{page_name}",
                    "snippets": snippets,
                }
            )

    return results


def rewrite_md_links(html: str) -> str:
    """Rewrite relative .md links to point to the clean route path name."""

    def repl(match: re.Match[str]) -> str:
        quote = match.group(1)
        path = match.group(2)
        anchor = match.group(3) or ""
        # Handle parent directory links like ../README.md
        if path.lower().endswith("readme") or path.lower().endswith("readme.md"):
            return f"href={quote}/docs/readme{anchor}{quote}"
        # Strip parent directory prefix like ../docs/
        path_name = path.split("/")[-1]
        return f"href={quote}/docs/{path_name}{anchor}{quote}"

    # Regex to match relative hrefs ending with .md in double or single quotes
    pattern = r'href=(["\'])(?![a-z]+://)([^"\']+)\.md(#?[^"\']*)\1'
    return re.sub(pattern, repl, html, flags=re.IGNORECASE)


@app.get("/docs/{page_name}", response_class=HTMLResponse)
def read_doc(request: Request, page_name: str) -> HTMLResponse:
    """Render documentation page."""
    # Resolve the correct markdown file path
    if page_name.lower() == "readme":
        file_path = DOCS_DIR.parent / "README.md"
    else:
        file_path = DOCS_DIR / f"{page_name}.md"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Documentation page not found")

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as err:
        raise HTTPException(status_code=500, detail="Error reading file") from err

    # Parse headings for right-sidebar TOC
    toc = extract_toc(content)

    # Convert markdown to HTML (with standard extensions)
    # extensions like extra (tables, attributes), codehilite (syntax highlighting), toc
    html_content = markdown.markdown(
        content,
        extensions=[
            "extra",
            "codehilite",
            "nl2br",
            "toc",
        ],
    )

    # Rewrite relative .md links to point to the clean route path name
    html_content = rewrite_md_links(html_content)

    # Extract display title from markdown heading
    title = page_name.replace("-", " ").title()
    for line in content.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break

    nav_items = get_nav_items()

    return templates.TemplateResponse(
        request=request,
        name="page.html",
        context={
            "title": title,
            "content": html_content,
            "toc": toc,
            "nav_items": nav_items,
            "active_page": page_name,
            "cli_version": CLI_VERSION,
            "docs_version": DOCS_VERSION,
        },
    )


def main() -> None:
    """Start uvicorn for local or Azure hosting."""
    import importlib.util

    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "127.0.0.1")

    # Dynamically determine the import module path
    try:
        if importlib.util.find_spec("src.docs_web.main") is not None:
            module_path = "src.docs_web.main:app"
        else:
            module_path = "docs_web.main:app"
    except ModuleNotFoundError:
        module_path = "docs_web.main:app"

    uvicorn.run(module_path, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
