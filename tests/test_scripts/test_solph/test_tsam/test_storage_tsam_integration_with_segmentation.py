# -*- coding: utf-8 -*-

r"""
General description:
---------------------

The example models the following energy system:

                input/output   bel
                     |          |
 wind(FixedSource)   |--------->|
                     |          |
 demand(Sink)        |<---------|
                     |          |
 storage(Storage)    |<---------|
                     |--------->|

An initial SOC of zero leads to infeasible solution, as last inter SOC has to
match first inter SOC.
Following equations have to be fulfilled:
:math:`F_{el,st}[0] = F_{el,st}[6]`
:math:`SOC_{init} * discharge + F_{el,st}[0] =`
:math:`\sum_{i=1}^{n=5}F_{st,el}[i]/eff_{out}/(1 - discharge)^i`
:math:`F_{el,st}[6] = (SOC_{init} + F_{el,st}[5]/eff_{out}) / (1 - discharge)`

This file is part of project oemof (github.com/oemof/oemof). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location oemof/tests/test_scripts/test_solph/
test_storage_investment/test_storage_investment.py

SPDX-License-Identifier: MIT
"""

import logging

import pandas as pd
import pytest
from oemof.tools import logger

from oemof import solph

##########################################################################
# Initialize the energy system and read/calculate necessary parameters
##########################################################################

logger.define_logging()
logging.info("Initialize the energy system")

tindex_original = pd.date_range("2022-01-01", periods=16, freq="H")
tindex = pd.date_range("2022-01-01", periods=4, freq="H")

energysystem = solph.EnergySystem(
    timeindex=tindex,
    periods=[tindex],
    tsa_parameters=[
        {
            "timesteps_per_period": 4,
            "order": [0, 1, 1, 0],
            "segments": {(0, 0): 1, (0, 1): 3, (1, 0): 2, (1, 1): 2},
        },
    ],
    infer_last_interval=False,
)

##########################################################################
# Create oemof objects
##########################################################################

logging.info("Create oemof objects")

# create electricity bus
bel = solph.Bus(label="electricity")
energysystem.add(bel)

# create fixed source object representing wind power plants
wind = solph.components.Source(
    label="wind",
    outputs={bel: solph.Flow(fix=[1000, 0, 0, 50], nominal_value=1)},
)

# create simple sink object representing the electrical demand
demand = solph.components.Sink(
    label="demand",
    inputs={
        bel: solph.Flow(
            fix=[100] * 4,
            nominal_value=1,
        )
    },
)

# create storage object representing a battery
storage = solph.components.GenericStorage(
    label="storage",
    nominal_storage_capacity=2000,
    inputs={bel: solph.Flow()},
    outputs={bel: solph.Flow()},
    loss_rate=0.01,
    inflow_conversion_factor=0.9,
    outflow_conversion_factor=0.8,
)

excess = solph.components.Sink(
    label="excess",
    inputs={bel: solph.Flow()},
)

energysystem.add(wind, demand, storage, excess)

##########################################################################
# Optimise the energy system
##########################################################################

logging.info("Optimise the energy system")

# initialise the operational model
om = solph.Model(energysystem)
om.write("model.lp", io_options={"symbolic_solver_labels": True})

# if tee_switch is true solver messages will be displayed
logging.info("Solve the optimization problem")
om.solve(solver="cbc", solve_kwargs={"tee": True})

##########################################################################
# Check and plot the results
##########################################################################

# check if the new result object is working for custom components
results = solph.processing.results(om)

# Concatenate flows:
flows = pd.concat([flow["sequences"] for flow in results.values()], axis=1)
flows.columns = [
    f"{oemof_tuple[0]}-{oemof_tuple[1]}" for oemof_tuple in results.keys()
]

