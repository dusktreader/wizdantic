"""
Type introspection utilities for wizdantic.

Pure functions that crack open type annotations and extract the information
the wizard needs to pick the right prompt strategy, plus pure parsing helpers
that convert raw user input into typed Python values.
"""

import json
import types
import typing
from typing import Any, get_args, get_origin

import pydantic


def unwrap_optional(annotation: Any) -> Any | None:
    """
    Detect `Optional[T]` (or `T | None`) and return the inner type.

    Returns the unwrapped inner type if the annotation is optional,
    or `None` if it is not. Callers typically unwrap first so they can
    inspect or validate the inner type independently while still
    supporting `None` as a valid value.
    """
    origin = get_origin(annotation)
    if origin is typing.Union or isinstance(annotation, types.UnionType):
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if type(None) in args and len(non_none) == 1:
            return non_none[0]
    return None


def unwrap_list(annotation: Any) -> Any | None:
    """
    Detect `list[T]` and return the item type.

    Returns the item type if the annotation is a parameterized list,
    `str` if it is a bare `list`, or `None` if the annotation is not a list.
    """
    origin = get_origin(annotation)
    if origin is list:
        args = get_args(annotation)
        return args[0] if args else str
    if annotation is list:
        return str
    return None


def unwrap_tuple(annotation: Any) -> tuple[list[Any], bool] | None:
    """
    Detect `tuple[T, ...]` or `tuple[T1, T2, ...]` and return item types.

    Returns a two-element tuple of `(item_types, is_homogeneous)`:

    - For homogeneous `tuple[T, ...]`: `([T], True)`
    - For fixed-length `tuple[T1, T2, T3]`: `([T1, T2, T3], False)`
    - For bare `tuple`: `([str], True)`
    - For non-tuples: `None`

    Parameters:
        annotation: The type annotation to inspect.
    """
    origin = get_origin(annotation)
    if origin is tuple:
        args = get_args(annotation)
        if not args:
            return ([str], True)
        if len(args) == 2 and args[1] is Ellipsis:
            return ([args[0]], True)
        return (list(args), False)
    if annotation is tuple:
        return ([str], True)
    return None


def unwrap_set(annotation: Any) -> Any | None:
    """
    Detect `set[T]` and return the item type.

    Returns the item type if the annotation is a parameterized set,
    `str` if it is a bare `set`, or `None` if the annotation is not a set.
    """
    origin = get_origin(annotation)
    if origin is set:
        args = get_args(annotation)
        return args[0] if args else str
    if annotation is set:
        return str
    return None


def unwrap_dict(annotation: Any) -> tuple[Any, Any] | None:
    """
    Detect `dict[K, V]` and return the key and value types.

    Returns `(key_type, value_type)` if the annotation is a parameterized
    dict, `(str, str)` for a bare `dict`, or `None` if it is not a dict.
    """
    origin = get_origin(annotation)
    if origin is dict:
        args = get_args(annotation)
        if args:
            return (args[0], args[1])
        return (str, str)
    if annotation is dict:
        return (str, str)
    return None


def unwrap_literal(annotation: Any) -> tuple[Any, ...] | None:
    """
    Detect `Literal["a", "b", ...]` and return the allowed values.

    Returns a tuple of the literal values, or `None` if the annotation
    is not a `Literal`.
    """
    if get_origin(annotation) is typing.Literal:
        return get_args(annotation)
    return None


def parse_json_sequence(raw: str, item_type: Any) -> list[Any]:
    """
    Parse `raw` as a JSON array and validate each element via `TypeAdapter`.

    Raises `ValueError` if `raw` is not valid JSON, if the JSON value is not
    an array, or if any element fails validation.

    Parameters:
        raw:       The raw string from the prompt.
        item_type: The expected type of each element.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(parsed, list):
        raise ValueError(f"Expected a JSON array, got {type(parsed).__name__}")

    adapter = pydantic.TypeAdapter(item_type)
    try:
        return [adapter.validate_python(item) for item in parsed]
    except pydantic.ValidationError as exc:
        msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
        raise ValueError(msg) from exc


def parse_csv_sequence(raw: str, item_type: Any) -> list[Any]:
    """
    Split `raw` on commas, strip whitespace, and validate each element.

    Raises `ValueError` if the string is blank after stripping or if any
    element fails validation.

    Parameters:
        raw:       The raw string from the prompt.
        item_type: The expected type of each element.
    """
    items = [s.strip() for s in raw.split(",") if s.strip()]
    if not items:
        raise ValueError("No values found after splitting on commas")

    adapter = pydantic.TypeAdapter(item_type)
    try:
        return [adapter.validate_python(item) for item in items]
    except pydantic.ValidationError as exc:
        msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
        raise ValueError(msg) from exc


def parse_csv_fixed_tuple(raw: str, item_types: list[Any]) -> list[Any]:
    """
    Split `raw` on commas and validate each position against its declared type.

    Raises `ValueError` if the element count does not match `item_types`, if
    the string is blank after stripping, or if any element fails validation.

    Parameters:
        raw:        The raw string from the prompt.
        item_types: One type per expected position in the tuple.
    """
    items = [s.strip() for s in raw.split(",") if s.strip()]
    if not items:
        raise ValueError("No values found after splitting on commas")
    if len(items) != len(item_types):
        raise ValueError(f"Expected {len(item_types)} element(s), got {len(items)}")

    result = []
    for item, item_type in zip(items, item_types):
        try:
            result.append(pydantic.TypeAdapter(item_type).validate_python(item))
        except pydantic.ValidationError as exc:
            msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
            raise ValueError(msg) from exc
    return result


def parse_json_fixed_tuple(raw: str, item_types: list[Any]) -> list[Any]:
    """
    Parse `raw` as a JSON array and validate each position against its declared type.

    Raises `ValueError` if `raw` is not valid JSON, if the JSON value is not an
    array, if the element count does not match `item_types`, or if any element
    fails validation.

    Parameters:
        raw:        The raw string from the prompt.
        item_types: One type per expected position in the tuple.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError(f"Expected a JSON array, got {type(parsed).__name__}")
    if len(parsed) != len(item_types):
        raise ValueError(f"Expected {len(item_types)} element(s), got {len(parsed)}")

    result = []
    for element, item_type in zip(parsed, item_types):
        try:
            result.append(pydantic.TypeAdapter(item_type).validate_python(element))
        except pydantic.ValidationError as exc:
            msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
            raise ValueError(msg) from exc
    return result


