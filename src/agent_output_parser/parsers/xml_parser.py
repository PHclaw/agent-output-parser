"""XML parser — extract structured data from XML tags."""

import re
from typing import Any

from pydantic import BaseModel

from agent_output_parser.base import BaseParser, ParseResult


class XMLParser(BaseParser[dict[str, Any]]):
    """
    Extract data from XML-style tags in LLM output.
    
    Usage:
        parser = XMLParser(tag="result")
        result = parser.parse('''
            Here is the result:
            <result>
                <name>John</name>
                <age>30</age>
            </result>
        ''')
    """

    name = "xml-parser"
    description = "Extract data from XML tags"

    def __init__(self, tag: str | None = None, strict: bool = False):
        self.tag = tag
        self.strict = strict

    def parse(self, text: str) -> ParseResult[dict[str, Any]]:
        self.raw = text

        if self.tag:
            return self._parse_single_tag(text, self.tag)

        # Auto-detect all tags
        tags = self._detect_tags(text)
        if not tags:
            return ParseResult(
                success=False,
                error="No XML tags found",
                raw=text,
            )

        # Parse all found tags
        data = {}
        for tag_name in tags:
            tag_data = self._parse_single_tag(text, tag_name)
            if tag_data.success:
                data[tag_name] = tag_data.data

        if data:
            return ParseResult(success=True, data=data, raw=text)
        return ParseResult(success=False, error="Failed to parse tags", raw=text)

    def _detect_tags(self, text: str) -> list[str]:
        """Auto-detect XML tag names in text."""
        pattern = r"<(\w+)[^>]*>"
        return list(dict.fromkeys(re.findall(pattern, text)))

    def _parse_single_tag(self, text: str, tag: str) -> ParseResult[Any]:
        """Parse content of a specific tag."""
        pattern = rf"<{tag}[^>]*>(.*?)</{tag}>"
        match = re.search(pattern, text, re.DOTALL)

        if not match:
            if self.strict:
                return ParseResult(
                    success=False,
                    error=f"Tag <{tag}> not found",
                    raw=text,
                )
            return ParseResult(success=False, error="Tag not found", raw=text)

        content = match.group(1).strip()

        # Try to parse nested content
        nested = self._parse_nested(content)
        if nested is not None:
            return ParseResult(success=True, data=nested, raw=content)

        # Return as string
        return ParseResult(success=True, data=content, raw=content)

    def _parse_nested(self, content: str) -> dict[str, Any] | None:
        """Try to parse nested tags."""
        data = {}
        pattern = r"<(\w+)[^>]*>(.*?)</\1>"

        for match in re.finditer(pattern, content, re.DOTALL):
            tag_name = match.group(1)
            inner = match.group(2).strip()

            # Check for further nesting
            if re.search(r"<\w+", inner):
                nested = self._parse_nested(inner)
                if nested is not None:
                    data[tag_name] = nested
                else:
                    data[tag_name] = inner
            else:
                data[tag_name] = inner

        return data if data else None

    def extract_field(self, text: str, tag: str) -> str | None:
        """Extract a single field value."""
        result = self._parse_single_tag(text, tag)
        if result.success:
            return str(result.data)
        return None
