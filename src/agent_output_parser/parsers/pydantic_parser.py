"""Pydantic model parser — parse text into Pydantic models."""

from typing import Any, TypeVar, Type

from pydantic import BaseModel, ValidationError

from agent_output_parser.base import BaseParser, ParseResult
from agent_output_parser.parsers.json_parser import JSONParser
from agent_output_parser.errors import ParseError


T = TypeVar("T", bound=BaseModel)


class PydanticParser(BaseParser[T]):
    """
    Parse LLM output directly into Pydantic models.
    
    Usage:
        from pydantic import BaseModel
        from agent_output_parser import PydanticParser
        
        class User(BaseModel):
            name: str
            age: int
            email: str | None = None
        
        parser = PydanticParser(User)
        result = parser.parse('''
            Here's the user info:
            Name: John
            Age: 30
            Email: john@example.com
        ''')
    """

    name = "pydantic-parser"
    description = "Parse LLM output into Pydantic models"

    def __init__(
        self,
        model: Type[T],
        json_parser: JSONParser | None = None,
        strict: bool = False,
    ):
        self.model = model
        self.json_parser = json_parser or JSONParser()
        self.strict = strict

    def parse(self, text: str) -> ParseResult[T]:
        self.raw = text

        # Try 1: Direct Pydantic model parsing
        try:
            data = self.model.model_validate_json(text)
            return ParseResult(success=True, data=data, raw=text)
        except (ValidationError, ValueError):
            pass

        # Try 2: Extract JSON from text and parse
        json_result = self.json_parser.parse(text)
        if json_result.success and json_result.data:
            try:
                # Handle both dict and raw JSON string
                data_dict = json_result.data
                if isinstance(data_dict, str):
                    data_dict = self.json_parser.parse(data_dict).data
                if data_dict:
                    model_instance = self.model.model_validate(data_dict)
                    return ParseResult(
                        success=True,
                        data=model_instance,
                        raw=json_result.raw,
                        confidence=0.9,
                    )
            except ValidationError as e:
                return ParseResult(
                    success=False,
                    error=f"Pydantic validation failed: {e}",
                    raw=text,
                    confidence=0.5,
                )

        # Try 3: Key-value extraction for non-JSON text
        kv_data = self._extract_key_values(text)
        if kv_data:
            try:
                model_instance = self.model.model_validate(kv_data)
                return ParseResult(
                    success=True,
                    data=model_instance,
                    raw=text,
                    confidence=0.7,
                )
            except ValidationError as e:
                return ParseResult(
                    success=False,
                    error=f"Key-value validation failed: {e}",
                    raw=text,
                    confidence=0.3,
                )

        return ParseResult(
            success=False,
            error="Failed to parse into Pydantic model",
            raw=text,
            confidence=0.0,
        )

    def _extract_key_values(self, text: str) -> dict[str, Any]:
        """Extract key: value pairs from plain text."""
        import re

        data: dict[str, Any] = {}
        lines = text.split("\n")

        for line in lines:
            # Match "Key: Value" or "Key - Value" or "Key = Value"
            match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_\s]*?)[\-:=]\s*(.+)$", line.strip())
            if match:
                key = match.group(1).strip().lower().replace(" ", "_")
                value = match.group(2).strip().rstrip(".,")
                data[key] = self._coerce_value(value)

        return data

    def _coerce_value(self, value: str) -> Any:
        """Try to coerce string value to proper type."""
        import re

        value = value.strip()

        # None/null
        if value.lower() in ("none", "null", "n/a", "-"):
            return None

        # Bool
        if value.lower() in ("true", "yes", "correct"):
            return True
        if value.lower() in ("false", "no", "incorrect"):
            return False

        # Number
        if re.match(r"^-?\d+$", value):
            return int(value)
        if re.match(r"^-?\d+\.\d+$", value):
            return float(value)

        # List (comma-separated)
        if "," in value and not value.startswith("["):
            items = [i.strip() for i in value.split(",")]
            try:
                return [int(i) if i.isdigit() else i for i in items]
            except ValueError:
                pass

        return value
