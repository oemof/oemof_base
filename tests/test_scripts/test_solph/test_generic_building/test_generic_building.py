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
from types import SimpleNamespace

from oemof.tools import economics
from oemof.tools import logger
from oemof.solph import views

from oemof import solph

##########################################################################
# Initialize the energy system and read/calculate necessary parameters
##########################################################################

logger.define_logging()
logging.info("Initialize the energy system")

tindex = pd.date_range("2022-01-01", periods=8, freq="H")

energysystem = solph.EnergySystem(
    timeindex=tindex,
    infer_last_interval=False,
)
solar_gains = [3000, 4000, 1000 ,300, 300, 200, 100, 50]
internal_gains = [100, 100, 100, 100, 100, 100, 100, 100]
t_outside = [22, 19, 16, 15, 14, 10, 7, 4]
building_config = SimpleNamespace(
                                total_internal_area=499.95,
                                h_ve=55.55,
                                h_tr_w=51.52,
                                h_tr_em=412.05866346891787,
                                h_tr_is=1724.8275,
                                mass_area=277.75,
                                h_tr_ms=2527.525,
                                c_m=18331500.0,
                                floor_area=111.1,
                                heat_transfer_coefficient_ventilation=0.51,
                                total_air_change_rate=0.6
                            )

##########################################################################
# Create oemof objects
##########################################################################

logging.info("Create oemof objects")

# create electricity bus
b_elect = solph.buses.Bus(label="electricity")
energysystem.add(b_elect)

# create heat and cooling flow
b_heat = solph.buses.Bus(label="b_heat")
energysystem.add(b_heat)
b_cool = solph.buses.Bus(label="b_cool")
energysystem.add(b_cool)

# create electrical source
energysystem.add(
    solph.components.Source(
        label="elect_from_grid",
        outputs={b_elect: solph.flows.Flow(variable_costs=30)},
    )
)
'''
energysystem.add(
    solph.components.Sink(
        label="elect_into_grid",
        inputs={b_elect: solph.flows.Flow(variable_costs=10)},
    )
)
'''
# create electrical heating and cooling device
energysystem.add(
    solph.components.Transformer(
        label="ElectricalHeater",
        inputs={b_elect: solph.flows.Flow()},
        outputs={b_heat: solph.flows.Flow()},
        conversion_factors={b_elect: 1},
    )
)
energysystem.add(
    solph.components.Transformer(
        label="ElectricalCooler",
        inputs={b_cool: solph.flows.Flow()},
        outputs={b_elect: solph.flows.Flow()},
        conversion_factors={b_elect: -1},
    )
)

# create single family house building object
energysystem.add(
    solph.components.experimental.GenericBuilding(
        label="GenericBuilding",
        inputs={b_heat: solph.flows.Flow(variable_costs=0)},
        outputs={b_cool: solph.flows.Flow(variable_costs=0)},
        solar_gains=solar_gains,
        t_outside=t_outside,
        internal_gains=internal_gains,
        t_set_heating=20,
        t_set_cooling=22,
        building_config=building_config,
        t_inital=21,
    )
)

energysystem.add(b_heat, b_cool, b_elect)

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
energysystem.results["main"] = solph.processing.results(om)
energysystem.results["meta"] = solph.processing.meta_results(om)
results = energysystem.results["main"]
custom_building = views.node(results, "GenericBuilding")

print(2)

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
    assert flows["storage-None"][7] == pytest.approx(first_input)
