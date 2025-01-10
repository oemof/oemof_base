# -*- coding: utf-8 -

"""Basic tests.

This file is part of project oemof (github.com/oemof/oemof). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location oemof/tests/basic_tests.py

SPDX-License-Identifier: MIT
"""

import warnings

import pandas as pd
import pytest

from oemof import solph


def test_infeasible_model_warning():
    es = solph.EnergySystem(timeincrement=[1])
    bel = solph.buses.Bus(label="bus")
    es.add(bel)
    es.add(
        solph.components.Sink(
            inputs={bel: solph.flows.Flow(nominal_capacity=5, fix=[1])}
        )
    )
    es.add(
        solph.components.Source(
            outputs={
                bel: solph.flows.Flow(nominal_capacity=4, variable_costs=5)
            }
        )
    )
    m = solph.Model(es)
    with warnings.catch_warnings(record=False) as w:
        m.solve(solver="cbc", allow_nonoptimal=True)
        assert "The solver did not return an optimal solution" in str(
            w[0].message
        )


def test_infeasible_model_error():
    es = solph.EnergySystem(timeincrement=[1])
    bel = solph.buses.Bus(label="bus")
    es.add(bel)
    es.add(
        solph.components.Sink(
            inputs={bel: solph.flows.Flow(nominal_value=5, fix=[1])}
        )
    )
    es.add(
        solph.components.Source(
            outputs={bel: solph.flows.Flow(nominal_value=4, variable_costs=5)}
        )
    )
    m = solph.Model(es)
    try:
        m.solve(solver="cbc", allow_nonoptimal=False)
    except Exception as e:
        assert "The solver did not return an optimal solution" in str(e)


def test_unbounded_model():
    es = solph.EnergySystem(timeincrement=[1])
    bel = solph.buses.Bus(label="bus")
    es.add(bel)
    # Add a Sink with a higher demand
    es.add(solph.components.Sink(inputs={bel: solph.flows.Flow()}))

    # Add a Source with a very high supply
    es.add(
        solph.components.Source(
            outputs={bel: solph.flows.Flow(variable_costs=-5)}
        )
    )
    m = solph.Model(es)

    try:
        m.solve(solver="cbc", allow_nonoptimal=False)
    except Exception as e:
        assert "The solver did not return an optimal solution" in str(e)


@pytest.mark.filterwarnings(
    "ignore:Ensure that your timeindex and timeincrement are"
    " consistent.:UserWarning"
)
@pytest.mark.filterwarnings(
    "ignore:CAUTION! You specified the 'periods' attribute:UserWarning"
)
def test_multi_period_default_discount_rate():
    """Test error being thrown for default multi-period discount rate"""
    timeindex = pd.date_range(start="2017-01-01", periods=100, freq="D")
    es = solph.EnergySystem(
        timeindex=timeindex,
        timeincrement=[1] * len(timeindex),
        periods=[timeindex],
        infer_last_interval=False,
    )
    bel = solph.buses.Bus(label="bus")
    es.add(bel)
    es.add(
        solph.components.Sink(
            label="sink",
            inputs={
                bel: solph.flows.Flow(
                    nominal_capacity=5, fix=[1] * len(timeindex)
                )
            },
        )
    )
    es.add(
        solph.components.Source(
            label="source",
            outputs={
                bel: solph.flows.Flow(nominal_capacity=4, variable_costs=5)
            },
        )
    )
    msg = (
        "By default, a discount_rate of 0.02 is used for a multi-period model."
    )
    with warnings.catch_warnings(record=True) as w:
        solph.Model(es)
        assert msg in str(w[0].message)
