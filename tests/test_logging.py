from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

from loguru import logger

from vinylkit.cli import cli, initialise_logging
from vinylkit.config import load_config, save_config
from vinylkit.models import AppConfig

if TYPE_CHECKING:
    import pytest
    from click.testing import CliRunner


# ---------------------------------------------------------------------------
# initialise_logging() sink tests
# ---------------------------------------------------------------------------


class TestInitialiseLogging:
    """Verify that initialise_logging configures the expected sinks."""

    def test_default_config_creates_two_sinks(self, tmp_path: Path) -> None:
        """Default config: one console sink + one file sink."""
        log_file = tmp_path / "vinylkit.log"
        config = AppConfig(library_root=tmp_path, log_file=log_file)

        logger.remove()
        initialise_logging(config)

        # Two sinks: stderr + file
        handlers = logger._core.handlers  # type: ignore[attr-defined]
        assert len(handlers) == 2

        logger.remove()  # clean up

    def test_file_sink_disabled(self, tmp_path: Path) -> None:
        """With log_to_file=False, only the console sink is created."""
        config = AppConfig(library_root=tmp_path, log_to_file=False)

        logger.remove()
        initialise_logging(config)

        handlers = logger._core.handlers  # type: ignore[attr-defined]
        assert len(handlers) == 1

        logger.remove()

    def test_custom_log_file_path(self, tmp_path: Path) -> None:
        """A custom log_file path is used when set."""
        custom_path = tmp_path / "custom" / "my.log"
        config = AppConfig(library_root=tmp_path, log_file=custom_path)

        logger.remove()
        initialise_logging(config)

        # Write a message and check the file exists
        logger.info("test message")
        assert custom_path.exists()
        assert "test message" in custom_path.read_text(encoding="utf-8")

        logger.remove()

    def test_default_log_path_uses_platformdirs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When log_file is None, the default path uses platformdirs."""
        fake_log_dir = tmp_path / "logdir"
        monkeypatch.setattr(
            "vinylkit.cli.user_log_dir",
            lambda *_args, **_kwargs: str(fake_log_dir),
        )
        config = AppConfig(library_root=tmp_path, log_file=None, log_to_file=True)

        logger.remove()
        initialise_logging(config)

        logger.info("platformdirs test")
        expected = fake_log_dir / "vinylkit.log"
        assert expected.exists()

        logger.remove()


# ---------------------------------------------------------------------------
# Config round-trip tests
# ---------------------------------------------------------------------------


class TestLoggingConfigRoundTrip:
    """Verify that logging settings survive save_config -> load_config."""

    def test_roundtrip_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = tmp_path / "config.toml"
        monkeypatch.setenv("VINYLKIT_CONFIG", str(config_path))

        original = AppConfig(library_root=tmp_path)
        save_config(original)
        loaded = load_config()

        assert loaded.log_level == "INFO"
        assert loaded.log_to_file is True
        assert loaded.log_file is None
        assert loaded.log_rotation == "5 MB"
        assert loaded.log_retention == 5

    def test_roundtrip_custom_values(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = tmp_path / "config.toml"
        monkeypatch.setenv("VINYLKIT_CONFIG", str(config_path))

        custom_log = tmp_path / "custom.log"
        original = AppConfig(
            library_root=tmp_path,
            log_level="DEBUG",
            log_to_file=False,
            log_file=custom_log,
            log_rotation="10 MB",
            log_retention=3,
        )
        save_config(original)
        loaded = load_config()

        assert loaded.log_level == "DEBUG"
        assert loaded.log_to_file is False
        assert loaded.log_file == custom_log
        assert loaded.log_rotation == "10 MB"
        assert loaded.log_retention == 3


# ---------------------------------------------------------------------------
# CLI config set / show tests
# ---------------------------------------------------------------------------


class TestLoggingCLI:
    """Test CLI interaction with logging config keys."""

    def test_config_set_log_level(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["config", "set", "log_level", "DEBUG"])
        assert result.exit_code == 0
        assert "log_level" in result.output

        result = runner.invoke(cli, ["config", "show"])
        assert "DEBUG" in result.output

    def test_config_set_log_to_file_false(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["config", "set", "log_to_file", "false"])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["config", "show"])
        assert "False" in result.output

    def test_config_set_log_file(self, runner: CliRunner, tmp_path: Path) -> None:
        log_path = tmp_path / "custom.log"
        result = runner.invoke(cli, ["config", "set", "log_file", str(log_path)])
        assert result.exit_code == 0

    def test_config_set_log_rotation(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["config", "set", "log_rotation", "10 MB"])
        assert result.exit_code == 0

    def test_config_set_log_retention(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["config", "set", "log_retention", "3"])
        assert result.exit_code == 0

    def test_config_show_logging_section(self, runner: CliRunner) -> None:
        """config show displays a Logging section with all 5 settings."""
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert "Logging" in result.output
        assert "log_level" in result.output
        assert "log_to_file" in result.output
        assert "log_file" in result.output
        assert "log_rotation" in result.output
        assert "log_retention" in result.output
