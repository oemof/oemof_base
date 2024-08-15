# -*- coding: utf-8 -*-

"""This module can be used to check the installation.

This is not an illustrated example.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: jnnr

SPDX-License-Identifier: MIT

"""

import logging

import pandas as pd

from oemof import solph


def check_oemof_installation(silent=False):
    logging.disable(logging.CRITICAL)

    date_time_index = pd.date_range("1/1/2012", periods=6, freq="h")
    energysystem = solph.EnergySystem(
        timeindex=date_time_index,
        infer_last_interval=False,
    )

    bgas = solph.buses.Bus(label="natural_gas")
    bel = solph.buses.Bus(label="electricity")
    solph.components.Sink(label="excess_bel", inputs={bel: solph.flows.Flow()})
    solph.components.Source(label="rgas", outputs={bgas: solph.flows.Flow()})
    solph.components.Sink(
        label="demand",
        inputs={
            bel: solph.flows.Flow(fix=[10, 20, 30, 40, 50], nominal_value=1)
        },
    )
    solph.components.Converter(
        label="pp_gas",
        inputs={bgas: solph.flows.Flow()},
        outputs={
            bel: solph.flows.Flow(nominal_value=10e10, variable_costs=50)
        },
        conversion_factors={bel: 0.58},
    )
    om = solph.Model(energysystem)

    # check solvers
    solver = {}
    for s in ["cbc", "glpk", "gurobi", "cplex", "scip"]:
        try:
            om.solve(solver=s)
            solver[s] = "working"
        except Exception:
            solver[s] = "not working"

    if not silent:
        _print_division_line("Solver installed with oemof:")
        print()
        for s, t in solver.items():
            print("{0}: {1}".format(s, t))
        _print_division_line("oemof successfully installed.")
        print("*****************************")


def _print_division_line(arg0):
    print()
    print("*****************************")
    print(arg0)
