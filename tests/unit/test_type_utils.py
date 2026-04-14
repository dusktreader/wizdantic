"""
Tests for type_utils: unwrap helpers and parsing functions.
"""

from typing import Literal, Optional

import pytest

from wizdantic.type_utils import (
    is_unsupported_union,
    parse_csv_fixed_tuple,
    parse_csv_sequence,
    parse_csv_set,
    parse_json_dict,
    parse_json_fixed_tuple,
    parse_json_sequence,
    parse_json_set,
    parse_kv_string,
    unwrap_dict,
    unwrap_list,
    unwrap_literal,
    unwrap_optional,
    unwrap_set,
    unwrap_tuple,
)


class TestUnwrapOptional:
    def test_optional_str(self):
        assert unwrap_optional(Optional[str]) is str

    def test_pipe_none(self):
        assert unwrap_optional(str | None) is str

    def test_not_optional(self):
        assert unwrap_optional(str) is None

    def test_optional_int(self):
        assert unwrap_optional(int | None) is int

    def test_optional_float(self):
        assert unwrap_optional(float | None) is float

    def test_optional_bool(self):
        assert unwrap_optional(bool | None) is bool

    def test_bare_none_type(self):
        """`type(None)` alone is not an Optional wrapper."""
        assert unwrap_optional(type(None)) is None

    def test_union_of_two_concrete_types(self):
        """`str | int` is a Union but not Optional (no None)."""
        assert unwrap_optional(str | int) is None


class TestUnwrapList:
    def test_list_int(self):
        assert unwrap_list(list[int]) is int

    def test_list_str(self):
        assert unwrap_list(list[str]) is str

    def test_not_list(self):
        assert unwrap_list(str) is None

    def test_list_float(self):
        assert unwrap_list(list[float]) is float

    def test_bare_list_returns_str(self):
        """Bare `list` without type args defaults to `str`."""
        assert unwrap_list(list) is str

    def test_tuple_not_detected(self):
        """`tuple[int, ...]` is not a list type."""
        assert unwrap_list(tuple[int, ...]) is None

    def test_set_not_detected(self):
        """`set[str]` is not a list type."""
        assert unwrap_list(set[str]) is None


class TestUnwrapTuple:
    def test_homogeneous_tuple(self):
        result = unwrap_tuple(tuple[int, ...])
        assert result == ([int], True)

    def test_homogeneous_str_tuple(self):
        result = unwrap_tuple(tuple[str, ...])
        assert result == ([str], True)

    def test_fixed_length_tuple(self):
        result = unwrap_tuple(tuple[str, int, bool])
        assert result == ([str, int, bool], False)

    def test_fixed_length_two_elements(self):
        result = unwrap_tuple(tuple[str, int])
        assert result == ([str, int], False)

    def test_bare_tuple(self):
        result = unwrap_tuple(tuple)
        assert result == ([str], True)

    def test_not_tuple(self):
        assert unwrap_tuple(list[int]) is None
        assert unwrap_tuple(str) is None
        assert unwrap_tuple(dict[str, int]) is None

    def test_single_element_fixed_tuple(self):
        """A single-element tuple without Ellipsis is fixed-length."""
        result = unwrap_tuple(tuple[str])
        assert result == ([str], False)


class TestUnwrapSet:
    def test_set_str(self):
        assert unwrap_set(set[str]) is str

    def test_set_int(self):
        assert unwrap_set(set[int]) is int

    def test_bare_set(self):
        assert unwrap_set(set) is str

    def test_not_set(self):
        assert unwrap_set(list[str]) is None
        assert unwrap_set(str) is None

    def test_set_float(self):
        assert unwrap_set(set[float]) is float


class TestUnwrapDict:
    def test_dict_str_str(self):
        assert unwrap_dict(dict[str, str]) == (str, str)

    def test_dict_str_int(self):
        assert unwrap_dict(dict[str, int]) == (str, int)

    def test_dict_int_float(self):
        assert unwrap_dict(dict[int, float]) == (int, float)

    def test_bare_dict(self):
        assert unwrap_dict(dict) == (str, str)

    def test_not_dict(self):
        assert unwrap_dict(list[str]) is None
        assert unwrap_dict(str) is None
        assert unwrap_dict(set[str]) is None


class TestUnwrapLiteral:
    def test_literal_strings(self):
        assert unwrap_literal(Literal["arcane", "shadow"]) == ("arcane", "shadow")

    def test_not_literal(self):
        assert unwrap_literal(str) is None

    def test_literal_ints(self):
        assert unwrap_literal(Literal[1, 2, 3]) == (1, 2, 3)

    def test_literal_single_value(self):
        assert unwrap_literal(Literal["only"]) == ("only",)

    def test_literal_mixed_types(self):
        assert unwrap_literal(Literal["alpha", 42]) == ("alpha", 42)


