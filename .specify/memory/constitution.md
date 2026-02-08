# Project Constitution

> Non-negotiable principles governing all specification, planning, and implementation in this project.
> This constitution is the supreme authority — all specs, plans, and generated code MUST comply.

---

## Article I — Solo Project Philosophy

This is a single-developer project. All decisions optimise for:

- **Maintainability over extensibility**: Code will be read far more than it will be extended. Optimise for a developer returning after 6 months cold.
- **Small surface area**: Do not create modules, abstractions, or layers without an immediate, concrete justification in the spec. Every file must earn its existence.
- **Pragmatic architecture**: Use the simplest structure that satisfies the current spec. Refactor when complexity is proven, not predicted.

---

## Article II — Python Standards & Tooling (NON-NEGOTIABLE)

### 2.1 Language Version
- **Python 3.12+** — exploit modern features: `type` statement for aliases, `type[T]` syntax, `match` statements, exception groups where appropriate, and `tomllib` from stdlib.

### 2.2 Project Layout
- `pyproject.toml` is the single source of truth. No `setup.py`, `setup.cfg`, `requirements.txt`, or `MANIFEST.in`.
- **`uv`** for dependency management, virtual environments, and script running. All dependency mutations via `uv add` / `uv remove`.
- `src/` layout mandatory:
  ```
  vinylkit/
  ├── pyproject.toml
  ├── README.md
  ├── src/
  │   └── vinylkit/
  │       ├── __init__.py
  │       ├── py.typed          # PEP 561 marker
  │       └── ...
  └── tests/
      ├── conftest.py
      └── ...
  ```

### 2.3 Code Quality Tooling
- **Ruff** — sole linter AND formatter. No black, flake8, isort, pylint, or bandit.
- Configuration in `pyproject.toml` under `[tool.ruff]`:
  ```toml
  [tool.ruff]
  target-version = "py312"
  line-length = 88

  [tool.ruff.lint]
  select = [
    "E", "F", "W",       # pycodestyle + pyflakes
    "I",                  # isort
    "N",                  # pep8-naming
    "UP",                 # pyupgrade
    "B",                  # flake8-bugbear
    "A",                  # flake8-builtins
    "SIM",                # flake8-simplify
    "TCH",                # flake8-type-checking
    "RUF",                # ruff-specific
    "PT",                 # flake8-pytest-style
    "RET",                # flake8-return
    "ARG",                # flake8-unused-arguments
    "PTH",                # flake8-use-pathlib
    "PERF",               # perflint
    "FURB",               # refurb
  ]
  ```
- **mypy** in strict mode (`--strict`) for static type checking. Zero `type: ignore` comments without an inline justification.

### 2.4 Type System
- `from __future__ import annotations` in every module.
- All function signatures fully typed — parameters, return values, and generic constraints.
- `str | None` not `Optional[str]`. `collections.abc` for abstract container types.
- Use `typing.Protocol` for structural subtyping where interface contracts are needed — no ABCs unless inheriting concrete behaviour.
- Use `TypeAlias`, `TypeVar`, `ParamSpec` where they improve readability. Do not over-genericise.
- `@overload` for functions with genuinely distinct signatures. Not for trivial unions.

---

## Article III — Test-First Imperative (NON-NEGOTIABLE)

1. **No production code without a failing test that demands it.** TDD red-green-refactor cycle is mandatory.
2. **pytest** exclusively. No `unittest.TestCase` subclasses, no `setUp`/`tearDown` — use fixtures.
3. **Test structure**:
   - `tests/` mirrors `src/` package structure.
   - `conftest.py` for shared fixtures scoped appropriately (`session`, `module`, `function`).
   - `@pytest.mark.parametrize` for data-driven tests. No copy-pasted test functions varying only in input.
4. **Mocking discipline**:
   - Mock at the boundary (HTTP calls, filesystem I/O, clock). Never mock internal collaborators.
   - Use `pytest-mock` for patching. Use `respx` or `responses` for HTTP mocking.
   - `tmp_path` fixture for all filesystem tests — never write to real directories.
