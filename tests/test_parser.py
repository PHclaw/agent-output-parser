"""Tests for output parser."""

import pytest
from pydantic import BaseModel

from agent_output_parser import (
    JSONParser,
    XMLParser,
    MarkdownParser,
    PydanticParser,
    RegexParser,
    CompletenessChecker,
)
from agent_output_parser.base import ParseResult


class TestJSONParser:
    def test_parse_clean_json(self) -> None:
        parser = JSONParser()
        result = parser.parse('{"name": "Alice", "age": 30}')
        assert result.success
        assert result.data == {"name": "Alice", "age": 30}

    def test_parse_from_code_block(self) -> None:
        parser = JSONParser()
        result = parser.parse('```json\n{"name": "Bob"}\n```')
        assert result.success
        assert result.data["name"] == "Bob"

    def test_fix_trailing_comma(self) -> None:
        parser = JSONParser()
        result = parser.parse('{"a": 1, "b": 2,}')
        assert result.success

    def test_fix_single_quotes(self) -> None:
        parser = JSONParser()
        result = parser.parse("{'name': 'Alice'}")
        assert result.success

    def test_extract_from_mixed_text(self) -> None:
        parser = JSONParser()
        result = parser.parse('Answer: {"key": "value"} - done')
        assert result.success
        assert result.data["key"] == "value"

    def test_parse_invalid(self) -> None:
        parser = JSONParser()
        result = parser.parse("not json at all")
        assert not result.success
        assert result.error is not None


class TestXMLParser:
    def test_parse_single_tag(self) -> None:
        parser = XMLParser(tag="result")
        result = parser.parse("<result>hello</result>")
        assert result.success
        assert result.data == "hello"

    def test_parse_nested(self) -> None:
        parser = XMLParser(tag="user")
        result = parser.parse("<user><name>John</name><age>30</age></user>")
        assert result.success
        assert result.data["name"] == "John"
        assert result.data["age"] == "30"

    def test_not_found(self) -> None:
        parser = XMLParser(tag="missing")
        result = parser.parse("<other>text</other>")
        assert not result.success

    def test_extract_field(self) -> None:
        parser = XMLParser()
        value = parser.extract_field("<name>Alice</name>", "name")
        assert value == "Alice"


class TestMarkdownParser:
    def test_parse_simple_table(self) -> None:
        parser = MarkdownParser()
        text = """
| Name  | Age |
|-------|-----|
| John  | 30  |
| Mary  | 25  |
"""
        result = parser.parse(text)
        assert result.success
        assert len(result.data) == 2
        assert result.data[0]["Name"] == "John"
        assert result.data[1]["Age"] == "25"

    def test_no_table(self) -> None:
        parser = MarkdownParser()
        result = parser.parse("No table here")
        assert not result.success


class UserModel(BaseModel):
    name: str
    age: int
    email: str | None = None


class TestPydanticParser:
    def test_parse_kv_text(self) -> None:
        parser = PydanticParser(UserModel)
        result = parser.parse("Name: Alice\nAge: 28\nEmail: alice@example.com")
        assert result.success
        assert result.data.name == "Alice"
        assert result.data.age == 28
        assert result.data.email == "alice@example.com"

    def test_parse_json(self) -> None:
        parser = PydanticParser(UserModel)
        result = parser.parse('{"name": "Bob", "age": 25}')
        assert result.success
        assert result.data.name == "Bob"

    def test_parse_invalid(self) -> None:
        parser = PydanticParser(UserModel)
        result = parser.parse("No data here")
        assert not result.success

    def test_type_coercion(self) -> None:
        parser = PydanticParser(UserModel)
        result = parser.parse("Name: Charlie\nAge: twenty")
        assert not result.success


class TestRegexParser:
    def test_basic_patterns(self) -> None:
        parser = RegexParser(patterns={
            "email": r"(\S+@\S+)",
            "age": r"Age:\s*(\d+)",
        })
        result = parser.parse("Email: john@example.com, Age: 30")
        assert result.success
        assert result.data["email"] == "john@example.com"
        assert result.data["age"] == "30"

    def test_no_match(self) -> None:
        parser = RegexParser(patterns={"x": r"(\d+)"})
        result = parser.parse("no numbers here")
        assert not result.success


class TestCompletenessChecker:
    def test_all_found(self) -> None:
        checker = CompletenessChecker(required=["name", "age"])
        result = checker.check('{"name": "Alice", "age": 30}')
        assert result.is_complete
        assert result.score == 1.0

    def test_missing_required(self) -> None:
        checker = CompletenessChecker(required=["name", "age", "email"])
        result = checker.check('{"name": "Bob", "age": 25}')
        assert not result.is_complete
        assert "email" in result.missing_required

    def test_optional_missing_ok(self) -> None:
        checker = CompletenessChecker(
            required=["name"],
            optional=["phone"]
        )
        result = checker.check('{"name": "Charlie"}')
        assert result.is_complete
        assert result.score == 0.5  # 1/2 fields

    def test_kv_text(self) -> None:
        checker = CompletenessChecker(required=["name", "age"])
        result = checker.check("Name: Dana\nAge: 40")
        assert result.is_complete
