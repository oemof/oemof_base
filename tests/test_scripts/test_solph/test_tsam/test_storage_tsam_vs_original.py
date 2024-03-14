# -*- coding: utf-8 -*-

"""
General description:
---------------------

The example models the same setup as in test_storage_tsam_integration,
but instead of aggregating timeseries, timeseries are left untouched.
Nevertheless, storage input/output and SOC should equal TSAM example.

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

tindex = pd.date_range("2022-01-01", periods=8, freq="H")

energysystem = solph.EnergySystem(
    timeindex=tindex,
    infer_last_interval=True,
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
    outputs={
        bel: solph.Flow(fix=[1000, 0, 0, 50, 0, 50, 1000, 0], nominal_value=1)
    },
)

# create simple sink object representing the electrical demand
demand = solph.components.Sink(
    label="demand",
    inputs={
        bel: solph.Flow(
            fix=[100] * 8,
            nominal_value=1,
        )
    },
)

# Solving equations from above, needed initial SOC is as follows:
first_input = (
    (100 * 1 / 0.8) / (1 - 0.01)
    + (100 * 1 / 0.8) / (1 - 0.01) ** 2
    + (50 * 1 / 0.8) / (1 - 0.01) ** 3
    + (100 * 1 / 0.8) / (1 - 0.01) ** 4
    + (50 * 1 / 0.8) / (1 - 0.01) ** 5
)
last_output = (100 * 1 / 0.8) / 0.99
init_soc = (first_input - last_output) / (1 / 0.99 + 0.99)

# create storage object representing a battery
storage = solph.components.GenericStorage(
    label="storage",
    nominal_storage_capacity=2000,
    initial_storage_level=init_soc / 2000,
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


def test_storage_input():
    assert flows["electricity-storage"][0] == pytest.approx(
        (first_input - 0.99 * init_soc) / 0.9
    )
    assert flows["electricity-storage"][1] == 0
    assert flows["electricity-storage"][2] == 0
    assert flows["electricity-storage"][3] == 0
    assert flows["electricity-storage"][4] == 0
    assert flows["electricity-storage"][5] == 0
    assert flows["electricity-storage"][6] == flows["electricity-storage"][0]
    assert flows["electricity-storage"][7] == 0


def test_storage_output():
    assert flows["storage-electricity"][0] == 0
    assert flows["storage-electricity"][1] == 100
    assert flows["storage-electricity"][2] == 100
    assert flows["storage-electricity"][3] == 50
    assert flows["storage-electricity"][4] == 100
    assert flows["storage-electricity"][5] == 50
    assert flows["storage-electricity"][6] == 0
    assert flows["storage-electricity"][7] == 100


def test_soc():
    assert flows["storage-None"][0] == pytest.approx(init_soc)
    assert flows["storage-None"][1] == pytest.approx(
        (100 * 1 / 0.8) / (1 - 0.01)
        + (100 * 1 / 0.8) / (1 - 0.01) ** 2
        + (50 * 1 / 0.8) / (1 - 0.01) ** 3
        + (100 * 1 / 0.8) / (1 - 0.01) ** 4
        + (50 * 1 / 0.8) / (1 - 0.01) ** 5,
        abs=1e-2,
    )
    assert flows["storage-None"][2] == pytest.approx(
        (100 * 1 / 0.8) / (1 - 0.01)
        + (50 * 1 / 0.8) / (1 - 0.01) ** 2
        + (100 * 1 / 0.8) / (1 - 0.01) ** 3
        + (50 * 1 / 0.8) / (1 - 0.01) ** 4,
        abs=1e-2,
    )
    assert flows["storage-None"][3] == pytest.approx(
        (50 * 1 / 0.8) / (1 - 0.01)
        + (100 * 1 / 0.8) / (1 - 0.01) ** 2
        + (50 * 1 / 0.8) / (1 - 0.01) ** 3,
        abs=1e-2,
    )
    assert flows["storage-None"][4] == pytest.approx(
        (100 * 1 / 0.8) / (1 - 0.01) + (50 * 1 / 0.8) / (1 - 0.01) ** 2,
        abs=1e-2,
    )
    assert flows["storage-None"][5] == pytest.approx(
        (50 * 1 / 0.8) / (1 - 0.01), abs=1e-2
    )
    assert flows["storage-None"][6] == pytest.approx(0, abs=1e-2)
    assert flows["storage-None"][7] == pytest.approx(
        (init_soc + (100 * 1 / 0.8)) / 0.99
    )