# Solving equations from above, needed initial SOC is as follows:
first_input = (
    (3 * 100 * 1 / 0.8) / ((1 - 0.01) ** 3)
    + (2 * 100 * 1 / 0.8) / ((1 - 0.01) ** (2 + 3))
    + (2 * 50 * 1 / 0.8) / ((1 - 0.01) ** (2 + 5))
    + (2 * 100 * 1 / 0.8) / ((1 - 0.01) ** (2 + 7))
    + (2 * 50 * 1 / 0.8) / ((1 - 0.01) ** (2 + 9))
)
last_output = (3 * 100 * 1 / 0.8) / 0.99**3
init_soc = (first_input - last_output) / (1 / 0.99**3 + 0.99)


def test_storage_input():
    assert flows["electricity-storage"][0] == pytest.approx(
        (first_input - 0.99 * init_soc) / 0.9
    )
    assert flows["electricity-storage"][1] == 0
    assert flows["electricity-storage"][2] == 0
    assert flows["electricity-storage"][3] == 0
    assert flows["electricity-storage"][4] == 0
    assert flows["electricity-storage"][5] == 0
    assert flows["electricity-storage"][6] == 0
    assert flows["electricity-storage"][7] == 0
    assert flows["electricity-storage"][8] == 0
    assert flows["electricity-storage"][9] == 0
    assert flows["electricity-storage"][10] == 0
    assert flows["electricity-storage"][11] == 0
    assert flows["electricity-storage"][12] == flows["electricity-storage"][0]
    assert flows["electricity-storage"][13] == 0
    assert flows["electricity-storage"][14] == 0
    assert flows["electricity-storage"][15] == 0


def test_storage_output():
    assert flows["storage-electricity"][0] == 0
    assert flows["storage-electricity"][1] == 100
    assert flows["storage-electricity"][2] == 100
    assert flows["storage-electricity"][3] == 100
    assert flows["storage-electricity"][4] == 100
    assert flows["storage-electricity"][5] == 100
    assert flows["storage-electricity"][6] == 50
    assert flows["storage-electricity"][7] == 50
    assert flows["storage-electricity"][8] == 100
    assert flows["storage-electricity"][9] == 100
    assert flows["storage-electricity"][10] == 50
    assert flows["storage-electricity"][11] == 50
    assert flows["storage-electricity"][12] == 0
    assert flows["storage-electricity"][13] == 100
    assert flows["storage-electricity"][14] == 100
    assert flows["storage-electricity"][15] == 100


def test_soc():
    assert flows["storage-None"][0] == pytest.approx(init_soc)
    assert flows["storage-None"][1] == pytest.approx(
        first_input,
        abs=1e-2,
    )
    assert flows["storage-None"][4] == pytest.approx(
        (2 * 100 * 1 / 0.8) / ((1 - 0.01) ** 2)
        + (2 * 50 * 1 / 0.8) / ((1 - 0.01) ** (2 + 2))
        + (2 * 100 * 1 / 0.8) / ((1 - 0.01) ** (2 + 4))
        + (2 * 50 * 1 / 0.8) / ((1 - 0.01) ** (2 + 6)),
        abs=1e-2,
    )
    assert flows["storage-None"][6] == pytest.approx(
        (2 * 50 * 1 / 0.8) / ((1 - 0.01) ** 2)
        + (2 * 100 * 1 / 0.8) / ((1 - 0.01) ** (2 + 2))
        + (2 * 50 * 1 / 0.8) / ((1 - 0.01) ** (2 + 4)),
        abs=1e-2,
    )
    assert flows["storage-None"][8] == pytest.approx(
        (2 * 100 * 1 / 0.8) / ((1 - 0.01) ** 2)
        + (2 * 50 * 1 / 0.8) / ((1 - 0.01) ** (2 * 2)),
        abs=1e-2,
    )
    assert flows["storage-None"][10] == pytest.approx(
        (2 * 50 * 1 / 0.8) / ((1 - 0.01) ** 2), abs=1e-2
    )
    assert flows["storage-None"][12] == pytest.approx(0, abs=1e-2)
    assert flows["storage-None"][13] == pytest.approx(
        (init_soc + (3 * 100 * 1 / 0.8)) / 0.99**3
    )
    assert flows["storage-None"][15] == pytest.approx(
        init_soc
        + (flows["storage-None"][13] - init_soc) / 3  # linear interpolation
    )