5. **Coverage**: 85% minimum, measured via `pytest-cov`. Configure in `pyproject.toml`. Coverage gates MUST pass in CI.
6. **Test speed**: Total suite under 10 seconds. Anything requiring network or disk beyond `tmp_path` must be marked `@pytest.mark.integration` and excluded from default runs.

---

## Article IV — Error Handling Architecture

- **Custom exception hierarchy** rooted in a single `VinylkitError(Exception)` base. All project exceptions inherit from it. Never raise bare `Exception`, `ValueError`, or `RuntimeError` for domain errors.
- Catch specific exceptions. No bare `except:`. No `except Exception:` without re-raise or explicit justification.
- `raise ... from err` to preserve chains. Always.
- Use `contextlib.suppress()` for intentional, documented ignoring of specific exceptions — never `except: pass`.
- Return types for operations that can partially succeed: use a result pattern (`@dataclass` with success/failure data) or return `tuple[list[Success], list[Failure]]`. Do not use exceptions for flow control in batch operations.
- Log exceptions with `logger.exception()` to capture tracebacks automatically.

---

## Article V — Structured Logging

- Python `logging` module only. No `print()` for operational output. No third-party logging frameworks (no loguru, no structlog).
- One logger per module: `logger = logging.getLogger(__name__)`.
- Log levels used correctly:
  - `DEBUG`: Detailed diagnostic info (file paths, tag values, API response codes).
  - `INFO`: High-level operations (tagging started, file renamed, scan complete).
  - `WARNING`: Recoverable issues (missing Discogs field, skipped file).
  - `ERROR`: Operation failures that don't halt the program.
  - `CRITICAL`: Reserved for unrecoverable state.
- CLI verbosity flags (`-v`, `-vv`, `-q`) map to log levels.

---

## Article VI — Dependency Governance

- **Stdlib first.** `pathlib` for paths, `tomllib` for reading TOML, `json` for serialisation, `logging` for logs, `dataclasses` for data containers, `enum` for enumerations, `functools` for caching, `concurrent.futures` for parallelism.
- Every third-party dependency requires justification. Document the reason in the commit message introducing it.
- Hard limits on dependency weight: no package that introduces >10 transitive dependencies without explicit sign-off in the plan.
- Pin to compatible ranges: `>=1.2,<2`.
- Dev dependencies isolated in `[tool.uv]` dev-dependency group.
- **Pre-approved dependencies** (may be used without additional justification):
  - `click` or `typer` — CLI framework
  - `mutagen` — audio tag I/O
  - `httpx` — HTTP client (async-capable, modern API)
  - `rich` — terminal output and progress bars
  - `tomli-w` — TOML writing (stdlib only reads)
  - `platformdirs` — cross-platform config/cache/data directories
  - `pytest`, `pytest-cov`, `pytest-mock`, `respx` — testing

---

## Article VII — File & Path Safety (NON-NEGOTIABLE)

This tool mutates user files. Absolute discipline required:

- **`pathlib.Path` everywhere.** No `os.path`, no string concatenation for paths, no hardcoded separators.
- **Filename sanitisation**: Strip or replace characters illegal on any target platform (`<>:"/\|?*`, control characters). Use a configurable replacement character (default `_`). Truncate to 255 bytes (filesystem limit).
- **Long path support on Windows**: Use `\\?\` prefix or ensure paths stay under 260 chars. Document the strategy.
- **Unicode normalisation**: NFC-normalise all filenames before comparison or creation.
- **Atomic writes where possible**: Write to a temp file in the same directory, then `os.replace()` to the target. This prevents corruption on crash.
- **Never delete user files.** Move to a backup/trash location if removal is needed. Backup location must be configurable.

---

## Article VIII — API Client Discipline

- **Single HTTP client instance** per session, reused with connection pooling via `httpx.Client`.
- **Rate limiting**: Respect Discogs 60 req/min (authenticated). Implement as a token bucket or simple sleep-based throttle. The rate limiter MUST be tested.
- **User-Agent header**: Required by Discogs TOS. Format: `VinylKit/{version} +https://github.com/{user}/{repo}`.
- **Response caching**: Cache Discogs release data locally (filesystem-based, keyed by release ID). Cache invalidation by TTL (configurable, default 7 days).
- **Retry with backoff**: Retry transient failures (429, 500, 502, 503) with exponential backoff. Max 3 retries. Do not retry 4xx client errors.
- **OAuth 1.0a**: Discogs uses OAuth 1.0a (NOT 2.0). The implementation must handle the 3-legged flow: request token → user authorisation in browser → access token exchange. Store tokens securely in the config file.

