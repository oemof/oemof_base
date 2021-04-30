# -*- coding: utf-8 -*-
"""
This script contains tests for the MultiObjectiveModel
"""

import pandas as pd
from pyomo.core.expr import current

import oemof.solph as solph
from oemof.solph.options import MultiObjective as mo


def test_objective_functions_keys():

    t = pd.date_range(start="01/01/2020", end="01/02/2020", freq="12H")

    es = solph.EnergySystem(timeindex=t)

    bus = solph.Bus(label='bus')

    flow1 = solph.Flow(
        label='flow1',
        multiobjective=mo(
            eco=mo.Objective(
                variable_costs=1),
            cost=mo.Objective(
                variable_costs=2)))
    flow2 = solph.Flow(
        label='flow2',
        multiobjective=mo(
            eco=mo.Objective(
                variable_costs=1),
            benefit=mo.Objective(
                variable_costs=3)))

    trans = solph.Transformer(label='trans',
                              inputs={bus: flow1},
                              outputs={bus: flow2})

    es.add(trans, bus)

    model = solph.MultiObjectiveModel(es)

    objective_functions = model.objective_functions

    dict_compare = {'cost': 1, 'eco': 2, 'benefit': 3, '_standard': 4}

    assert objective_functions.keys() == dict_compare.keys()


def test_objective_functions_values():

    t = pd.date_range(start="01/01/2020", end="01/02/2020", freq="12H")

    es = solph.EnergySystem(timeindex=t)

    bus = solph.Bus(label='bus')

    costs = {'eco': 1, 'cost': 2, 'benefit': 3, '_standard': 0}

    flow1 = solph.Flow(
        label='flow1',
        multiobjective=mo(
            eco=mo.Objective(
                variable_costs=costs['eco']),
            cost=mo.Objective(
                variable_costs=costs['cost'])))
    flow2 = solph.Flow(
        label='flow2',
        multiobjective=mo(
            eco=mo.Objective(
                variable_costs=costs['eco']),
            benefit=mo.Objective(
                variable_costs=costs['benefit'])))

    trans = solph.Transformer(
        label='trans',
        inputs={bus: flow1},
        outputs={bus: flow2})

    es.add(trans, bus)

    model = solph.MultiObjectiveModel(es)

    objective_functions = model.objective_functions

    expr_compare = {
        'eco': ('12.0*flow[trans,bus,0] + 12.0*flow[trans,bus,1] + '
                + '12.0*flow[trans,bus,2] + 12.0*flow[bus,trans,0] + '
                + '12.0*flow[bus,trans,1] + 12.0*flow[bus,trans,2]'),
        'cost': ('24.0*flow[bus,trans,0] + 24.0*flow[bus,trans,1] + '
                 + '24.0*flow[bus,trans,2]'),
        'benefit': ('36.0*flow[trans,bus,0] + 36.0*flow[trans,bus,1] + '
                    + '36.0*flow[trans,bus,2]'),
        '_standard': '0'}

    for x, c in costs.items():
        mod_expr = current.expression_to_string(objective_functions[x])

        assert mod_expr == expr_compare[x]


def test_objective_functions_key_standard():

    t = pd.date_range(start="01/01/2020", end="01/02/2020", freq="12H")

    es = solph.EnergySystem(timeindex=t)

    bus = solph.Bus(label='bus')

    snk = solph.Sink(label='snk', inputs={bus: solph.Flow()})

    es.add(snk, bus)

    model = solph.MultiObjectiveModel(es)

    objective_functions = model.objective_functions

    dict_compare = {'_standard': 0}

    assert objective_functions.keys() == dict_compare.keys()
