# -*- coding: utf-8 -*-

"""
General description
-------------------
This example shows how to perform a capacity optimization for
an energy system with storage. The following energy system is modeled:

.. code-block:: text

                    input/output  bgas     bel
                         |          |        |
                         |          |        |
     wind(FixedSource)   |------------------>|
                         |          |        |
     pv(FixedSource)     |------------------>|
                         |          |        |
     gas_resource        |--------->|        |
     (Commodity)         |          |        |
                         |          |        |
     demand(Sink)        |<------------------|
                         |          |        |
                         |          |        |
     pp_gas(Converter)   |<---------|        |
                         |------------------>|
                         |          |        |
     storage(Storage)    |<------------------|
                         |------------------>|


The example exists in four variations. The following parameters describe
the main setting for the optimization variation 2:

- optimize gas_resource and storage
- set installed capacities for wind and pv
- set investment cost for storage
- set gas price for kWh

Results show a higher renewable energy share than in variation 1
(78% compared to 51%) due to preinstalled renewable capacities.
Storage is not installed as the gas resource is cheaper.

.. tip::

    Have a look at different parameter settings. There are four variations
    of this example in the same folder.

Code
----
Download source code: :download:`v2_invest_optimize_only_gas_and_storage.py </../examples/storage_investment/v2_invest_optimize_only_gas_and_storage.py>`

.. dropdown:: Click to display code

    .. literalinclude:: /../examples/storage_investment/v2_invest_optimize_only_gas_and_storage.py
        :language: python
        :lines: 83-

Data
----
Download data: :download:`storage_investment.csv </../examples/storage_investment/storage_investment.csv>`

Installation requirements
-------------------------

This example requires oemof.solph (v0.5.x), install by:

.. code:: bash

    pip install oemof.solph[examples]


License
-------
`MIT license <https://github.com/oemof/oemof-solph/blob/dev/LICENSE>`_

"""


###############################################################################
# Imports
###############################################################################

import logging
import os
import pprint as pp
import warnings

import pandas as pd
from oemof.tools import economics
from oemof.tools import logger

from oemof import solph


def main():
    # Read data file
    filename = os.path.join(
        os.path.dirname(__file__), "storage_investment.csv"
    )
    try:
        data = pd.read_csv(filename)
    except FileNotFoundError:
        msg = "Data file not found: {0}. Only one value used!"
        warnings.warn(msg.format(filename), UserWarning)
        data = pd.DataFrame(
            {"pv": [0.3, 0.5], "wind": [0.6, 0.8], "demand_el": [500, 600]}
        )

    number_timesteps = len(data)

    ##########################################################################
    # Initialize the energy system and read/calculate necessary parameters
    ##########################################################################

    logger.define_logging()
    logging.info("Initialize the energy system")
    date_time_index = solph.create_time_index(2012, number=number_timesteps)

    energysystem = solph.EnergySystem(
        timeindex=date_time_index, infer_last_interval=False
    )

    price_gas = 0.04

    # If the period is one year the equivalent periodical costs (epc) of an
    # investment are equal to the annuity. Use oemof's economic tools.
    # It is assumed that the investment object in storage capacity entails the
    # costs for investment into both input and output capacity
    epc_storage = economics.annuity(capex=1000, n=20, wacc=0.05)

    ##########################################################################
    # Create oemof objects
    ##########################################################################

    logging.info("Create oemof objects")
    # create natural gas bus
    bgas = solph.Bus(label="natural_gas")

    # create electricity bus
    bel = solph.Bus(label="electricity")

    energysystem.add(bgas, bel)

    # create excess component for the electricity bus to allow overproduction
    excess = solph.components.Sink(
        label="excess_bel", inputs={bel: solph.Flow()}
    )

    # create source object representing the gas commodity
    gas_resource = solph.components.Source(
        label="rgas", outputs={bgas: solph.Flow(variable_costs=price_gas)}
    )

    # create fixed source object representing wind power plants
    wind = solph.components.Source(
        label="wind",
        outputs={bel: solph.Flow(fix=data["wind"], nominal_capacity=1000000)},
    )

    # create fixed source object representing pv power plants
    pv = solph.components.Source(
        label="pv",
        outputs={bel: solph.Flow(fix=data["pv"], nominal_capacity=600000)},
    )

    # create simple sink object representing the electrical demand
    demand = solph.components.Sink(
        label="demand",
        inputs={bel: solph.Flow(fix=data["demand_el"], nominal_capacity=1)},
    )

    # create simple Converter object representing a gas power plant
    pp_gas = solph.components.Converter(
        label="pp_gas",
        inputs={bgas: solph.Flow()},
        outputs={bel: solph.Flow(nominal_capacity=10e10, variable_costs=0)},
        conversion_factors={bel: 0.58},
    )

    # create storage object representing a battery
    storage = solph.components.GenericStorage(
        label="storage",
        inputs={bel: solph.Flow(variable_costs=0.0001)},
        outputs={bel: solph.Flow()},
        loss_rate=0.00,
        initial_storage_level=0,
        invest_relation_input_capacity=1 / 6,  # input flow is 1/6 of capacity
        invest_relation_output_capacity=1
        / 6,  # output flow is 1/6 of capacity
        inflow_conversion_factor=1,
        outflow_conversion_factor=0.8,
        nominal_capacity=solph.Investment(ep_costs=epc_storage),
    )

    energysystem.add(excess, gas_resource, wind, pv, demand, pp_gas, storage)

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

    electricity_bus = solph.views.node(results, "electricity")

    meta_results = solph.processing.meta_results(om)
    pp.pprint(meta_results)

    # returns a pandas Series with all scalar values (investment, total) of
    # components connected to the electricity bus
    my_results = electricity_bus["scalars"]

    # installed capacity of storage in GWh
    my_results["storage_invest_GWh"] = (
        results[(storage, None)]["scalars"]["invest"] / 1e6
    )

    # resulting renewable energy share
    my_results["res_share"] = (
        1
        - results[(pp_gas, bel)]["sequences"].sum().iloc[0]
        / results[(bel, demand)]["sequences"].sum().iloc[0]
    )

    pp.pprint(my_results)


if __name__ == "__main__":
    main()
