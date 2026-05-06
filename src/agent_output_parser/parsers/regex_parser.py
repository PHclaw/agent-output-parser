"""Regex-based parser for structured patterns."""

import re
from typing import Any

from pydantic import BaseModel

from agent_output_parser.base import BaseParser, ParseResult


class RegexParser(BaseParser[dict[str, Any]]):
    """
    Parse LLM output using regex patterns.
    
    Usage:
        parser = RegexParser(
            patterns={
                "email": r"Email:\s*(\S+@\S+)",
                "phone": r"Phone:\s*(\d{3}-\d{4})",
            }
        )
        result = parser.parse("Email: john@example.com, Phone: 123-4567")
    """

    name = "regex-parser"
    description = "Parse structured patterns with regex"

    def __init__(self, patterns: dict[str, str] | None = None):
        self.patterns = patterns or {}

    def add_pattern(self, name: str, pattern: str) -> None:
        """Add a regex pattern at runtime."""
        self.patterns[name] = pattern

    def parse(self, text: str) -> ParseResult[dict[str, Any]]:
        self.raw = text
        data = {}

        for name, pattern in self.patterns.items():
            match = re.search(pattern, text, re.DOTALL)
            if match:
                if match.groups():
                    data[name] = match.group(1)
                else:
                    data[name] = match.group(0)

        if data:
            return ParseResult(success=True, data=data, raw=text)
        return ParseResult(
            success=False,
            error="No patterns matched",
            raw=text,
        )

    def extract_first(self, pattern: str, text: str) -> str | None:
        """Extract first match of a pattern."""
        match = re.search(pattern, text)
        if match:
            return match.group(1) if match.groups() else match.group(0)
        return None

    def extract_all(self, pattern: str, text: str) -> list[str]:
        """Extract all matches of a pattern."""
        return re.findall(pattern, text)
