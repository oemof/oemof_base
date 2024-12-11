# -*- coding: utf-8 -*-

"""
General description
-------------------

A minimal example to show speedup of giving expected value to solver.

Installation requirements
-------------------------

This example requires oemof.solph, install by:

    pip install oemof.solph
"""
import numpy as np
import pandas as pd

from oemof import solph

solver = "cbc"  # 'glpk', 'gurobi',...
solver_verbose = False  # show/hide solver output
time_steps = 2000 # 8760

date_time_index = pd.date_range("1/1/2000", periods=time_steps, freq="h")

rng = np.random.default_rng(seed=1337)
random_costs = rng.exponential(size=time_steps)
random_demands = rng.uniform(size=time_steps)
random_losses = np.minimum(
    np.ones(time_steps), rng.exponential(scale=1e-1, size=time_steps)
)


def run_energy_system(index, costs, demands, losses, expected=None):
    energy_system = solph.EnergySystem(
        timeindex=index,
        infer_last_interval=True,
    )

    if expected is None:
        expected = {
            (("bus", "storage"), "flow"): None,
            (("source", "bus"), "flow"): None,
            (("storage", "bus"), "flow"): None,
        }
    else:
        expected = expected / 10

    bus = solph.buses.Bus(label="bus")
    source = solph.components.Source(
        label="source",
        outputs={
            bus: solph.flows.Flow(
                variable_costs=costs,
                nonconvex=solph.NonConvex(),
                expected=expected[(("source", "bus"), "flow")],
                min=0.2,
                nominal_capacity=10,
            )
        },
    )
    storage = solph.components.GenericStorage(
        label="storage",
        inputs={
            bus: solph.flows.Flow(
                nominal_capacity=10,
                expected=expected[(("bus", "storage"), "flow")],
            )
        },
        outputs={
            bus: solph.flows.Flow(
                nominal_capacity=10,
                expected=expected[(("storage", "bus"), "flow")],
            )
        },
        nominal_capacity=1e4,
        loss_rate=losses,
    )
    sink = solph.components.Sink(
        label="sink",
        inputs={bus: solph.flows.Flow(nominal_capacity=1, fix=demands)},
    )

    energy_system.add(bus, source, sink, storage)
    model = solph.Model(energy_system)
    model.solve(
        solver=solver,
        solve_kwargs={
            "tee": solver_verbose,
            "warmstart": True,
        },
    )

    _results = solph.processing.results(model)
    _meta_results = solph.processing.meta_results(model)
    return _results, _meta_results


meta_results = {}

results, meta_results["no hints 1"] = run_energy_system(
    date_time_index, random_costs, random_demands, random_losses
)
bus_data = solph.views.node(results, "bus")["sequences"]

_, meta_results["no hints 2"] = run_energy_system(
    date_time_index, random_costs, random_demands, random_losses
)
_, meta_results["with hints"] = run_energy_system(
    date_time_index,
    random_costs,
    random_demands,
    random_losses,
    expected=bus_data,
)
_, meta_results["no hints 3"] = run_energy_system(
    date_time_index, random_costs, random_demands, random_losses
)

for meta_result in meta_results:
    print(
        "Time to solve run {run}: {time:.2f} s".format(
            run=meta_result,
            time=meta_results[meta_result]["solver"]["Wallclock time"],
        )
    )
