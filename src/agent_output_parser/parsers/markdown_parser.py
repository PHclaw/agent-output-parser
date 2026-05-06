"""Markdown table and structured output parser."""

import re
from typing import Any

from pydantic import BaseModel

from agent_output_parser.base import BaseParser, ParseResult


class MarkdownParser(BaseParser[list[dict[str, Any]]]):
    """
    Parse markdown tables and structured markdown into data.
    
    Usage:
        parser = MarkdownParser()
        result = parser.parse('''
            | Name  | Age |
            |-------|-----|
            | John  | 30  |
            | Mary  | 25  |
        ''')
        # → [{"Name": "John", "Age": "30"}, {"Name": "Mary", "Age": "25"}]
    """

    name = "markdown-parser"
    description = "Parse markdown tables into structured data"

    def parse(self, text: str) -> ParseResult[list[dict[str, Any]]]:
        self.raw = text

        tables = self._extract_tables(text)
        if not tables:
            return ParseResult(
                success=False,
                error="No markdown tables found",
                raw=text,
            )

        # Parse first table
        parsed = self._parse_table(tables[0])
        return ParseResult(success=True, data=parsed, raw=text)

    def _extract_tables(self, text: str) -> list[str]:
        """Extract all markdown tables from text."""
        tables = []
        lines = text.split("\n")
        in_table = False
        current_table: list[str] = []

        for line in lines:
            line = line.strip()
            if "|" in line:
                in_table = True
                current_table.append(line)
            else:
                if in_table and current_table:
                    tables.append("\n".join(current_table))
                    current_table = []
                in_table = False

        if current_table:
            tables.append("\n".join(current_table))

        return tables

    def _parse_table(self, table: str) -> list[dict[str, Any]]:
        """Parse a single markdown table."""
        lines = [l.strip() for l in table.split("\n") if l.strip() and "|" in l]

        # Skip separator line
        lines = [l for l in lines if not re.match(r"\|[\s\-:|]+\|", l)]

        if len(lines) < 2:
            return []

        # Parse headers
        headers = [h.strip() for h in lines[0].split("|") if h.strip()]

        # Parse rows
        rows = []
        for line in lines[1:]:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) == len(headers):
                row = dict(zip(headers, cells))
                rows.append(row)

        return rows

    def parse_all_tables(self, text: str) -> list[list[dict[str, Any]]]:
        """Parse all tables in text."""
        tables = self._extract_tables(text)
        return [self._parse_table(t) for t in tables]