class TestParseJsonSequence:
    def test_basic_string_list(self):
        assert parse_json_sequence('["mordain", "elara"]', str) == ["mordain", "elara"]

    def test_int_list(self):
        assert parse_json_sequence("[1, 2, 3]", int) == [1, 2, 3]

    def test_float_list(self):
        result = parse_json_sequence("[1.1, 2.2]", float)
        assert result == pytest.approx([1.1, 2.2])

    def test_single_element(self):
        assert parse_json_sequence('["lone"]', str) == ["lone"]

    def test_empty_array(self):
        assert parse_json_sequence("[]", str) == []

    def test_type_coercion_from_json_strings(self):
        """JSON strings inside an int array are coerced by TypeAdapter."""
        assert parse_json_sequence('["1", "2"]', int) == [1, 2]

    def test_json_int_to_str_fails(self):
        """JSON integers are not coerced to str by validate_python (strict types)."""
        with pytest.raises(ValueError):
            parse_json_sequence("[1, 2]", str)

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_json_sequence("not json", str)

    def test_json_object_raises(self):
        """A JSON object is not a sequence."""
        with pytest.raises(ValueError, match="Expected a JSON array"):
            parse_json_sequence('{"a": 1}', str)

    def test_json_string_raises(self):
        """A bare JSON string is not a sequence."""
        with pytest.raises(ValueError, match="Expected a JSON array"):
            parse_json_sequence('"hello"', str)

    def test_validation_failure_raises(self):
        with pytest.raises(ValueError):
            parse_json_sequence('["not_a_number"]', int)

    def test_nested_values_coerced(self):
        """Numeric strings inside JSON are coerced by TypeAdapter."""
        assert parse_json_sequence('["1", "2"]', int) == [1, 2]


class TestParseCsvSequence:
    def test_basic(self):
        assert parse_csv_sequence("mordain, elara, grimshaw", str) == ["mordain", "elara", "grimshaw"]

    def test_strips_whitespace(self):
        assert parse_csv_sequence("  mordain  ,  elara  ", str) == ["mordain", "elara"]

    def test_int_coercion(self):
        assert parse_csv_sequence("1, 2, 3", int) == [1, 2, 3]

    def test_float_coercion(self):
        result = parse_csv_sequence("1.1, 2.2", float)
        assert result == pytest.approx([1.1, 2.2])

    def test_single_value(self):
        assert parse_csv_sequence("embervault", str) == ["embervault"]

    def test_blank_string_raises(self):
        with pytest.raises(ValueError, match="No values found"):
            parse_csv_sequence("", str)

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="No values found"):
            parse_csv_sequence("   ", str)

    def test_commas_only_raises(self):
        with pytest.raises(ValueError, match="No values found"):
            parse_csv_sequence(" , , ", str)

    def test_validation_failure_raises(self):
        with pytest.raises(ValueError):
            parse_csv_sequence("one, two, three", int)

    def test_mixed_valid_invalid_raises_on_first_bad(self):
        with pytest.raises(ValueError):
            parse_csv_sequence("1, bad, 3", int)


class TestParseCsvFixedTuple:
    def test_basic(self):
        assert parse_csv_fixed_tuple("mordain, 7", [str, int]) == ["mordain", 7]

    def test_strips_whitespace(self):
        assert parse_csv_fixed_tuple("  veil  ,  3  ", [str, int]) == ["veil", 3]

    def test_all_same_type(self):
        assert parse_csv_fixed_tuple("1.1, 2.2, 3.3", [float, float, float]) == pytest.approx([1.1, 2.2, 3.3])

    def test_wrong_count_too_few_raises(self):
        with pytest.raises(ValueError, match="Expected 3"):
            parse_csv_fixed_tuple("a, b", [str, str, str])

    def test_wrong_count_too_many_raises(self):
        with pytest.raises(ValueError, match="Expected 2"):
            parse_csv_fixed_tuple("a, b, c", [str, str])

    def test_blank_string_raises(self):
        with pytest.raises(ValueError, match="No values found"):
            parse_csv_fixed_tuple("", [str, int])

    def test_validation_failure_raises(self):
        with pytest.raises(ValueError):
            parse_csv_fixed_tuple("veil, notanumber", [str, int])


class TestParseJsonFixedTuple:
    def test_basic(self):
        assert parse_json_fixed_tuple('["mordain", 7]', [str, int]) == ["mordain", 7]

    def test_all_same_type(self):
        result = parse_json_fixed_tuple("[1.1, 2.2, 3.3]", [float, float, float])
        assert result == pytest.approx([1.1, 2.2, 3.3])

    def test_wrong_count_too_few_raises(self):
        with pytest.raises(ValueError, match="Expected 3"):
            parse_json_fixed_tuple('["a", "b"]', [str, str, str])

    def test_wrong_count_too_many_raises(self):
        with pytest.raises(ValueError, match="Expected 2"):
            parse_json_fixed_tuple('["a", "b", "c"]', [str, str])

    def test_not_array_raises(self):
        with pytest.raises(ValueError, match="Expected a JSON array"):
            parse_json_fixed_tuple('{"a": 1}', [str, int])

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_json_fixed_tuple("not json", [str, int])

    def test_validation_failure_raises(self):
        with pytest.raises(ValueError):
            parse_json_fixed_tuple('["veil", "notanumber"]', [str, int])


