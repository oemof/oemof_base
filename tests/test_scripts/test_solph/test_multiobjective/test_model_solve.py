# -*- coding: utf-8 -*-
"""
This script cains tests for the MultiObjectiveModel solve-function.
"""

import pandas as pd
from nose.tools import raises
from pyomo.core.expr import current

import oemof.solph as solph
from oemof.solph.options import MultiObjective as mo


def test_opt_type():
    es = solph.EnergySystem(timeindex=pd.date_range(
        start='1/1/2018', end='3/1/2018', freq='D'))
    mod = solph.MultiObjectiveModel(es)
    with raises(Exception, match="Invalid optimization type"):
        mod.solve(solver="cbc", optimization_type="flux_capacitator")


def test_singular_obj_type():
    es = solph.EnergySystem(timeindex=pd.date_range(
        start='1/1/2018', end='3/1/2018', freq='D'))
    mod = solph.MultiObjectiveModel(es)
    with raises(TypeError, match='Objective is not of type "string"'):
        mod.solve(solver="cbc",
                  optimization_type='singular',
                  objective=['eco'])


def test_weighted_weights_dict():
    es = solph.EnergySystem(timeindex=pd.date_range(
        start='1/1/2018', end='3/1/2018', freq='D'))
    bus = solph.Bus(label='bus')
    src = solph.Source(label='src', outputs={bus: solph.Flow(
        multiobjective=mo(
            eco=mo.Objective(
                variable_costs=0.5)))})
    es.add(bus)
    es.add(src)
    mod = solph.MultiObjectiveModel(es)
    with raises(TypeError, match="Objective weights must be of type 'dict'"):
        mod.solve(solver="cbc",
                  optimization_type='weighted',
                  objective_weights=[0.3])


def test_weighted_weights_length():
    es = solph.EnergySystem(timeindex=pd.date_range(
        start='1/1/2018', end='3/1/2018', freq='D'))
    bus = solph.Bus(label='bus')
    src = solph.Source(label='src', outputs={bus: solph.Flow(
        multiobjective=mo(
            eco=mo.Objective(
                variable_costs=0.5)))})
    es.add(bus)
    es.add(src)
    mod = solph.MultiObjectiveModel(es)
    with raises(ValueError, match='Objective weights must not be empty'):
        mod.solve(solver="cbc",
                  optimization_type='weighted',
                  objective_weights={})


def test_objective_weighting():
    es = solph.EnergySystem(timeindex=pd.date_range(
        start='1/1/2018', end='3/1/2018', freq='D'))
    bus = solph.Bus(label='bus')
    src = solph.Source(label='src', outputs={bus: solph.Flow(
        multiobjective=mo(
            eco=mo.Objective(
                variable_costs=0.5),
            mon=mo.Objective(
                variable_costs=1.3)))})
    snk = solph.Sink(label='snk', inputs={bus: solph.Flow()})
    es.add(bus)
    es.add(src)
    es.add(snk)
    mod = solph.MultiObjectiveModel(es)
    mod.solve(solver='cbc',
              optimization_type='weighted',
              objective_weights={'eco': 0.3, 'mon': 0.7})
    s = current.expression_to_string(mod.objective)

    # initialise expression string for first part of wighted sum
    i = 0
    expr_str = '(0.3*({0:}*flow[src,bus,{1:d}]'.format(0.5 * 24, i)
    i += 1
    # add summed values
    while i < (len(es.timeindex) - 1):
        expr_str += ' + {0:}*flow[src,bus,{1:d}]'.format(0.5 * 24, i)
        i += 1
    # add end of first partial sum
    expr_str += ' + {0:}*flow[src,bus,{1:d}])'.format(0.5 * 24, i)
    # initialise expression string for second part of wighted sum
    i = 0
    expr_str += ' + 0.7*({0:}*flow[src,bus,{1:d}]'.format(1.3 * 24, i)
    i += 1
    # add summed values
    while i < (len(es.timeindex) - 1):
        expr_str += ' + {0:}*flow[src,bus,{1:d}]'.format(1.3 * 24, i)
        i += 1
    # add end of first partial sum
    expr_str += ' + {0:}*flow[src,bus,{1:d}]))'.format(1.3 * 24, i)

    assert s == expr_str
