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

The example describes the use of time series aggregation
methods for seasonal storages in oemof. For this the package tsam is used
for this purpose, which is developed by Forschungszentrum Jülich. For a more detailed
explanation we refer to the paper "Time series aggregation for energy
system design: Modeling seasonal storage" by Kotzur et. al.
https://www.sciencedirect.com/science/article/pii/S0306261918300242


The optimization aim is:
- optimize wind, pv, gas_resource and seasonal storage
- set investment cost for wind, pv and storage
- set gas price for kWh

.. tip::

    Have a look at the Generic Storage class, to understand better
    the idea of the implementation of inter and intra storage contents.
    For this purpose a function to get timesteps from
    tsam_timesteps is added in _models.

Code
----
Download source code: :download:`v1_invest_optimize_all_technologies.py </../examples/storage_investment/v1_invest_optimize_all_technologies.py>`

.. dropdown:: Click to display code

    .. literalinclude:: /../examples/storage_investment/v1_invest_optimize_all_technologies.py
        :language: python
        :lines: 80-

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
import tsam.timeseriesaggregation as tsam
from oemof.tools import economics
from oemof.tools import logger

from oemof import solph


def main():
    # Read data file
    filename = os.path.join(
        os.getcwd(), "../storage_investment/storage_investment.csv"
    )
    try:
        data = pd.read_csv(filename)
    except FileNotFoundError:
        msg = "Data file not found: {0}. Only one value used!"
        warnings.warn(msg.format(filename), UserWarning)
        data = pd.DataFrame(
            {"pv": [0.3, 0.5], "wind": [0.6, 0.8], "demand_el": [500, 600]}
        )

    data = pd.concat([data, data], ignore_index=True)
    data["wind"].iloc[8760 - 24 : 8760] = 0
    data["wind"].iloc[8760 * 2 - 24 : 8760] = 0
    data["pv"].iloc[8760 - 24 : 8760] = 0
    data["pv"].iloc[8760 * 2 - 24 : 8760] = 0

    ##########################################################################
    # Initialize the energy system and read/calculate necessary parameters
    ##########################################################################

    logger.define_logging()
    logging.info("Initialize the energy system")

    t1 = pd.date_range("2022-01-01", periods=8760, freq="H")
    t2 = pd.date_range("2033-01-01", periods=8760, freq="H")
    tindex = t1.append(t2)

    data.index = tindex
    del data["timestep"]

    typical_periods = 40
    hours_per_period = 24

    aggregation1 = tsam.TimeSeriesAggregation(
        timeSeries=data.iloc[:8760],
        noTypicalPeriods=typical_periods,
        hoursPerPeriod=hours_per_period,
        clusterMethod="k_means",
        sortValues=False,
        rescaleClusterPeriods=False,
        extremePeriodMethod="replace_cluster_center",
        addPeakMin=["wind", "pv"],
        representationMethod="durationRepresentation",
    )
    aggregation1.createTypicalPeriods()
    aggregation2 = tsam.TimeSeriesAggregation(
        timeSeries=data.iloc[8760:],
        noTypicalPeriods=typical_periods,
        hoursPerPeriod=hours_per_period,
        clusterMethod="hierarchical",
        sortValues=False,
        rescaleClusterPeriods=False,
        extremePeriodMethod="replace_cluster_center",
        addPeakMin=["wind", "pv"],
        representationMethod="durationRepresentation",
    )
    aggregation2.createTypicalPeriods()

    t1_agg = pd.date_range(
        "2022-01-01", periods=typical_periods * hours_per_period, freq="H"
    )
    t2_agg = pd.date_range(
        "2033-01-01", periods=typical_periods * hours_per_period, freq="H"
    )
    tindex_agg = t1_agg.append(t2_agg)

    energysystem = solph.EnergySystem(
        timeindex=tindex_agg,
        timeincrement=[1] * len(tindex_agg),
        periods=[t1_agg, t2_agg],
        tsa_parameters=[
            {
                "timesteps_per_period": aggregation1.hoursPerPeriod,
                "order": aggregation1.clusterOrder,
                "timeindex": aggregation1.timeIndex,
            },
            {
                "timesteps_per_period": aggregation2.hoursPerPeriod,
                "order": aggregation2.clusterOrder,
                "timeindex": aggregation2.timeIndex,
            },
        ],
        infer_last_interval=False,
    )

    price_gas = 5

    # If the period is one year the equivalent periodical costs (epc) of an
    # investment are equal to the annuity. Use oemof's economic tools.
    epc_wind = economics.annuity(capex=1000, n=20, wacc=0.05)
    epc_pv = economics.annuity(capex=1000, n=20, wacc=0.05)
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

    # create source object representing the gas commodity (annual limit)
    gas_resource = solph.components.Source(
        label="rgas", outputs={bgas: solph.Flow(variable_costs=price_gas)}
    )

    wind_profile = pd.concat(
        [
            aggregation1.typicalPeriods["wind"],
            aggregation2.typicalPeriods["wind"],
        ],
        ignore_index=True,
    )
    wind_profile.iloc[-24:] = 0

    # create fixed source object representing wind power plants
    wind = solph.components.Source(
        label="wind",
        outputs={
            bel: solph.Flow(
                fix=wind_profile,
                investment=solph.Investment(ep_costs=epc_wind, lifetime=10),
            )
        },
    )

    pv_profile = pd.concat(
        [aggregation1.typicalPeriods["pv"], aggregation2.typicalPeriods["pv"]],
        ignore_index=True,
    )
    pv_profile.iloc[-24:] = 0

    # create fixed source object representing pv power plants
    pv = solph.components.Source(
        label="pv",
        outputs={
            bel: solph.Flow(
                fix=pd.concat(
                    [
                        aggregation1.typicalPeriods["pv"],
                        aggregation2.typicalPeriods["pv"],
                    ],
                    ignore_index=True,
                ),
                investment=solph.Investment(ep_costs=epc_pv, lifetime=10),
            )
        },
    )

    # create simple sink object representing the electrical demand
    demand = solph.components.Sink(
        label="demand",
        inputs={
            bel: solph.Flow(
                fix=pd.concat(
                    [
                        aggregation1.typicalPeriods["demand_el"],
                        aggregation2.typicalPeriods["demand_el"],
                    ],
                    ignore_index=True,
                ),
                nominal_value=1,
            )
        },
    )

    # create simple Converter object representing a gas power plant
    pp_gas = solph.components.Converter(
        label="pp_gas",
        inputs={bgas: solph.Flow()},
        outputs={bel: solph.Flow(nominal_value=10e10, variable_costs=0)},
        conversion_factors={bel: 0.58},
    )

    # create storage object representing a battery
    storage = solph.components.GenericStorage(
        label="storage",
        inputs={bel: solph.Flow(variable_costs=0.0001)},
        outputs={bel: solph.Flow()},
        loss_rate=0.01,
        lifetime_inflow=10,
        lifetime_outflow=10,
        invest_relation_input_capacity=1 / 6,
        invest_relation_output_capacity=1 / 6,
        inflow_conversion_factor=1,
        outflow_conversion_factor=0.8,
        investment=solph.Investment(ep_costs=epc_storage, lifetime=10),
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
    om.write("my_model.lp", io_options={"symbolic_solver_labels": True})
    om.solve(solver="cbc", solve_kwargs={"tee": True})

    ##########################################################################
    # Check and plot the results
    ##########################################################################

    # check if the new result object is working for custom components
    results = solph.processing.results(om)
    print(results)

    # Concatenate flows:
    flows = pd.concat([flow["sequences"] for flow in results.values()], axis=1)
    flows.columns = [
        f"{oemof_tuple[0]}-{oemof_tuple[1]}" for oemof_tuple in results.keys()
    ]
    print(flows)

    electricity_bus = solph.views.node(results, "electricity")

    meta_results = solph.processing.meta_results(om)
    pp.pprint(meta_results)

    my_results = electricity_bus["period_scalars"]

    # installed capacity of storage in GWh
    my_results["storage_invest_GWh"] = (
        results[(storage, None)]["period_scalars"]["invest"] / 1e6
    )

    # installed capacity of wind power plant in MW
    my_results["wind_invest_MW"] = (
        results[(wind, bel)]["period_scalars"]["invest"] / 1e3
    )

    # resulting renewable energy share
    print(
        "res_share:",
        (
            1
            - results[(pp_gas, bel)]["sequences"].sum()
            / results[(bel, demand)]["sequences"].sum()
        ),
    )

    pp.pprint(my_results)


if __name__ == "__main__":
    main()
