# -*- coding: utf-8 -

"""Tests the processing module of solph.

This file is part of project oemof (github.com/oemof/oemof). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location oemof/tests/test_py

SPDX-License-Identifier: MIT
"""

import os

import pandas

from oemof.solph import EnergySystem
from oemof.solph import Investment
from oemof.solph import Model
from oemof.solph import _experimental_processing as exppro
from oemof.solph import processing
from oemof.solph.buses import Bus
from oemof.solph.components import Converter
from oemof.solph.components import GenericStorage
from oemof.solph.components import Sink
from oemof.solph.flows import Flow


class TestParameterResult:
    @classmethod
    def setup_class(cls):
        cls.period = 24
        cls.es = EnergySystem(
            timeindex=pandas.date_range(
                "2016-01-01", periods=cls.period, freq="H"
            ),
            infer_last_interval=True,
        )

        # BUSSES
        b_el1 = Bus(label="b_el1")
        b_el2 = Bus(label="b_el2")
        b_diesel = Bus(label="b_diesel", balanced=False)
        cls.es.add(b_el1, b_el2, b_diesel)

        # TEST DIESEL:
        dg = Converter(
            label="diesel",
            inputs={b_diesel: Flow(variable_costs=2)},
            outputs={
                b_el1: Flow(
                    variable_costs=1, nominal_value=Investment(ep_costs=0.5)
                )
            },
            conversion_factors={b_el1: 2},
        )

        batt = GenericStorage(
            label="storage",
            inputs={b_el1: Flow(variable_costs=3)},
            outputs={b_el2: Flow(variable_costs=2.5)},
            loss_rate=0.00,
            initial_storage_level=0,
            invest_relation_input_capacity=1 / 6,
            invest_relation_output_capacity=1 / 6,
            inflow_conversion_factor=1,
            outflow_conversion_factor=0.8,
            nominal_storage_capacity=Investment(ep_costs=0.4),
        )

        cls.demand_values = [0.0] + [100] * 23
        demand = Sink(
            label="demand_el",
            inputs={b_el2: Flow(nominal_value=1, fix=cls.demand_values)},
        )
        cls.es.add(dg, batt, demand)
        cls.om = Model(cls.es)
        cls.om.receive_duals()
        cls.om.solve()
        cls.mod = Model(cls.es)
        cls.mod.solve()

    def test_get_set_costs_from_lpfile(self):
        self.om.write(
            os.path.join(
                os.getcwd(), "tests", "lp_files", "costs_from_lpfile.lp"
            ),
            io_options={"symbolic_solver_labels": True},
        )

        lp_file = os.path.join(
            os.getcwd(), "tests", "lp_files", "costs_from_lpfile.lp"
        )
        tdc, tic = exppro.get_set_costs_from_lpfile(
            lp_file, self.om
        )

        expected_values_tdc = {
            "b_diesel_diesel": 2,
            "diesel_b_el1": 1,
            "b_el1_storage": 3,
            "storage_b_el2": 2.5,
        }
        for name, val in expected_values_tdc.items():
            assert all(tdc[name] == val)

        period = 0
        expected_values_tic = {
            "invest_diesel_b_el1_" + str(period): 0.5,
            "invest_storage_" + str(period): 0.4,
        }
        for name, val in expected_values_tic.items():
            assert tic[name][0] == val

    def test_get_time_dependent_results_as_dataframe(self):
        results = processing.results(self.om, remove_last_time_point=True)
        results_dataframe = exppro.time_dependent_values_as_dataframe(
            results
        )

        assert isinstance(results_dataframe, pandas.DataFrame)

    def test_time_indepentden_results_as_dataframe(self):

        results = processing.results(self.om, remove_last_time_point=True)
        results_dataframe = exppro.time_independent_values_as_dataframe(
            results
        )

        assert isinstance(results_dataframe, pandas.DataFrame)
