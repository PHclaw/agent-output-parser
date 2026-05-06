"""Base parser class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeVar, Generic

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


@dataclass
class ParseResult(Generic[T]):
    """Result of parsing an LLM output."""

    success: bool
    data: T | None = None
    raw: str = ""
    error: str | None = None
    confidence: float = 1.0  # 0.0 to 1.0

    def __repr__(self) -> str:
        if self.success:
            return f"ParseResult(success=True, data={self.data})"
        return f"ParseResult(success=False, error={self.error!r})"


class BaseParser(ABC, Generic[T]):
    """Base class for all output parsers."""

    name: str
    description: str

    @abstractmethod
    def parse(self, text: str) -> ParseResult[T]:
        """
        Parse text into structured data.
        Returns ParseResult with success/failure and parsed data.
        """
        ...

    def parse_or_raise(self, text: str) -> T:
        """
        Parse text, raise ParseError on failure.
        """
        from agent_output_parser.errors import ParseError

        result = self.parse(text)
        if not result.success:
            raise ParseError(result.error or "Parse failed")
        return result.data

    def try_parse(self, text: str, default: T | None = None) -> T | None:
        """
        Parse text, return default on failure.
        """
        result = self.parse(text)
        if result.success:
            return result.data
        return default
