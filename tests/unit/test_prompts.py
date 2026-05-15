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
    prompt_picker,
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

    def test_required_empty_retries(self, mocker, console):
        """ListPrompt required empty input shows error and retries."""
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["", "a, b"])
        prompt = ListPrompt(console, "Items", PydanticUndefined, True, False, item_type=str)
        assert prompt.prompt() == ["a", "b"]
        assert "required" in console.file.getvalue()


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


class TestPromptPicker:
    def test_uses_description_as_label(self, mocker, console):
        """prompt_picker uses ctx.description as the prompt label when provided."""
        from wizdantic.lore import PickerContext
        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="crimson")
        ctx = PickerContext(name="color", description="Favourite colour", default=None, hint=None)
        result = prompt_picker(ctx)
        assert result == "crimson"
        label_arg = mock_ask.call_args[0][0]
        assert "Favourite colour" in label_arg

    def test_falls_back_to_titleized_name(self, mocker, console):
        """prompt_picker titleizes ctx.name when description is None."""
        from wizdantic.lore import PickerContext
        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="blue")
        ctx = PickerContext(name="bg_color", description=None, default=None, hint=None)
        result = prompt_picker(ctx)
        assert result == "blue"
        label_arg = mock_ask.call_args[0][0]
        assert "Bg Color" in label_arg

    def test_applies_hint_when_present(self, mocker, console):
        """prompt_picker includes the hint in the label when ctx.hint is set."""
        from wizdantic.lore import PickerContext
        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="#ff0000")
        ctx = PickerContext(name="color", description="Color", default=None, hint="e.g. #rrggbb")
        prompt_picker(ctx)
        label_arg = mock_ask.call_args[0][0]
        assert "e.g. #rrggbb" in label_arg

    def test_passes_default_as_kwarg(self, mocker, console):
        """prompt_picker passes ctx.default as the Prompt default when set."""
        from wizdantic.lore import PickerContext
        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="#aabbcc")
        ctx = PickerContext(name="color", description="Color", default="#ffffff", hint=None)
        prompt_picker(ctx)
        call_kwargs = mock_ask.call_args[1]
        assert call_kwargs.get("default") == "#ffffff"


class TestBoolPromptOptionalWithDefault:
    def test_optional_with_true_default_prefills_y(self, mocker, console):
        """BoolPrompt optional with default=True uses 'y' as the pre-filled value."""
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="y")
        prompt = BoolPrompt(console, "Active", True, False, True)
        assert prompt.prompt() is True

    def test_optional_with_false_default_prefills_n(self, mocker, console):
        """BoolPrompt optional with default=False uses 'n' as the pre-filled value."""
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="n")
        prompt = BoolPrompt(console, "Active", False, False, True)
        assert prompt.prompt() is False


class TestSecretPromptParserAndValidation:
    def test_parser_error_retries(self, mocker, console):
        """When the parser raises, SecretPrompt shows an error and retries."""
        call_count = 0

        def strict_parser(raw: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("bad input")
            return raw.upper()

        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["bad", "good"])
        prompt = SecretPrompt(
            console, "Code", PydanticUndefined, True, False, annotation=str, parser=strict_parser
        )
        assert prompt.prompt() == "GOOD"
        assert "Invalid" in console.file.getvalue()

    def test_type_adapter_validation_error_retries(self, mocker, console):
        """SecretPrompt retries when TypeAdapter validation fails."""
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["notanint", "42"])
        prompt = SecretPrompt(
            console, "Level", PydanticUndefined, True, False, annotation=int, hint=None
        )
        assert prompt.prompt() == 42
        assert "Invalid" in console.file.getvalue()


class TestListPromptParserError:
    def test_parser_error_retries(self, mocker, console):
        """When the parser raises, ListPrompt shows an error and retries."""
        call_count = 0

        def strict_parser(raw: str) -> list[str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("bad input")
            return raw.split(",")

        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["bad", "a,b"])
        prompt = ListPrompt(
            console, "Items", [], False, False, item_type=str, parser=strict_parser
        )
        result = prompt.prompt()
        assert result == ["a", "b"]
        assert "Invalid" in console.file.getvalue()


