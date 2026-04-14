import io
from enum import Enum

import pytest
from pydantic_core import PydanticUndefined
from rich.console import Console

from wizdantic.prompts import (
    BoolPrompt,
    DictPrompt,
    EnumPrompt,
    ListPrompt,
    LiteralPrompt,
    SecretPrompt,
    SetPrompt,
    TuplePrompt,
    ValuePrompt,
    apply_hint,
    type_name,
    validated_parser,
)


@pytest.fixture
def console():
    """A console that writes to an in-memory buffer so tests stay silent."""
    return Console(file=io.StringIO(), force_terminal=True)


class TestApplyHint:
    def test_with_hint(self):
        result = apply_hint("Planet Name", "name of the planet")
        assert "Planet Name" in result
        assert "name of the planet" in result
        assert "[dim]" in result

    def test_with_none_hint(self):
        """When hint is None, the label is returned unchanged."""
        label = "Planet Name"
        result = apply_hint(label, None)
        assert result == label

    def test_hint_appears_in_parentheses(self):
        result = apply_hint("Label", "some hint")
        assert "(some hint)" in result

    def test_is_opt_appends_empty_for_none(self):
        result = apply_hint("Label", None, is_opt=True)
        assert "empty for None" in result

    def test_hint_and_is_opt_combined(self):
        result = apply_hint("Label", "format: JSON", is_opt=True)
        assert "format: JSON" in result
        assert "empty for None" in result


class TestTypeName:
    def test_named_type(self):
        assert type_name(int) == "int"
        assert type_name(str) == "str"

    def test_unnamed_annotation(self):
        """Falls back to str() for annotations without __name__."""
        result = type_name(list[int])
        assert "list" in result


class TestValidatedParser:
    def test_wraps_parser_with_validation(self):
        def raw_parser(s: str) -> int:
            return int(s)

        wrapped = validated_parser(raw_parser, int)
        assert wrapped("42") == 42

    def test_raises_on_validation_failure(self):
        def raw_parser(s: str) -> str:
            return s

        from typing import Annotated

        from pydantic import Field

        wrapped = validated_parser(raw_parser, Annotated[int, Field(ge=10)])
        with pytest.raises(ValueError, match="greater than"):
            wrapped("5")


