# -*- coding: utf-8 -*-

"""
General description:
---------------------

The example models the following energy system:

                input/output  bgas     bel
                     |          |        |       |
                     |          |        |       |
 wind(FixedSource)   |------------------>|       |
                     |          |        |       |
 pv(FixedSource)     |------------------>|       |
                     |          |        |       |
 rgas(Commodity)     |--------->|        |       |
                     |          |        |       |
 demand(Sink)        |<------------------|       |
                     |          |        |       |
                     |          |        |       |
 pp_gas(Transformer) |<---------|        |       |
                     |------------------>|       |
                     |          |        |       |
 storage(Storage)    |<------------------|       |
                     |------------------>|       |



This file is part of project oemof (github.com/oemof/oemof). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location oemof/tests/test_scripts/test_solph/
test_storage_investment/test_storage_investment.py

SPDX-License-Identifier: MIT
"""

import logging
import os
from unittest import skip

import pandas as pd
from nose.tools import eq_
from oemof.network.network import Node
from oemof.tools import economics

from oemof import solph
from oemof.solph import processing
from oemof.solph import views

PP_GAS = None


def test_optimise_storage_size(
    filename="storage_investment.csv", solver="cbc"
):
    global PP_GAS

    logging.info("Initialize the energy system")
    date_time_index = pd.date_range("1/1/2012", periods=400, freq="H")

    energysystem = solph.EnergySystem(timeindex=date_time_index)
    Node.registry = energysystem

    full_filename = os.path.join(os.path.dirname(__file__), filename)
    data = pd.read_csv(full_filename, sep=",")

    # Buses
    bgas = solph.Bus(label="natural_gas")
    bel = solph.Bus(label="electricity")

    # Sinks
    solph.Sink(label="excess_bel", inputs={bel: solph.Flow()})

    solph.Sink(
        label="demand",
        inputs={bel: solph.Flow(fix=data["demand_el"], nominal_value=1)},
    )

    # Sources
    solph.Source(
        label="rgas",
        outputs={
            bgas: solph.Flow(
                nominal_value=194397000 * 400 / 8760, summed_max=1
            )
        },
    )

    solph.Source(
        label="wind",
        outputs={bel: solph.Flow(fix=data["wind"], nominal_value=1000000)},
    )

    solph.Source(
        label="pv",
        outputs={bel: solph.Flow(fix=data["pv"], nominal_value=582000)},
    )

    # Transformer
    PP_GAS = solph.Transformer(
        label="pp_gas",
        inputs={bgas: solph.Flow()},
        outputs={bel: solph.Flow(nominal_value=10e10, variable_costs=50)},
        conversion_factors={bel: 0.58},
    )

    # Investment storage
    epc = economics.annuity(capex=1000, n=20, wacc=0.05)
    solph.components.GenericStorage(
        label="storage",
        inputs={bel: solph.Flow(variable_costs=10e10)},
        outputs={bel: solph.Flow(variable_costs=10e10)},
        loss_rate=0.00,
        initial_storage_level=0,
        invest_relation_input_capacity=1 / 6,
        invest_relation_output_capacity=1 / 6,
        inflow_conversion_factor=1,
        outflow_conversion_factor=0.8,
        investment=solph.Investment(ep_costs=epc,
                                    existing=6851),
    )

    # Solve model
    om = solph.Model(energysystem)
    om.receive_duals()
    om.solve(solver=solver)
    energysystem.results["main"] = processing.results(om)
    energysystem.results["meta"] = processing.meta_results(om)

    # Check dump and restore
    energysystem.dump()


def test_results_with_actual_dump():
    energysystem = solph.EnergySystem()
    energysystem.restore()

    # Results
    results = energysystem.results["main"]
    meta = energysystem.results["meta"]

    electricity_bus = views.node(results, "electricity")
    my_results = electricity_bus["sequences"].sum(axis=0).to_dict()
    storage = energysystem.groups["storage"]
    my_results["storage_invest"] = results[(storage, None)]["scalars"][
        "invest"
    ]

    stor_invest_dict = {
        "storage_invest": 2040000,
        (("electricity", "None"), "duals"): 10800000000321,
        (("electricity", "demand"), "flow"): 105867395,
        (("electricity", "excess_bel"), "flow"): 211771291,
        (("electricity", "storage"), "flow"): 2350931,
        (("pp_gas", "electricity"), "flow"): 5148414,
        (("pv", "electricity"), "flow"): 7488607,
        (("storage", "electricity"), "flow"): 1880745,
        (("wind", "electricity"), "flow"): 305471851,
    }

    for key in stor_invest_dict.keys():
        eq_(int(round(my_results[key])), int(round(stor_invest_dict[key])))

    # Solver results
    eq_(str(meta["solver"]["Termination condition"]), "optimal")
    eq_(meta["solver"]["Error rc"], 0)
    eq_(str(meta["solver"]["Status"]), "ok")

    # Problem results
    eq_(meta["problem"]["Lower bound"], 4.231675777e17)
    eq_(meta["problem"]["Upper bound"], 4.231675777e17)
    eq_(meta["problem"]["Number of variables"], 2805)
    eq_(meta["problem"]["Number of constraints"], 2806)
    eq_(meta["problem"]["Number of nonzeros"], 1197)
    eq_(meta["problem"]["Number of objectives"], 1)
    eq_(str(meta["problem"]["Sense"]), "minimize")

    # Objective function
    eq_(round(meta["objective"]), 423167578261115584)


@skip(
    "Opening an old dump may fail due to different python versions or"
    " version of other packages. We can try to reactivate the test with"
    " v0.4.0."
)
def test_results_with_old_dump():
    """
    Test again with a stored dump created with v0.3.2dev (896a6d50)
    """
    energysystem = solph.EnergySystem()
    energysystem.restore(
        dpath=os.path.dirname(os.path.realpath(__file__)),
        filename="es_dump_test_3_2dev.oemof",
    )

    results = energysystem.results["main"]

    electricity_bus = views.node(results, "electricity")
    my_results = electricity_bus["sequences"].sum(axis=0).to_dict()
    storage = energysystem.groups["storage"]
    my_results["storage_invest"] = results[(storage, None)]["scalars"][
        "invest"
    ]

    stor_invest_dict = {
        "storage_invest": 2040000,
        (("electricity", "demand"), "flow"): 105867395,
        (("electricity", "excess_bel"), "flow"): 211771291,
        (("electricity", "storage"), "flow"): 2350931,
        (("pp_gas", "electricity"), "flow"): 5148414,
        (("pv", "electricity"), "flow"): 7488607,
        (("storage", "electricity"), "flow"): 1880745,
        (("wind", "electricity"), "flow"): 305471851,
    }

    for key in stor_invest_dict.keys():
        eq_(int(round(my_results[key])), int(round(stor_invest_dict[key])))


def test_solph_transformer_attributes_before_dump_and_after_restore():
    """dump/restore should preserve all attributes of `solph.Transformer`"""
    energysystem = solph.EnergySystem()
    energysystem.restore()

    trsf_attr_before_dump = sorted([x for x in dir(PP_GAS) if "__" not in x])

    trsf_attr_after_restore = sorted(
        [x for x in dir(energysystem.groups["pp_gas"]) if "__" not in x]
    )

    # Compare attributes before dump and after restore
    eq_(trsf_attr_before_dump, trsf_attr_after_restore)