class TestTuplePromptGaps:
    def test_hint_branch_applies_hint(self, mocker, console):
        """TuplePrompt with a custom hint uses it in the label."""
        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="[1.0, 2.0]")
        prompt = TuplePrompt(
            console,
            "Coords",
            PydanticUndefined,
            True,
            False,
            item_types=[float],
            is_homogeneous=True,
            hint="x, y format",
        )
        prompt.prompt()
        label_arg = mock_ask.call_args[0][0]
        assert "x, y format" in label_arg

    def test_optional_empty_returns_none(self, mocker, console):
        """TuplePrompt optional empty input returns None."""
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")
        prompt = TuplePrompt(
            console,
            "Coords",
            None,
            False,
            True,
            item_types=[float],
            is_homogeneous=True,
        )
        assert prompt.prompt() is None

    def test_optional_default_is_set(self, mocker, console):
        """TuplePrompt optional uses empty-string default for the Prompt."""
        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="[1.0]")
        prompt = TuplePrompt(
            console,
            "Coords",
            None,
            False,
            True,
            item_types=[float],
            is_homogeneous=True,
        )
        prompt.prompt()
        call_kwargs = mock_ask.call_args[1]
        assert call_kwargs.get("default") == ""

    def test_required_empty_retries(self, mocker, console):
        """TuplePrompt required empty input shows error and retries."""
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["", "[1.0]"])
        prompt = TuplePrompt(
            console,
            "Coords",
            PydanticUndefined,
            True,
            False,
            item_types=[float],
            is_homogeneous=True,
        )
        assert prompt.prompt() == (1.0,)
        assert "required" in console.file.getvalue()

    def test_parser_success(self, mocker, console):
        """TuplePrompt with a parser uses it instead of JSON/CSV parsing."""
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="1.0,2.0")
        prompt = TuplePrompt(
            console,
            "Coords",
            PydanticUndefined,
            True,
            False,
            item_types=[float],
            is_homogeneous=True,
            parser=lambda raw: tuple(float(x) for x in raw.split(",")),
        )
        assert prompt.prompt() == (1.0, 2.0)

    def test_parser_error_retries(self, mocker, console):
        """TuplePrompt parser error shows message and retries."""
        call_count = 0

        def strict_parser(raw: str) -> tuple[float, ...]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("bad coords")
            return tuple(float(x) for x in raw.split(","))

        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["bad", "1.0,2.0"])
        prompt = TuplePrompt(
            console,
            "Coords",
            PydanticUndefined,
            True,
            False,
            item_types=[float],
            is_homogeneous=True,
            parser=strict_parser,
        )
        assert prompt.prompt() == (1.0, 2.0)
        assert "Invalid" in console.file.getvalue()

    def test_homogeneous_csv_error_retries(self, mocker, console):
        """TuplePrompt homogeneous CSV parse error shows message and retries."""
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["notafloat", "[1.0, 2.0]"])
        prompt = TuplePrompt(
            console,
            "Coords",
            PydanticUndefined,
            True,
            False,
            item_types=[float],
            is_homogeneous=True,
        )
        result = prompt.prompt()
        assert result == (1.0, 2.0)
        assert "Invalid" in console.file.getvalue()


class TestSetPromptGaps:
    def test_optional_default_is_set(self, mocker, console):
        """SetPrompt optional uses empty-string default for the Prompt."""
        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="arcane")
        prompt = SetPrompt(console, "Factions", None, False, True, item_type=str)
        prompt.prompt()
        call_kwargs = mock_ask.call_args[1]
        assert call_kwargs.get("default") == ""

    def test_optional_empty_returns_none(self, mocker, console):
        """SetPrompt optional empty input returns None."""
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")
        prompt = SetPrompt(console, "Factions", None, False, True, item_type=str)
        assert prompt.prompt() is None

    def test_parser_error_retries(self, mocker, console):
        """SetPrompt parser error shows message and retries."""
        call_count = 0

        def strict_parser(raw: str) -> set[str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("bad input")
            return set(raw.split(","))

        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["bad", "arcane,shadow"])
        prompt = SetPrompt(
            console, "Factions", set(), False, False, item_type=str, parser=strict_parser
        )
        result = prompt.prompt()
        assert result == {"arcane", "shadow"}
        assert "Invalid" in console.file.getvalue()


class TestDictPromptGaps:
    def test_non_empty_default_prefills_kv_string(self, mocker, console):
        """DictPrompt with a non-empty dict default uses k:v string as the pre-filled default."""
        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="realm:embervault")
        prompt = DictPrompt(
            console,
            "Index",
            {"realm": "embervault"},
            False,
            False,
            key_type=str,
            value_type=str,
        )
        prompt.prompt()
        call_kwargs = mock_ask.call_args[1]
        assert "realm:embervault" in call_kwargs.get("default", "")

    def test_optional_default_is_set(self, mocker, console):
        """DictPrompt optional uses empty-string default for the Prompt."""
        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="k:v")
        prompt = DictPrompt(console, "Index", None, False, True, key_type=str, value_type=str)
        prompt.prompt()
        call_kwargs = mock_ask.call_args[1]
        assert call_kwargs.get("default") == ""

    def test_optional_empty_returns_none(self, mocker, console):
        """DictPrompt optional empty input returns None."""
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")
        prompt = DictPrompt(console, "Index", None, False, True, key_type=str, value_type=str)
        assert prompt.prompt() is None

    def test_parser_error_retries(self, mocker, console):
        """DictPrompt parser error shows message and retries."""
        call_count = 0

        def strict_parser(raw: str) -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("bad input")
            k, v = raw.split(":")
            return {k: v}

        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["bad", "realm:embervault"])
        prompt = DictPrompt(
            console, "Index", {}, False, False, key_type=str, value_type=str, parser=strict_parser
        )
        result = prompt.prompt()
        assert result == {"realm": "embervault"}
        assert "Invalid" in console.file.getvalue()