class TestBoolPrompt:
    def test_non_optional_true(self, mocker, console):
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)
        prompt = BoolPrompt(console, "Armed", PydanticUndefined, True, False)
        assert prompt.prompt() is True

    def test_non_optional_false(self, mocker, console):
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=False)
        prompt = BoolPrompt(console, "Armed", PydanticUndefined, True, False)
        assert prompt.prompt() is False

    def test_optional_empty_returns_none(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")
        prompt = BoolPrompt(console, "Armed", None, False, True)
        assert prompt.prompt() is None

    def test_optional_y_returns_true(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="y")
        prompt = BoolPrompt(console, "Armed", None, False, True)
        assert prompt.prompt() is True

    def test_optional_n_returns_false(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="n")
        prompt = BoolPrompt(console, "Armed", None, False, True)
        assert prompt.prompt() is False

    def test_optional_invalid_then_valid(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["maybe", "y"])
        prompt = BoolPrompt(console, "Armed", None, False, True)
        assert prompt.prompt() is True
        assert "Enter y or n" in console.file.getvalue()


class TestEnumPrompt:
    class Side(str, Enum):
        LIGHT = "light"
        DARK = "dark"

    def test_select_by_index(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="2")
        prompt = EnumPrompt(console, "Side", PydanticUndefined, True, False, enum_cls=self.Side)
        assert prompt.prompt() == self.Side.DARK

    def test_select_by_value(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="light")
        prompt = EnumPrompt(console, "Side", PydanticUndefined, True, False, enum_cls=self.Side)
        assert prompt.prompt() == self.Side.LIGHT

    def test_optional_empty_returns_none(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")
        prompt = EnumPrompt(console, "Side", None, False, True, enum_cls=self.Side)
        assert prompt.prompt() is None

    def test_invalid_retries(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["warlock", "dark"])
        prompt = EnumPrompt(console, "Side", PydanticUndefined, True, False, enum_cls=self.Side)
        assert prompt.prompt() == self.Side.DARK
        assert "Invalid choice" in console.file.getvalue()


class TestLiteralPrompt:
    def test_select_by_index(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="1")
        prompt = LiteralPrompt(console, "Mode", PydanticUndefined, True, False, values=("fast", "slow"))
        assert prompt.prompt() == "fast"

    def test_select_by_value(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="slow")
        prompt = LiteralPrompt(console, "Mode", PydanticUndefined, True, False, values=("fast", "slow"))
        assert prompt.prompt() == "slow"

    def test_optional_empty_returns_none(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")
        prompt = LiteralPrompt(console, "Mode", None, False, True, values=("fast", "slow"))
        assert prompt.prompt() is None


class TestSecretPrompt:
    def test_collects_secret(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="runemark")
        prompt = SecretPrompt(
            console,
            "Code",
            PydanticUndefined,
            True,
            False,
            annotation=str,
            hint=None,
        )
        assert prompt.prompt() == "runemark"

    def test_optional_empty_returns_none(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")
        prompt = SecretPrompt(console, "Code", None, False, True, annotation=str, hint=None)
        assert prompt.prompt() is None

    def test_required_empty_retries(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["", "secret"])
        prompt = SecretPrompt(
            console,
            "Code",
            PydanticUndefined,
            True,
            False,
            annotation=str,
            hint=None,
        )
        assert prompt.prompt() == "secret"
        assert "required" in console.file.getvalue()


class TestValuePrompt:
    def test_collects_string(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="Theron")
        prompt = ValuePrompt(console, "Name", PydanticUndefined, True, False, annotation=str)
        assert prompt.prompt() == "Theron"

    def test_collects_int(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="42")
        prompt = ValuePrompt(console, "Count", PydanticUndefined, True, False, annotation=int)
        assert prompt.prompt() == 42

    def test_invalid_int_retries(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["abc", "42"])
        prompt = ValuePrompt(console, "Count", PydanticUndefined, True, False, annotation=int)
        assert prompt.prompt() == 42
        assert "Invalid" in console.file.getvalue()

    def test_optional_empty_returns_none(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")
        prompt = ValuePrompt(console, "Name", None, False, True, annotation=str)
        assert prompt.prompt() is None

    def test_required_empty_retries(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["", "Theron"])
        prompt = ValuePrompt(console, "Name", PydanticUndefined, True, False, annotation=str)
        assert prompt.prompt() == "Theron"
        assert "required" in console.file.getvalue()

    def test_custom_parser(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="hello")
        prompt = ValuePrompt(
            console,
            "Name",
            PydanticUndefined,
            True,
            False,
            annotation=str,
            parser=str.upper,
        )
        assert prompt.prompt() == "HELLO"


class TestListPrompt:
    def test_json_array(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value='["a", "b"]')
        prompt = ListPrompt(console, "Items", [], False, False, item_type=str)
        assert prompt.prompt() == ["a", "b"]

    def test_csv_input(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="a, b, c")
        prompt = ListPrompt(console, "Items", [], False, False, item_type=str)
        assert prompt.prompt() == ["a", "b", "c"]

    def test_empty_non_required_returns_empty(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")
        prompt = ListPrompt(console, "Items", [], False, False, item_type=str)
        assert prompt.prompt() == []


class TestSetPrompt:
    def test_csv_input(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="arcane, mystic")
        prompt = SetPrompt(console, "Factions", set(), False, False, item_type=str)
        assert prompt.prompt() == {"arcane", "mystic"}

    def test_duplicates_rejected(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["arcane, arcane", "arcane, mystic"],
        )
        prompt = SetPrompt(console, "Factions", set(), False, False, item_type=str)
        assert prompt.prompt() == {"arcane", "mystic"}
        assert "Duplicate" in console.file.getvalue()


class TestDictPrompt:
    def test_json_object(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            return_value='{"realm": "embervault"}',
        )
        prompt = DictPrompt(console, "Index", {}, False, False, key_type=str, value_type=str)
        assert prompt.prompt() == {"realm": "embervault"}

    def test_kv_notation(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            return_value="realm:embervault, domain:shadowfell",
        )
        prompt = DictPrompt(console, "Index", {}, False, False, key_type=str, value_type=str)
        assert prompt.prompt() == {"realm": "embervault", "domain": "shadowfell"}

    def test_empty_non_required_returns_empty(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")
        prompt = DictPrompt(console, "Index", {}, False, False, key_type=str, value_type=str)
        assert prompt.prompt() == {}


class TestTuplePrompt:
    def test_homogeneous_json(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="[1.5, 2.5]")
        prompt = TuplePrompt(
            console,
            "Coords",
            PydanticUndefined,
            True,
            False,
            item_types=[float],
            is_homogeneous=True,
        )
        assert prompt.prompt() == pytest.approx((1.5, 2.5))

    def test_fixed_json(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value='["Sector 7", 42]')
        prompt = TuplePrompt(
            console,
            "Point",
            PydanticUndefined,
            True,
            False,
            item_types=[str, int],
            is_homogeneous=False,
        )
        assert prompt.prompt() == ("Sector 7", 42)
