from __future__ import annotations


class FEACopilotError(Exception):
    """Base class for recoverable application errors."""


class PromptParseError(FEACopilotError):
    """Raised when a prompt cannot be converted into a supported simulation."""


class SpecValidationError(FEACopilotError):
    """Raised when a parsed or supplied simulation spec is invalid."""
