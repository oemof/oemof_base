# -*- coding: utf-8 -*-

"""
General description:
---------------------
This tests shall prove, that TSAM weighting is reflected in full load hours and
variable costs.

The example models the following energy system:

                input/output   bel
                     |          |
 Source              |--------->|
                     |          |
 Sink                |<---------|

whereby source is defined with full load hours.

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

tindex_original = pd.date_range("2022-01-01", periods=8, freq="H")
tindex = pd.date_range("2022-01-01", periods=4, freq="H")

energysystem = solph.EnergySystem(
    timeindex=tindex,
    timeincrement=[1] * len(tindex),
    periods=[tindex],
    tsa_parameters=[
        {
            "timesteps_per_period": 2,
            "order": [1, 1, 1, 0],
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
source = solph.components.Source(
    label="source",
    outputs={
        bel: solph.Flow(
            full_load_time_min=0.8,
            full_load_time_max=0.8,
            nominal_value=100,
            variable_costs=[0.1, 0.2, 0.3, 0.4],
        )
    },
)

# create simple sink object representing the electrical demand
excess = solph.components.Sink(
    label="excess",
    inputs={bel: solph.Flow()},
)

energysystem.add(source, excess)

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
meta_results = solph.processing.meta_results(om)

# Concatenate flows:
flows = pd.concat([flow["sequences"] for flow in results.values()], axis=1)
flows.columns = [
    f"{oemof_tuple[0]}-{oemof_tuple[1]}" for oemof_tuple in results.keys()
]


def test_weighted_full_load_hours():
    """Tests if full load hours are weighted accordingly to TSAM occurrences"""
    assert flows["source-electricity"].sum() == pytest.approx(80)


def test_weighted_variable_costs():
    """Tests if variable costs are weighted accordingly to TSAM occurrences"""
    assert meta_results["objective"] == (
        flows["source-electricity"][6] * 0.1
        + flows["source-electricity"][7] * 0.2
        + (
            flows["source-electricity"][0] * 0.3
            + flows["source-electricity"][1] * 0.4
        )
        * 3
    )