def parse_csv_set(raw: str, item_type: Any) -> set[Any]:
    """
    Split `raw` on commas, strip whitespace, validate each element, and
    return a set.

    Raises `ValueError` if the string is blank after stripping, if any
    element fails validation, or if duplicate values are found.

    Parameters:
        raw:       The raw string from the prompt.
        item_type: The expected type of each element.
    """
    items = parse_csv_sequence(raw, item_type)
    if len(items) != len(set(items)):
        duplicates = sorted({str(item) for item in items if items.count(item) > 1})
        raise ValueError(f"Duplicate values are not allowed in a set: {', '.join(duplicates)}")
    return set(items)


def parse_json_set(raw: str, item_type: Any) -> set[Any]:
    """
    Parse `raw` as a JSON array and return a set of validated elements.

    Raises `ValueError` if `raw` is not valid JSON, if the JSON value is not
    an array, if any element fails validation, or if duplicate values are found.

    Parameters:
        raw:       The raw string from the prompt.
        item_type: The expected type of each element.
    """
    items = parse_json_sequence(raw, item_type)
    if len(items) != len(set(items)):
        duplicates = sorted({str(item) for item in items if items.count(item) > 1})
        raise ValueError(f"Duplicate values are not allowed in a set: {', '.join(duplicates)}")
    return set(items)


def parse_kv_string(raw: str, key_type: Any, value_type: Any) -> dict[Any, Any]:
    """
    Parse `raw` as `k:v,k:v,...` notation into a dict.

    Each comma-separated chunk must split on `:` into exactly two parts.
    Leading and trailing whitespace is stripped from both keys and values.
    Raises `ValueError` if any chunk does not conform or if key/value
    validation fails.

    Parameters:
        raw:        The raw string from the prompt.
        key_type:   The expected type for keys.
        value_type: The expected type for values.
    """
    pairs = [chunk.strip() for chunk in raw.split(",") if chunk.strip()]
    if not pairs:
        raise ValueError("No key-value pairs found")

    result: dict[Any, Any] = {}
    key_adapter = pydantic.TypeAdapter(key_type)
    value_adapter = pydantic.TypeAdapter(value_type)

    for pair in pairs:
        parts = pair.split(":")
        if len(parts) != 2:
            raise ValueError(
                f"Expected 'key:value' but got {pair!r} "
                f"({len(parts)} part{'s' if len(parts) != 1 else ''} after splitting on ':')"
            )
        raw_key = parts[0].strip()
        raw_value = parts[1].strip()

        try:
            key = key_adapter.validate_python(raw_key)
        except pydantic.ValidationError as exc:
            msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
            raise ValueError(f"Invalid key {raw_key!r}: {msg}") from exc

        try:
            value = value_adapter.validate_python(raw_value)
        except pydantic.ValidationError as exc:
            msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
            raise ValueError(f"Invalid value {raw_value!r}: {msg}") from exc

        result[key] = value

    return result


def parse_json_dict(raw: str, key_type: Any, value_type: Any) -> dict[Any, Any]:
    """
    Parse `raw` as a JSON object and validate keys and values via `TypeAdapter`.

    Raises `ValueError` if `raw` is not valid JSON, if the JSON value is not
    an object, or if any key or value fails validation.

    Parameters:
        raw:        The raw string from the prompt.
        key_type:   The expected type for keys.
        value_type: The expected type for values.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a JSON object, got {type(parsed).__name__}")

    key_adapter = pydantic.TypeAdapter(key_type)
    value_adapter = pydantic.TypeAdapter(value_type)
    result: dict[Any, Any] = {}

    for raw_key, raw_value in parsed.items():
        try:
            key = key_adapter.validate_python(raw_key)
        except pydantic.ValidationError as exc:
            msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
            raise ValueError(f"Invalid key {raw_key!r}: {msg}") from exc

        try:
            value = value_adapter.validate_python(raw_value)
        except pydantic.ValidationError as exc:
            msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
            raise ValueError(f"Invalid value {raw_value!r}: {msg}") from exc

        result[key] = value

    return result


def is_unsupported_union(annotation: Any) -> bool:
    """
    Detect multi-type unions that wizdantic cannot prompt for.

    `Optional[T]` (i.e. `T | None`) is supported and returns `False`.
    Any other union of two or more concrete types (e.g. `str | int`) returns
    `True` because there is no way to know which branch to prompt for.
    """
    origin = get_origin(annotation)
    if origin is not typing.Union and not isinstance(annotation, types.UnionType):
        return False
    args = get_args(annotation)
    non_none = [a for a in args if a is not type(None)]
    # Optional[T] has exactly one non-None branch -- that's fine
    return len(non_none) > 1
