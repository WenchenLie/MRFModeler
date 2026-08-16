"""Validation helpers used by the public configuration API.

Legacy camelCase keyword arguments are accepted for compatibility with
existing model-definition scripts.
"""

from __future__ import annotations

from collections.abc import Sequence
from numbers import Real
from typing import Any


def _display_name(name: str) -> str:
    return f" `{name}`" if name else ""


def _resolve_is_none(is_none: bool, legacy_keywords: dict) -> bool:
    """Resolve the legacy ``isNone`` spelling and reject unknown keywords."""
    is_none = legacy_keywords.pop("isNone", is_none)
    if legacy_keywords:
        names = ", ".join(sorted(legacy_keywords))
        raise TypeError(f"Unexpected keyword argument(s): {names}")
    return is_none


def _skip_none(value: Any, *, is_none: bool, name: str) -> bool:
    if value is not None:
        return False
    if is_none:
        return True
    raise ValueError(f"Variable{_display_name(name)} should not be None")


def _check_range(value: Real, min_max: list | tuple | None, name: str) -> None:
    if min_max is None:
        return
    if len(min_max) != 2:
        raise ValueError("min_max must contain exactly two values")
    minimum, maximum = min_max
    if not minimum <= value <= maximum:
        raise ValueError(
            f"Variable{_display_name(name)} should be within the range [{minimum}, {maximum}]"
        )


def _check_nonnegative(value: Real, *, pos: bool, name: str) -> None:
    if pos and value < 0:
        raise ValueError(f"Variable{_display_name(name)} should be non-negative")


def _check_length(
    value: Sequence,
    *,
    kind: str,
    length: int | None,
    min_length: int | None,
    max_length: int | None,
    name: str,
) -> None:
    label = _display_name(name)
    if length is not None and len(value) != length:
        raise ValueError(f"The length of the {kind}{label} should be {length}")
    if min_length is not None and len(value) < min_length:
        raise ValueError(f"The minimum length of the {kind}{label} should be {min_length}")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"The maximum length of the {kind}{label} should be {max_length}")


def check_int(
    value: int, min_max: list = None, pos=True, is_none=False, name="", **legacy_keywords
):
    """Validate an integer and, optionally, its inclusive range."""
    is_none = _resolve_is_none(is_none, legacy_keywords)
    if _skip_none(value, is_none=is_none, name=name):
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Variable{_display_name(name)} should be of int type")
    _check_range(value, min_max, name)
    _check_nonnegative(value, pos=pos, name=name)


def check_int_float(
    value: int | float,
    min_max: list = None,
    pos=True,
    is_none=False,
    name="",
    **legacy_keywords,
):
    """Validate a real number and, optionally, its inclusive range."""
    is_none = _resolve_is_none(is_none, legacy_keywords)
    if _skip_none(value, is_none=is_none, name=name):
        return
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"Variable{_display_name(name)} should be of int or float type")
    _check_range(value, min_max, name)
    _check_nonnegative(value, pos=pos, name=name)


def check_boolean(value: bool, is_none=False, name="", **legacy_keywords):
    """Validate a Boolean value."""
    is_none = _resolve_is_none(is_none, legacy_keywords)
    if _skip_none(value, is_none=is_none, name=name):
        return
    if not isinstance(value, bool):
        raise ValueError(f"Variable{_display_name(name)} should be of bool type")


def check_string(value: str, options: list = None, is_none=False, name="", **legacy_keywords):
    """Validate a string and, optionally, a set of accepted values."""
    is_none = _resolve_is_none(is_none, legacy_keywords)
    if _skip_none(value, is_none=is_none, name=name):
        return
    if not isinstance(value, str):
        raise ValueError(f"Variable{_display_name(name)} should be of str type")
    if options is not None and value not in options:
        raise ValueError(f"Variable{_display_name(name)} should be within {options}")


def _check_sequence_values(value: Sequence, *, pos: bool, name: str) -> None:
    if not pos:
        return
    for item in value:
        if isinstance(item, bool) or not isinstance(item, Real):
            raise ValueError(f"Items of variable{_display_name(name)} should be numeric")
        _check_nonnegative(item, pos=True, name=name)


def check_tuple(
    value: tuple,
    length=None,
    min_length=None,
    max_length=None,
    pos=True,
    is_none=False,
    name="",
    **legacy_keywords,
):
    """Validate a tuple, its length, and optionally numeric item values."""
    is_none = _resolve_is_none(is_none, legacy_keywords)
    if _skip_none(value, is_none=is_none, name=name):
        return
    if not isinstance(value, tuple):
        raise ValueError(f"Variable{_display_name(name)} should be of tuple type")
    _check_length(
        value,
        kind="tuple",
        length=length,
        min_length=min_length,
        max_length=max_length,
        name=name,
    )
    _check_sequence_values(value, pos=pos, name=name)


def check_list(
    value: list,
    length=None,
    min_length=None,
    max_length=None,
    pos=True,
    is_none=False,
    name="",
    **legacy_keywords,
):
    """Validate a list, its length, and optionally numeric item values."""
    is_none = _resolve_is_none(is_none, legacy_keywords)
    if _skip_none(value, is_none=is_none, name=name):
        return
    if not isinstance(value, list):
        raise ValueError(f"Variable{_display_name(name)} should be of list type")
    _check_length(
        value,
        kind="list",
        length=length,
        min_length=min_length,
        max_length=max_length,
        name=name,
    )
    _check_sequence_values(value, pos=pos, name=name)


def check_dict(value: dict, is_none=False, name="", **legacy_keywords):
    """Validate a dictionary."""
    is_none = _resolve_is_none(is_none, legacy_keywords)
    if _skip_none(value, is_none=is_none, name=name):
        return
    if not isinstance(value, dict):
        raise ValueError(f"Variable{_display_name(name)} should be of dict type")
