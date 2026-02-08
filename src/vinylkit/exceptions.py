from __future__ import annotations


class VinylkitError(Exception):
    """Base exception for all vinylkit errors."""


class ConfigError(VinylkitError):
    """Raised when there is an issue with the configuration."""


class AuthError(VinylkitError):
    """Raised when authentication fails."""


class DiscogsAPIError(VinylkitError):
    """Raised when the Discogs API returns an error."""


class TaggingError(VinylkitError):
    """Raised when there is an issue tagging an audio file."""


class FileOperationError(VinylkitError):
    """Raised when a file operation (move, rename) fails."""


class ValidationError(VinylkitError):
    """Raised when data validation fails."""
