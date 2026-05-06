"""Errors for agent-output-parser."""


class ParseError(Exception):
    """Raised when parsing fails."""

    pass


class ValidationError(Exception):
    """Raised when parsed data fails validation."""

    pass


class ExtractionError(Exception):
    """Raised when extracting content from text fails."""

    pass
