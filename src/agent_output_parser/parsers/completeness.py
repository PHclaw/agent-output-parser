"""Completeness checker — verify LLM output has all required fields."""

import json
import re
from typing import Any

from agent_output_parser.base import ParseResult
from agent_output_parser.parsers.json_parser import JSONParser


class CompletenessChecker:
    """
    Check if LLM output contains all required fields.
    
    Usage:
        checker = CompletenessChecker(required=["name", "age", "email"])
        result = checker.check("Name: John\nAge: 30")  # missing email
        print(result.missing)  # ["email"]
        print(result.score)     # 0.667
    """

    def __init__(self, required: list[str] | None = None, optional: list[str] | None = None):
        self.required = required or []
        self.optional = optional or []

    def check(self, text: str) -> "CheckResult":
        """
        Check text for required and optional fields.
        Returns CheckResult with found/missing fields and completeness score.
        """
        found = self._extract_fields(text)
        missing_required = [f for f in self.required if f not in found]
        missing_optional = [f for f in self.optional if f not in found]
        found_all = self.required + self.optional
        found_count = sum(1 for f in found_all if f in found)

        score = found_count / len(found_all) if found_all else 1.0

        return CheckResult(
            found=found,
            missing_required=missing_required,
            missing_optional=missing_optional,
            score=score,
            is_complete=len(missing_required) == 0,
        )

    def _extract_fields(self, text: str) -> set[str]:
        """Extract field names from text."""
        fields = set()

        # Try JSON
        parser = JSONParser()
        result = parser.parse(text)
        if result.success and result.data:
            fields.update(result.data.keys())
            return fields

        # Try key-value pattern: "Field Name: value"
        pattern = r"^([A-Za-z][A-Za-z0-9\s]*?)[\-:=]\s*"
        for line in text.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                name = match.group(1).strip().lower().replace(" ", "_")
                fields.add(name)

        return fields

    def check_json(self, json_text: str) -> "CheckResult":
        """Check a JSON string directly."""
        parser = JSONParser()
        result = parser.parse(json_text)
        if not result.success:
            return CheckResult(
                found=set(),
                missing_required=self.required.copy(),
                missing_optional=self.optional.copy(),
                score=0.0,
                is_complete=False,
                error=result.error,
            )

        found = set(result.data.keys()) if result.data else set()
        missing_required = [f for f in self.required if f not in found]
        missing_optional = [f for f in self.optional if f not in found]
        found_all = self.required + self.optional
        found_count = sum(1 for f in found_all if f in found)
        score = found_count / len(found_all) if found_all else 1.0

        return CheckResult(
            found=found,
            missing_required=missing_required,
            missing_optional=missing_optional,
            score=score,
            is_complete=len(missing_required) == 0,
        )


class CheckResult:
    """Result of completeness check."""

    def __init__(
        self,
        found: set[str],
        missing_required: list[str],
        missing_optional: list[str],
        score: float,
        is_complete: bool,
        error: str | None = None,
    ):
        self.found = found
        self.missing_required = missing_required
        self.missing_optional = missing_optional
        self.score = score  # 0.0 to 1.0
        self.is_complete = is_complete
        self.error = error

    def __repr__(self) -> str:
        if self.error:
            return f"CheckResult(error={self.error!r})"
        pct = int(self.score * 100)
        status = "✅" if self.is_complete else "❌"
        return f"CheckResult({status} {pct}% complete, missing={self.missing_required})"