class TestParseJsonSet:
    def test_basic(self):
        assert parse_json_set('["gloomreach", "frosthollow"]', str) == {"gloomreach", "frosthollow"}

    def test_duplicates_raise(self):
        with pytest.raises(ValueError, match="Duplicate values are not allowed"):
            parse_json_set('["a", "a", "b"]', str)

    def test_int_set(self):
        assert parse_json_set("[1, 2, 3]", int) == {1, 2, 3}

    def test_empty_set(self):
        assert parse_json_set("[]", str) == set()

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_json_set("not json", str)

    def test_json_object_raises(self):
        with pytest.raises(ValueError, match="Expected a JSON array"):
            parse_json_set('{"a": 1}', str)


class TestParseCsvSet:
    def test_basic(self):
        assert parse_csv_set("gloomreach, frosthollow", str) == {"gloomreach", "frosthollow"}

    def test_strips_whitespace(self):
        assert parse_csv_set(" gloomreach , frosthollow ", str) == {"gloomreach", "frosthollow"}

    def test_single_element(self):
        assert parse_csv_set("gloomreach", str) == {"gloomreach"}

    def test_int_set(self):
        assert parse_csv_set("1, 2, 3", int) == {1, 2, 3}

    def test_duplicates_raise(self):
        with pytest.raises(ValueError, match="Duplicate values are not allowed"):
            parse_csv_set("arcane, arcane, wyvern", str)

    def test_blank_raises(self):
        with pytest.raises(ValueError):
            parse_csv_set("  ,  ,  ", str)

    def test_validation_failure_raises(self):
        with pytest.raises(ValueError):
            parse_csv_set("one, notanumber, three", int)


class TestParseKvString:
    def test_basic(self):
        assert parse_kv_string("name:mordain, school:evocation", str, str) == {"name": "mordain", "school": "evocation"}

    def test_strips_whitespace(self):
        assert parse_kv_string(" name : mordain , school : necromancy ", str, str) == {
            "name": "mordain",
            "school": "necromancy",
        }

    def test_single_pair(self):
        assert parse_kv_string("realm:embervault", str, str) == {"realm": "embervault"}

    def test_int_values(self):
        assert parse_kv_string("score:100, level:5", str, int) == {"score": 100, "level": 5}

    def test_int_keys_and_values(self):
        assert parse_kv_string("1:10, 2:20", int, int) == {1: 10, 2: 20}

    def test_float_values(self):
        result = parse_kv_string("rating:9.5", str, float)
        assert result == pytest.approx({"rating": 9.5})

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="No key-value pairs found"):
            parse_kv_string("", str, str)

    def test_missing_colon_raises(self):
        with pytest.raises(ValueError, match="Expected 'key:value'"):
            parse_kv_string("nocolon", str, str)

    def test_too_many_colons_raises(self):
        """Three parts after splitting on ':' is rejected."""
        with pytest.raises(ValueError, match="Expected 'key:value'"):
            parse_kv_string("url:https://example.com", str, str)

    def test_invalid_key_type_raises(self):
        with pytest.raises(ValueError, match="Invalid key"):
            parse_kv_string("notanint:value", int, str)

    def test_invalid_value_type_raises(self):
        with pytest.raises(ValueError, match="Invalid value"):
            parse_kv_string("key:notanint", str, int)

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="No key-value pairs found"):
            parse_kv_string("  ,  ", str, str)

    def test_multiple_pairs_one_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_kv_string("good:1, bad_pair, ok:3", str, int)


class TestParseJsonDict:
    def test_basic(self):
        assert parse_json_dict('{"name": "mordain", "school": "evocation"}', str, str) == {
            "name": "mordain",
            "school": "evocation",
        }

    def test_int_values(self):
        assert parse_json_dict('{"score": 100, "level": 5}', str, int) == {"score": 100, "level": 5}

    def test_empty_object(self):
        assert parse_json_dict("{}", str, str) == {}

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_json_dict("not json", str, str)

    def test_json_array_raises(self):
        with pytest.raises(ValueError, match="Expected a JSON object"):
            parse_json_dict("[1, 2]", str, str)

    def test_invalid_value_type_raises(self):
        with pytest.raises(ValueError, match="Invalid value"):
            parse_json_dict('{"key": "notanint"}', str, int)


class TestIsUnsupportedUnion:
    def test_str_int_union(self):
        assert is_unsupported_union(str | int) is True

    def test_three_way_union(self):
        assert is_unsupported_union(str | int | float) is True

    def test_optional_str_is_supported(self):
        """Optional[str] is a union with None, but it's supported."""
        assert is_unsupported_union(str | None) is False
        assert is_unsupported_union(Optional[str]) is False

    def test_plain_type_is_supported(self):
        assert is_unsupported_union(str) is False
        assert is_unsupported_union(int) is False
        assert is_unsupported_union(list[str]) is False

    def test_multi_type_with_none(self):
        """str | int | None is still unsupported -- two non-None branches."""
        assert is_unsupported_union(str | int | None) is True
