# -*- coding: utf-8 -

"""Test the created constraints against approved constraints.

This file is part of project oemof (github.com/oemof/oemof). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location oemof/tests/test_solph_network_classes.py

SPDX-License-Identifier: MIT
"""

import warnings

import pytest
from oemof.tools.debugging import SuspiciousUsageWarning

from oemof import solph


class TestTransformerClass:
    @classmethod
    def setup_class(cls):
        """Setup default values"""
        cls.bus = solph.Bus()
        warnings.filterwarnings("ignore", category=SuspiciousUsageWarning)

    @classmethod
    def teardown_class(cls):
        warnings.filterwarnings("always", category=SuspiciousUsageWarning)

    def test_empty_transformer(self):
        transf = solph.Transformer()
        assert isinstance(transf.conversion_factors, dict)
        assert len(transf.conversion_factors.keys()) == 0

    def test_default_conversion_factor(self):
        transf = solph.Transformer(inputs={self.bus: solph.Flow()})
        assert transf.conversion_factors[self.bus][2] == 1

    def test_sequence_conversion_factor_from_scalar(self):
        transf = solph.Transformer(inputs={self.bus: solph.Flow()},
                                   conversion_factors={self.bus: 2})
        assert transf.conversion_factors[self.bus][6] == 2

    def test_sequence_conversion_factor_from_list_correct_length(self):
        transf = solph.Transformer(inputs={self.bus: solph.Flow()},
                                   conversion_factors={self.bus: [2]})
        assert len(transf.conversion_factors[self.bus]) == 1

    def test_sequence_conversion_factor_from_list_wrong_length(self):
        transf = solph.Transformer(inputs={self.bus: solph.Flow()},
                                   conversion_factors={self.bus: [2]})
        with pytest.raises(IndexError):
            self.a = transf.conversion_factors[self.bus][6]


def test_wrong_combination_invest_and_nominal_value():
    msg = "Using the investment object the nominal_value"
    with pytest.raises(ValueError, match=msg):
        solph.Flow(investment=solph.Investment(), nominal_value=4)


def test_wrong_combination_of_options():
    msg = "Investment flows cannot be combined with nonconvex flows!"
    with pytest.raises(ValueError, match=msg):
        solph.Flow(investment=solph.Investment(), nonconvex=solph.NonConvex())


def test_error_of_deprecated_fixed_costs():
    msg = "The `fixed_costs` attribute has been removed with v0.2!"
    with pytest.raises(AttributeError, match=msg):
        solph.Flow(fixed_costs=34)


def test_flow_with_fix_and_min_max():
    msg = "It is not allowed to define min/max if fix is defined."
    with pytest.raises(AttributeError, match=msg):
        solph.Flow(fix=[1, 3], min=[0, 5])
    with pytest.raises(AttributeError, match=msg):
        solph.Flow(fix=[1, 3], max=[0, 5])
    with pytest.raises(AttributeError, match=msg):
        solph.Flow(fix=[1, 3], max=[0, 5], min=[4, 9])


def test_min_max_values_for_bidirectional_flow():
    a = solph.Flow(bidirectional=True)  # use default values
    b = solph.Flow(bidirectional=True, min=-0.9, max=0.9)
    assert a.bidirectional
    assert a.max[0] == 1
    assert a.min[0] == -1
    assert b.max[0] == 0.9
    assert b.min[0] == -0.9


def test_deprecated_actual_value():
    """Deprecated error for actual_warning is not raised correctly."""
    msg = "The `actual_value` attribute has been renamed to `fix`"
    with pytest.raises(AttributeError, match=msg):
        solph.Flow(actual_value=5)


def test_warning_fixed_still_used():
    """If fixed attribute is still used, a warning is raised."""
    msg = ("The `fixed` attribute is deprecated.\nIf you have defined "
           "the `fix` attribute the flow variable will be fixed.\n"
           "The `fixed` attribute does not change anything.")
    with warnings.catch_warnings(record=True) as w:
        solph.Flow(fixed=True)
        assert len(w) != 0
        assert msg == str(w[-1].message)


def test_missing_schedule_costs_values():
    """
    If schedule attribute is used and negative and positive schedule costs
    are missing, an error will be raised.
    """
    msg = ("The schedule attribute and the associated costs "
           "need to be used in combination. \n Please set "
           "the `schedule_cost_neg` and `schedule_cost_pos` "
           "attributes of the flow.")
    with pytest.raises(ValueError, match=msg):
        solph.Flow(schedule=[54, 74, 90])


def test_missing_schedule_neg_cost_value():
    msg = ("The schedule attribute and the associated costs "
           "need to be used in combination. \n Please set "
           "the `schedule_cost_neg` and `schedule_cost_pos` "
           "attributes of the flow.")
    with pytest.raises(ValueError, match=msg):
        solph.Flow(schedule=[54, 74, 90], schedule_cost_pos=1000)


def test_missing_schedule_pos_cost_value():
    msg = ("The schedule attribute and the associated costs "
           "need to be used in combination. \n Please set "
           "the `schedule_cost_neg` and `schedule_cost_pos` "
           "attributes of the flow.")
    with pytest.raises(ValueError, match=msg):
        solph.Flow(schedule=[54, 74, 90], schedule_cost_neg=1000)
