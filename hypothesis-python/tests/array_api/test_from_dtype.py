# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from hypothesis.extra.array_api import DTYPE_NAMES, find_castable_builtin_for_dtype
from hypothesis.internal.floats import width_smallest_normals

from tests.array_api.common import flushes_to_zero, skip_on_unsupported_dtype
from tests.common.debug import (
    assert_all_examples,
    assert_no_examples,
    find_any,
    minimal,
)

# TODO: filter unsupported dtypes


@pytest.mark.parametrize("dtype_name", DTYPE_NAMES)
def test_strategies_have_reusable_values(xp, xps, dtype_name):
    """Inferred strategies have reusable values."""
    skip_on_unsupported_dtype(xp, dtype_name)
    strat = xps.from_dtype(dtype_name)
    assert strat.has_reusable_values


@pytest.mark.parametrize("dtype_name", DTYPE_NAMES)
def test_produces_castable_instances_from_dtype(xp, xps, dtype_name):
    """Strategies inferred by dtype generate values of a builtin type castable
    to the dtype."""
    skip_on_unsupported_dtype(xp, dtype_name)
    dtype = getattr(xp, dtype_name)
    builtin = find_castable_builtin_for_dtype(xp, dtype)
    assert_all_examples(xps.from_dtype(dtype), lambda v: isinstance(v, builtin))


@pytest.mark.parametrize("dtype_name", DTYPE_NAMES)
def test_produces_castable_instances_from_name(xp, xps, dtype_name):
    """Strategies inferred by dtype name generate values of a builtin type
    castable to the dtype."""
    skip_on_unsupported_dtype(xp, dtype_name)
    dtype = getattr(xp, dtype_name)
    builtin = find_castable_builtin_for_dtype(xp, dtype)
    assert_all_examples(xps.from_dtype(dtype_name), lambda v: isinstance(v, builtin))


@pytest.mark.parametrize("dtype_name", DTYPE_NAMES)
def test_passing_inferred_strategies_in_arrays(xp, xps, dtype_name):
    """Inferred strategies usable in arrays strategy."""
    skip_on_unsupported_dtype(xp, dtype_name)
    elements = xps.from_dtype(dtype_name)
    find_any(xps.arrays(dtype_name, 10, elements=elements))


@pytest.mark.parametrize(
    "dtype, kwargs, predicate",
    [
        # Floating point: bounds, exclusive bounds, and excluding nonfinites
        ("float32", {"min_value": 1, "max_value": 2}, lambda x: 1 <= x <= 2),
        (
            "float32",
            {"min_value": 1, "max_value": 2, "exclude_min": True, "exclude_max": True},
            lambda x: 1 < x < 2,
        ),
        ("float32", {"allow_nan": False}, lambda x: not math.isnan(x)),
        ("float32", {"allow_infinity": False}, lambda x: not math.isinf(x)),
        ("float32", {"allow_nan": False, "allow_infinity": False}, math.isfinite),
        # Integer bounds, limited to the representable range
        ("int8", {"min_value": -1, "max_value": 1}, lambda x: -1 <= x <= 1),
        ("uint8", {"min_value": 1, "max_value": 2}, lambda x: 1 <= x <= 2),
    ],
)
def test_from_dtype_with_kwargs(xp, xps, dtype, kwargs, predicate):
    """Strategies inferred with kwargs generate values in bounds."""
    skip_on_unsupported_dtype(xp, dtype)
    strat = xps.from_dtype(dtype, **kwargs)
    assert_all_examples(strat, predicate)


def test_can_minimize_floats(xp, xps):
    """Inferred float strategy minimizes to a good example."""
    smallest = minimal(xps.from_dtype(xp.float32), lambda n: n >= 1.0)
    assert smallest == 1


smallest_normal = width_smallest_normals[32]
subnormal_from_dtype_kwargs = [
    {},
    {"min_value": -1},
    {"max_value": 1},
    pytest.param(
        {"min_value": -1, "max_value": 1},
        marks=pytest.mark.skip(
            reason="FixedBoundFloatStrategy(0, 1) rarely generates subnormals"
        ),
    ),
]


@pytest.mark.parametrize("kwargs", subnormal_from_dtype_kwargs)
def test_generate_subnormals_for_non_ftz_float32(xp, xps, kwargs):
    if flushes_to_zero(xp, width=32):
        pytest.skip("Subnormals should not be generated for FTZ builds")
    strat = xps.from_dtype(xp.float32, **kwargs)
    find_any(
        strat.filter(lambda n: n != 0), lambda n: -smallest_normal < n < smallest_normal
    )


@pytest.mark.parametrize("kwargs", subnormal_from_dtype_kwargs)
def test_does_not_generate_subnormals_for_ftz_float32(xp, xps, kwargs):
    if not flushes_to_zero(xp, width=32):
        pytest.skip("Subnormals should be generated for non-FTZ builds")
    strat = xps.from_dtype(xp.float32, **kwargs)
    assert_no_examples(
        strat.filter(lambda n: n != 0), lambda n: -smallest_normal < n < smallest_normal
    )
