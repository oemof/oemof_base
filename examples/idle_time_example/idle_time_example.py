# -*- coding: utf-8 -*-

"""

"""

__copyright__ = "oemof developer group"
__license__ = "GPLv3"

import os
import pandas as pd
import oemof.solph as solph

import matplotlib.pyplot as plt


solver = "cbc"

# Create an energy system and optimize the dispatch at least costs.
# ####################### initialize and provide data #####################

datetimeindex = pd.date_range("1/1/2016", periods=10, freq="H")
energysystem = solph.EnergySystem(timeindex=datetimeindex)

# ######################### create energysystem components ################

bus = solph.buses.Bus(label="Bus")
sink = solph.components.Sink(
    label="Sink",
    inputs={
        bus: solph.flows.Flow(
            nominal_value=1,
            variable_costs=-1,
            min=0.2,
            nonconvex=solph.NonConvex(),
        )
    },
)
source = solph.components.Source(
    label="Source",
    outputs={
        bus: solph.flows.Flow(
            nominal_value=1,
            min=0.2,
            nonconvex=solph.NonConvex(),
        )
    },
)
storage = solph.components.GenericStorage(
    nominal_storage_capacity=10,
    label="Storage",
    inputs={bus: solph.Flow(nominal_value=10 / 6)},
    outputs={bus: solph.Flow(nominal_value=10 / 6, variable_costs=0.001)},
    initial_storage_level=0,
    loss_rate=0,
    inflow_conversion_factor=1,
    outflow_conversion_factor=1,
)

energysystem.add(bus, sink, source, storage)

# ################################ optimization ###########################

# create optimization model based on energy_system
optimization_model = solph.Model(energysystem=energysystem)

solph.constraints.set_idle_time(
    optimization_model, (source, bus), (bus, sink), n=2
)

optimization_model.write(
    "/home/jann/Desktop/lp-idle.lp",
    io_options={"symbolic_solver_labels": True},
)

# solve problem
optimization_model.solve(
    solver=solver, solve_kwargs={"tee": True, "keepfiles": False}
)

# write back results from optimization object to energysystem
optimization_model.results()

# ################################ results ################################

# subset of results that includes all flows into and from electrical bus
# sequences are stored within a pandas.DataFrames and scalars e.g.
# investment values within a pandas.Series object.
# in this case the entry data['scalars'] does not exist since no investment
# variables are used
data = solph.views.node(optimization_model.results(), "Bus")

print("Optimization successful. Showing some results:")

# see: https://pandas.pydata.org/pandas-docs/stable/visualization.html
node_results_bel = solph.views.node(optimization_model.results(), "Bus")
node_results_flows = node_results_bel["sequences"]
node_results_flows = node_results_flows[
    [
        (("Bus", "Sink"), "flow"),
        (("Source", "Bus"), "flow"),
        (("Bus", "Storage"), "flow"),
        (("Storage", "Bus"), "flow"),
    ]
]
node_results_flows.loc[
    :, [(("Bus", "Sink"), "flow"), (("Bus", "Storage"), "flow")]
] *= -1
fig, ax = plt.subplots(figsize=(10, 5))
node_results_flows.plot(ax=ax, kind="bar", stacked=True, linewidth=0, width=1)
ax.set_title("Sums for optimization period")
ax.legend(loc="upper right", bbox_to_anchor=(1, 1))
ax.set_xlabel("Energy (MWh)")
ax.set_ylabel("Flow")
plt.legend(loc="center left", prop={"size": 8}, bbox_to_anchor=(1, 0.5))

fig.subplots_adjust(right=0.8)

plt.show()
