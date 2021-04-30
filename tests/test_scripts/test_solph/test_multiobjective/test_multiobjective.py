# -*- coding: utf-8 -*-
"""
This script contains an integration test for multi objective modelling.
"""

import pandas as pd

import oemof.solph as solph
from oemof.solph import processing
from oemof.solph import views
from oemof.solph.options import MultiObjective as mo


def test_multiobjective():
    ###########################################################################
    # Set Costs, Demand etc.
    ###########################################################################

    # set list with different weights
    weight_list = [(1, 0), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0, 1)]

    # set fixed costs
    cost_ecological_fix = 2
    cost_financial_fix = 2

    # read import data
    import_data = pd.DataFrame(
        index=pd.date_range(start='2020-01-01', periods=8, freq='3H'),
        data={'cost_ecological': [0, 1, 1, 1, 1, 2, 3, 4],
              'cost_financial': [0, 1, 2, 3, 4, 1, 1, 1],
              'p_el_dem': [1, 1, 1, 1, 1, 1, 1, 1]})

    # get demand
    p_el_dem = import_data.loc[:, 'p_el_dem']

    # get costs
    cost_ecological_var = import_data.loc[:, 'cost_ecological']
    cost_financial_var = import_data.loc[:, 'cost_financial']

    ###########################################################################
    # Create Enegy System
    ###########################################################################
    # get timeindex
    timesteps = pd.date_range(
        start=import_data.index[0],
        end=import_data.index[-1],
        freq=import_data.index.inferred_freq)

    # initialise energy system
    energy_system = solph.EnergySystem(timeindex=timesteps)

    # create and add electrical bus
    el_bus = solph.Bus(
        label='el_bus')
    energy_system.add(el_bus)

    # create and add electrical demand
    el_dem = solph.Sink(
        label='el_dem',
        inputs={el_bus: solph.Flow(fix=p_el_dem, nominal_value=1000)})
    energy_system.add(el_dem)

    # create and add electrical source with variable price
    el_source_var = solph.Source(
        label='el_source_var',
        outputs={el_bus: solph.Flow(multiobjective=mo(
            ecological=mo.Objective(
                variable_costs=cost_ecological_var),
            financial=mo.Objective(
                variable_costs=cost_financial_var)))})
    energy_system.add(el_source_var)

    # create and add electrical source with fixed price
    el_source_fix = solph.Source(
        label='el_source_fix',
        outputs={el_bus: solph.Flow(multiobjective=mo(
            ecological=mo.Objective(
                variable_costs=cost_ecological_fix),
            financial=mo.Objective(
                variable_costs=cost_financial_fix)))})
    energy_system.add(el_source_fix)

    #######################################################################
    # Create LP Model
    #######################################################################

    # create a pyomo optimization problem
    optimisation_model = solph.MultiObjectiveModel(energy_system)

    ###########################################################################
    # Iterate over different weights and Solve LP Model
    ###########################################################################

    for weight_ecological, weight_financial in weight_list:

        # solve problem using cplex
        # no console output
        optimisation_model.solve(
            solver='cbc',
            optimization_type='weighted',
            objective_weights={'ecological': weight_ecological,
                               'financial': weight_financial},
            solve_kwargs={'tee': False},
            cmdline_options={'tmlim': 30})

        #######################################################################
        # Extract and Postprocess results
        #######################################################################

        # get result dict
        results = processing.results(optimisation_model)

        # get results for important nodes
        el_bus_data = views.node(results, 'el_bus')['sequences']

        # get costs for variable cost source
        p_el_var = el_bus_data[(('el_source_var', 'el_bus'), 'flow')]

        # get costs for fixed cost source
        p_el_fix = el_bus_data[(('el_source_fix', 'el_bus'), 'flow')]

        # get variable costs
        cost_var = (weight_ecological * cost_ecological_var
                    + weight_financial * cost_financial_var)

        # get fix costs
        cost_fix = (weight_ecological * cost_ecological_fix
                    + weight_financial * cost_financial_fix)

        ###################################################################
        # Validate results
        ###################################################################

        # iterate over timesteps
        for t in range(len(timesteps)):
            # assert correct assignment only for unambiguous timesteps
            if cost_var.iat[t] > cost_fix:
                assert p_el_var.iat[t] == 0
            elif cost_var.iat[t] < cost_fix:
                assert p_el_fix.iat[t] == 0
