# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved
import builtins
import random
from copy import copy
from typing import Any, Callable, Dict, List, Optional, Union

from hydra._internal.grammar.utils import is_type_matching
from hydra.core.override_parser.types import (
    ChoiceSweep,
    Glob,
    IntervalSweep,
    ParsedElementType,
    QuotedString,
    RangeSweep,
    Sweep,
)
from hydra.errors import HydraException

ElementType = Union[str, int, bool, float, list, dict]


def apply_to_dict_values(
    # val
    value: Dict[Any, Any],
    # func
    function: Callable[..., Any],
) -> Dict[Any, Any]:
    ret_dict: Dict[str, Any] = {}
    for key, value in value.items():
        ret_dict[key] = function(value)
    return ret_dict


def cast_choice(value: ChoiceSweep, function: Callable[..., Any]) -> ChoiceSweep:
    choices = []
    for item in value.list:
        choice = function(item)
        assert is_type_matching(choice, ElementType)
        choices.append(choice)
    return ChoiceSweep(simple_form=value.simple_form, list=choices)


def cast_interval(value: IntervalSweep, _function: Callable[..., Any]) -> None:
    if isinstance(value, IntervalSweep):
        raise ValueError(
            "Intervals are always interpreted as floating-point intervals and cannot be cast"
        )


def cast_range(value: RangeSweep, function: Callable[..., Any]) -> RangeSweep:
    if function not in (cast_float, cast_int):
        raise HydraException("Range can only be cast to int or float")
    return RangeSweep(
        start=function(value.start),
        stop=function(value.stop),
        step=function(value.step),
    )


CastType = Union[ParsedElementType, Sweep]


def _list_to_simple_choice(*args: Any) -> ChoiceSweep:
    choices: List[ParsedElementType] = []
    for arg in args:
        assert is_type_matching(arg, ParsedElementType)
        choices.append(arg)
    return ChoiceSweep(list=builtins.list(choices), simple_form=True)


def _normalize_cast_value(*args: CastType, value: Optional[CastType]) -> CastType:
    if len(args) > 0 and value is not None:
        raise TypeError("cannot use both position and named arguments")
    if value is not None:
        return value
    if len(args) == 0:
        raise TypeError("No positional args or value specified")
    if len(args) == 1:
        return args[0]
    if len(args) > 1:
        return _list_to_simple_choice(*args)
    assert False


def cast_int(*args: CastType, value: Optional[CastType] = None) -> Any:
    value = _normalize_cast_value(*args, value=value)
    if isinstance(value, QuotedString):
        return cast_int(value.text)
    if isinstance(value, dict):
        return apply_to_dict_values(value, cast_int)
    if isinstance(value, list):
        return list(map(cast_int, value))
    elif isinstance(value, ChoiceSweep):
        return cast_choice(value, cast_int)
    elif isinstance(value, RangeSweep):
        return cast_range(value, cast_int)
    elif isinstance(value, IntervalSweep):
        return cast_interval(value, cast_int)
    assert isinstance(value, (int, float, bool, str))
    return int(value)


def cast_float(*args: CastType, value: Optional[CastType] = None) -> Any:
    value = _normalize_cast_value(*args, value=value)
    if isinstance(value, QuotedString):
        return cast_float(value.text)
    if isinstance(value, dict):
        return apply_to_dict_values(value, cast_float)
    if isinstance(value, list):
        return list(map(cast_float, value))
    elif isinstance(value, ChoiceSweep):
        return cast_choice(value, cast_float)
    elif isinstance(value, RangeSweep):
        return cast_range(value, cast_float)
    elif isinstance(value, IntervalSweep):
        return cast_interval(value, cast_float)
    assert isinstance(value, (int, float, bool, str))
    return float(value)


def cast_str(*args: CastType, value: Optional[CastType] = None) -> Any:
    value = _normalize_cast_value(*args, value=value)
    if isinstance(value, QuotedString):
        return cast_str(value.text)
    if isinstance(value, dict):
        return apply_to_dict_values(value, cast_str)
    if isinstance(value, list):
        return list(map(cast_str, value))
    elif isinstance(value, ChoiceSweep):
        return cast_choice(value, cast_str)
    elif isinstance(value, RangeSweep):
        return cast_range(value, cast_str)
    elif isinstance(value, IntervalSweep):
        return cast_interval(value, cast_str)

    assert isinstance(value, (int, float, bool, str))
    if isinstance(value, bool):
        return str(value).lower()
    else:
        return str(value)


def cast_bool(*args: CastType, value: Optional[CastType] = None) -> Any:
    value = _normalize_cast_value(*args, value=value)
    if isinstance(value, QuotedString):
        return cast_bool(value.text)
    if isinstance(value, dict):
        return apply_to_dict_values(value, cast_bool)
    if isinstance(value, list):
        return list(map(cast_bool, value))
    elif isinstance(value, ChoiceSweep):
        return cast_choice(value, cast_bool)
    elif isinstance(value, RangeSweep):
        return cast_range(value, cast_bool)
    elif isinstance(value, IntervalSweep):
        return cast_interval(value, cast_bool)

    if isinstance(value, str):
        if value.lower() == "false":
            return False
        elif value.lower() == "true":
            return True
        else:
            raise ValueError(f"Cannot cast '{value}' to bool")
    return bool(value)


