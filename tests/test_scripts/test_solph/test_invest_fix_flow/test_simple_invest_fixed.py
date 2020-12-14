# -*- coding: utf-8 -*-

""" This example shows how to create an energysystem with oemof objects and
solve it with the solph module.

Data: example_data.csv

This file is part of project oemof (github.com/oemof/oemof). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location.

SPDX-License-Identifier: MIT
"""

import os

import pandas as pd
from oemof.network.network import Node
from oemof.tools import economics

from oemof.solph import Bus
from oemof.solph import EnergySystem
from oemof.solph import Flow
from oemof.solph import Investment
from oemof.solph import Model
from oemof.solph import Sink
from oemof.solph import Source
from oemof.solph import processing
from oemof.solph import views


def test_dispatch_fix_example(solver='cbc', periods=10):
    """Invest in a flow with a `fix` sequence containing values > 1."""
    Node.registry = None

    filename = os.path.join(os.path.dirname(__file__), 'input_data.csv')
    data = pd.read_csv(filename, sep=",")

    # ######################### create energysystem components ################

    # electricity and heat
    bel = Bus(label='b_el')

    # an excess and a shortage variable can help to avoid infeasible problems
    excess_el = Sink(
        label='excess_el',
        inputs={bel: Flow()}
    )

    # shortage_el = Source(label='shortage_el',
    #                      outputs={bel: Flow(variable_costs=200)})

    # sources
    ep_pv = economics.annuity(capex=1500, n=20, wacc=0.05)

    pv = Source(
        label='pv',
        outputs={
            bel: Flow(
                fix=data['pv'],
                investment=Investment(ep_costs=ep_pv)
            )
        }
    )

    # demands (electricity/heat)
    demand_el = Sink(
        label='demand_elec',
        inputs={
            bel: Flow(
                nominal_value=85,
                fix=data['demand_el']
            )
        }
    )

    datetimeindex = pd.date_range('1/1/2012', periods=periods, freq='H')

    energysystem = EnergySystem(timeindex=datetimeindex)

    energysystem.add(bel, excess_el, pv, demand_el)

    # ################################ optimization ###########################

    # create optimization model based on energy_system
    optimization_model = Model(energysystem=energysystem)

    # solve problem
    optimization_model.solve(solver=solver)

    # ################################ results ################################

    # generic result object
    results = processing.results(om=optimization_model)

    # subset of results that includes all flows into and from electrical bus
    # sequences are stored within a pandas.DataFrames and scalars e.g.
    # investment values within a pandas.Series object.
    # in this case the entry data['scalars'] does not exist since no investment
    # variables are used
    data = views.node(results, 'b_el')

    # generate results to be evaluated in tests
    comp_results = data['sequences'].sum(axis=0).to_dict()
    comp_results['pv_capacity'] = results[(pv, bel)]['scalars'].invest

    assert comp_results[(('pv', 'b_el'), 'flow')] > 0

    test_results = {
        (('pv', 'b_el'), 'flow'): 2523,
        (('b_el', 'demand_elec'), 'flow'): 436.05,
        (('b_el', 'excess_el'), 'flow'): 2087,
        'pv_capacity': 450,
    }

    for key in test_results.keys():
        assert int(round(comp_results[key])) == int(round(test_results[key]))
