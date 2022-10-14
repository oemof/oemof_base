# -*- coding: utf-8 -*-
"""
Example that shows how to use a combination of minimum and maximum uptime.

The model consists of a volatile renewable energy source with
a fixed profile (Source: 'renewable_energy'), a cyclic industrial process
modelled as a Sink with a NonConvex flow with negative variable costs as
revenues, and an excess for surplus of renewable energy.

The cyclic industrial process has a fixed block profile and a certain time
within each cycle is required. With the attributes `maximum_uptime`,
`minimum_uptime` and `minimum_downtime`, and a given `nominal_value`
combination with the `min` attribute it is possible to model
this scheduling problem.

SPDX-FileCopyrightText: Johannes Röder <johannes.roeder@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
import os
import logging

import pandas as pd
import matplotlib.pyplot as plt

from oemof.solph import components
from oemof.solph import Flow, Bus, EnergySystem, Model
from oemof.solph._options import NonConvex
from oemof.solph import processing, views
from oemof.solph import helpers

renewable_timeseries = [
    1, 1, 2, 4, 5, 6, 4, 6, 2, 6, 7, 6,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    8, 8, 2, 1, 0, 5, 6, 7, 6, 7, 3,
    3, 1, 1,
]

# select periods
periods = len(renewable_timeseries)

# create an energy system
idx = pd.date_range('1/1/2022', periods=periods, freq='H')
es = EnergySystem(timeindex=idx)

bus_1 = Bus(label='bus')

es.add(bus_1)

es.add(components.Source(
    label='renewable_energy',
    outputs={bus_1: Flow(
        fix=renewable_timeseries,
        nominal_value=1,
    )}
))

es.add(components.Sink(
    label='cyclic_process',
    inputs={bus_1: Flow(
        variable_costs=-5565,
        nominal_value=10,
        min=0,
        nonconvex=NonConvex(
            minimum_downtime=3,
            minimum_uptime=4,
            maximum_uptime=4,
            profile=[2, 3, 4, 5],
            startup_costs=10,
            # shutdown_costs=2,
        ),
    )},
))

es.add(components.Sink(
    label='excess',
    inputs={bus_1: Flow(
        variable_costs=0,
    )},
))

# create an optimization problem and solve it
om = Model(es)

# export lp file
filename = os.path.join(
    helpers.extend_basic_path('lp_files'), 'Schedule_profile.lp')
logging.info('Store lp-file in {0}.'.format(filename))
om.write(filename, io_options={'symbolic_solver_labels': True})

# solve model
om.solve(solver='gurobi', solve_kwargs={'tee': True})

# create result object
results = processing.results(om)

bus1 = views.node(results, 'bus')["sequences"]
bus1.plot(kind='line', drawstyle='steps-mid')
plt.ylim(None, 10)
plt.legend()
plt.show()