---

## Article IX — Configuration Architecture

- **TOML format**, stored at platform-appropriate location:
  - Linux: `$XDG_CONFIG_HOME/vinylkit/config.toml` (fallback `~/.config/vinylkit/`)
  - macOS: `~/Library/Application Support/vinylkit/config.toml`
  - Windows: `%APPDATA%\vinylkit\config.toml`
- Use `platformdirs` for resolving config/cache/data directories.
- Read with `tomllib` (stdlib). Write with `tomli-w`.
- All settings MUST have sensible defaults. The tool must work with zero configuration beyond a Discogs token.
- Settings hierarchy: CLI flags > environment variables (`VINYLKIT_*`) > config file > defaults.
- Secrets (tokens) stored in the config file with a clear comment that it's user-local. Do not invent a keyring integration — keep it simple.

---

## Article X — Simplicity & Anti-Abstraction Gates

- **No class hierarchies deeper than 2 levels.** Prefer composition, protocols, and plain functions.
- **`@dataclass(slots=True, frozen=True)`** for all immutable data containers. Mutable only when mutation is the point.
- **No metaclasses, descriptors, or `__init_subclass__`** unless the plan explicitly justifies them.
- **No premature patterns**: No Factory, Strategy, Observer, Repository, or Unit of Work unless the spec demands the flexibility they provide. Document the justification.
- **No async unless proven necessary.** Start synchronous. The only candidate for async is batch HTTP requests — and even then, `concurrent.futures.ThreadPoolExecutor` may suffice.
- **Maximum file count per feature**: The plan must justify every source file beyond 5 for a single feature. Fewer files with clear responsibilities beats many files with thin abstractions.

---

## Article XI — Documentation

- **Google-style docstrings** on all public functions, classes, and modules.
- `README.md` contains: project purpose, installation (`uv`-based), quickstart usage, configuration reference, supported formats, and how to run tests.
- CLI `--help` text must be comprehensive — every command, every flag, with examples. This IS the user documentation.
- No Sphinx, no MkDocs, no ReadTheDocs. Docs live in-repo as Markdown and `--help` output.
- Architecture decisions that aren't obvious get a brief comment with rationale. Comments explain **why**, code explains **what**.

---

## Article XII — Version Control & CI

- **Conventional commits**: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- One logical change per commit. Each spec-kit task (T001, T002, ...) gets its own commit.
- `.gitignore` from day one: `__pycache__/`, `.venv/`, `*.egg-info/`, `dist/`, `.ruff_cache/`, `.pytest_cache/`, `.coverage`, `.mypy_cache/`, `*.pyc`.
- CI pipeline (GitHub Actions) runs on every push: `ruff check`, `ruff format --check`, `mypy --strict`, `pytest --cov` with coverage gate.
- Tagged releases follow SemVer. `__version__` lives in `pyproject.toml` — no `__version__` variable in source.

---

## Governance

- This constitution supersedes all other guidance, conventions, or AI-generated suggestions.
- The AI agent MUST flag any spec, plan, or implementation that violates these articles and halt until resolved.
- Amendments require a `docs:` commit with rationale.
- When two valid approaches exist, choose the one with fewer moving parts.