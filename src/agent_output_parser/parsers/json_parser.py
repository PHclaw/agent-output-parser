"""JSON parser with auto-fix for common LLM JSON issues."""

import json
import re
from typing import Any

from pydantic import BaseModel

from agent_output_parser.base import BaseParser, ParseResult


class JSONParser(BaseParser[dict[str, Any]]):
    """
    Parse JSON from LLM output — handles common issues.
    
    Features:
    - Extracts JSON from markdown code blocks
    - Fixes trailing commas
    - Handles single quotes
    - Extracts from mixed content
    
    Usage:
        parser = JSONParser()
        result = parser.parse(llm_output)
        if result.success:
            data = result.data
    """

    name = "json-parser"
    description = "Parse JSON from LLM output"

    strip_code_blocks: bool = True
    fix_common_errors: bool = True

    def parse(self, text: str) -> ParseResult[dict[str, Any]]:
        self.raw = text
        original = text

        # Step 1: Try direct parse first
        try:
            data = json.loads(text)
            return ParseResult(success=True, data=data, raw=text)
        except json.JSONDecodeError:
            pass

        # Step 2: Extract from code blocks
        if self.strip_code_blocks:
            text = self._extract_from_code_block(text)
            text = self._extract_json_from_text(text)

        # Step 3: Fix common errors
        if self.fix_common_errors:
            text = self._fix_json(text)

        # Step 4: Try again
        try:
            data = json.loads(text)
            return ParseResult(success=True, data=data, raw=text)
        except json.JSONDecodeError as e:
            return ParseResult(
                success=False,
                error=f"JSON decode error at pos {e.pos}: {e.msg}",
                raw=original,
                confidence=0.0,
            )

    def _extract_from_code_block(self, text: str) -> str:
        """Extract JSON from markdown ```json blocks."""
        patterns = [
            r"```json\s*(.+?)\s*```",
            r"```\s*({\s*.+})\s*```",
            r"```\s*(\[\s*.+?\])\s*```",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1)
        return text

    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON object/array from mixed text."""
        # Find first { or [ and last matching }
        for start_char in ["{", "["]:
            start = text.find(start_char)
            if start != -1:
                # Try to find the matching end
                end = self._find_matching_bracket(text, start)
                if end != -1:
                    return text[start : end + 1]
        return text

    def _find_matching_bracket(self, text: str, start: int) -> int:
        """Find the matching closing bracket."""
        stack = []
        in_string = False
        escape = False

        for i in range(start, len(text)):
            c = text[i]

            if escape:
                escape = False
                continue

            if c == "\\":
                escape = True
                continue

            if c == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if c in "{[":
                stack.append(c)
            elif c in "}]":
                if not stack:
                    return -1
                expected = "{" if stack[-1] == "{" else "["
                if c != expected:
                    return -1
                stack.pop()
                if not stack:
                    return i

        return -1

    def _fix_json(self, text: str) -> str:
        """Fix common JSON errors from LLM output."""
        # Remove trailing commas
        text = re.sub(r",(\s*[}\]])", r"\1", text)

        # Single quotes to double quotes (simple cases)
        # Only within JSON structures
        text = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', text)

        # Remove comments (// and /* */)
        text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

        # Fix unquoted keys (basic cases like {key: value})
        text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', text)

        # Remove control characters
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)

        return text.strip()