def choice(
    *args: Union[str, int, float, bool, Dict[Any, Any], List[Any], ChoiceSweep]
) -> ChoiceSweep:
    if len(args) == 1:
        first = args[0]
        if isinstance(first, ChoiceSweep) and first.simple_form:
            first.simple_form = False
            return first

    for arg in args:
        if isinstance(arg, ChoiceSweep):
            raise HydraException("Only a simple choice sweep is supported")
    return ChoiceSweep(list=list(args))  # type: ignore


def range(
    start: Union[int, float], stop: Union[int, float], step: Union[int, float] = 1
) -> RangeSweep:
    return RangeSweep(start=start, stop=stop, step=step)


def interval(start: Union[int, float], end: Union[int, float]) -> IntervalSweep:
    return IntervalSweep(start=start, end=end)


def tag(*args: Union[str, Union[Sweep]], sweep: Optional[Sweep] = None) -> Sweep:
    if len(args) < 1:
        raise ValueError("Not enough arguments to tag, must take at least a sweep")

    if sweep is not None:
        return tag(*(list(args) + [sweep]))

    last = args[-1]
    if isinstance(last, Sweep):
        sweep = last
        tags = set()
        for tag_ in args[0:-1]:
            if not isinstance(tag_, str):
                raise ValueError(
                    f"tag arguments type must be string, got {type(tag_).__name__}"
                )
            tags.add(tag_)
        sweep.tags = tags
        return sweep
    else:
        raise ValueError(
            f"Last argument to tag() must be a choice(), range() or interval(), got {type(sweep).__name__}"
        )


def shuffle(
    *args: Union[ElementType, ChoiceSweep, RangeSweep],
    sweep: Optional[Union[ChoiceSweep, RangeSweep]] = None,
    list: Optional[List[Any]] = None,
) -> Union[List[Any], ChoiceSweep, RangeSweep]:
    """
    simple choice:  shuffle(a,b,c)
    choice:         shuffle(choice(a,b,c)), shuffle(sweep=choice(a,b,c))
    range:          shuffle(range(1,10)),   shuffle(sweep=range(1,10))
    list:           shuffle([a,b,c]),       shuffle(list=[a,b,c])
    """
    if list is not None:
        return shuffle(list)
    if sweep is not None:
        return shuffle(sweep)

    if len(args) == 1:
        arg = args[0]
        if isinstance(arg, (ChoiceSweep, RangeSweep)):
            sweep = copy(arg)
            sweep.shuffle = True
            return sweep
        if isinstance(arg, builtins.list):
            lst = copy(arg)
            random.shuffle(lst)
            return lst
        else:
            return [arg]
    else:
        simple_choice = _list_to_simple_choice(*args)
        simple_choice.shuffle = True
        return simple_choice


def sort(
    *args: Union[ElementType, ChoiceSweep, RangeSweep],
    sweep: Optional[Union[ChoiceSweep, RangeSweep]] = None,
    reverse: bool = False,
    list: Optional[List[Any]] = None,
) -> Any:
    """
    sort(1,3,2)
    sort(1,3,2,reverse=true)
    sort([1,3,2])
    sort(lst=[1,3,2])
    """

    if list is not None:
        return sort(list, reverse=reverse)
    if sweep is not None:
        return _sort_sweep(sweep, reverse)

    if len(args) == 1:
        arg = args[0]
        if isinstance(arg, (ChoiceSweep, RangeSweep)):
            # choice: sort(choice(a,b,c))
            # range: sort(range(1,10))
            return _sort_sweep(arg, reverse)
        elif isinstance(arg, builtins.list):
            return sorted(arg, reverse=reverse)
        else:
            raise TypeError(f"Invalid arguments: {args}")
    else:
        primitives = (int, float, bool, str)
        for arg in args:
            if not isinstance(arg, primitives):
                raise TypeError(f"Invalid arguments: {args}")

        cw = _list_to_simple_choice(*args)
        return _sort_sweep(cw, reverse)


def _sort_sweep(
    sweep: Union[ChoiceSweep, RangeSweep], reverse: bool
) -> Union[ChoiceSweep, RangeSweep]:
    sweep = copy(sweep)

    if isinstance(sweep, ChoiceSweep):
        sweep.list = sorted(sweep.list, reverse=reverse)
        return sweep
    elif isinstance(sweep, RangeSweep):
        assert sweep.start is not None
        assert sweep.stop is not None
        if not reverse:
            # ascending
            if sweep.start > sweep.stop:
                start = sweep.stop + abs(sweep.step)
                stop = sweep.start + abs(sweep.step)
                sweep.start = start
                sweep.stop = stop
                sweep.step = -sweep.step
        else:
            # descending
            if sweep.start < sweep.stop:
                start = sweep.stop - abs(sweep.step)
                stop = sweep.start - abs(sweep.step)
                sweep.start = start
                sweep.stop = stop
                sweep.step = -sweep.step
        return sweep
    else:
        assert False


def glob(
    include: Union[List[str], str], exclude: Optional[Union[List[str], str]] = None
) -> Glob:

    if isinstance(include, str):
        include = [include]
    if exclude is None:
        exclude = []
    elif isinstance(exclude, str):
        exclude = [exclude]

    return Glob(include=include, exclude=exclude)