# -*- coding: utf-8 -

"""Tests the processing module of solph.

This file is part of project oemof (github.com/oemof/oemof). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location oemof/tests/test_processing.py

SPDX-License-Identifier: MIT
"""

import pandas
from nose.tools import assert_raises
from nose.tools import eq_
from nose.tools import ok_
from pandas.testing import assert_frame_equal
from pandas.testing import assert_series_equal

from oemof.solph import Bus
from oemof.solph import EnergySystem
from oemof.solph import Flow
from oemof.solph import Investment
from oemof.solph import Model
from oemof.solph import Sink
from oemof.solph import Transformer
from oemof.solph import processing
from oemof.solph import views
from oemof.solph.components import GenericStorage


class TestParameterResult:
    @classmethod
    def setup_class(cls):
        cls.period = 24
        cls.es = EnergySystem(
            timeindex=pandas.date_range(
                '2016-01-01',
                periods=cls.period,
                freq='H'
            )
        )

        # BUSSES
        b_el1 = Bus(label="b_el1")
        b_el2 = Bus(label="b_el2")
        b_diesel = Bus(label='b_diesel', balanced=False)
        cls.es.add(b_el1, b_el2, b_diesel)

        # TEST DIESEL:
        dg = Transformer(
            label='diesel',
            inputs={b_diesel: Flow(variable_costs=2)},
            outputs={
                b_el1: Flow(
                    variable_costs=1,
                    investment=Investment(ep_costs=0.5)
                )
            },
            conversion_factors={b_el1: 2},
        )

        batt = GenericStorage(
            label='storage',
            inputs={b_el1: Flow(variable_costs=3)},
            outputs={b_el2: Flow(variable_costs=2.5)},
            loss_rate=0.00,
            initial_storage_level=0,
            invest_relation_input_capacity=1/6,
            invest_relation_output_capacity=1/6,
            inflow_conversion_factor=1,
            outflow_conversion_factor=0.8,
            investment=Investment(ep_costs=0.4),
        )

        cls.demand_values = [0.0] + [100] * 23
        demand = Sink(
            label="demand_el",
            inputs={
                b_el2: Flow(
                    nominal_value=1,
                    fix=cls.demand_values,
                )
            }
        )
        cls.es.add(dg, batt, demand)
        cls.om = Model(cls.es)
        cls.om.receive_duals()
        cls.om.solve()
        cls.mod = Model(cls.es)
        cls.mod.solve()

    def test_flows_with_none_exclusion(self):
        b_el2 = self.es.groups['b_el2']
        demand = self.es.groups['demand_el']
        param_results = processing.parameter_as_dict(self.es,
                                                     exclude_none=True)
        assert_series_equal(
            param_results[(b_el2, demand)]['scalars'].sort_index(),
            pandas.Series(
                {
                    'nominal_value': 1,
                    'max': 1,
                    'min': 0,
                    'negative_gradient_costs': 0,
                    'positive_gradient_costs': 0,
                    'variable_costs': 0,
                    'label': str(b_el2.outputs[demand].label),
                }
            ).sort_index()
        )
        assert_frame_equal(
            param_results[(b_el2, demand)]['sequences'],
            pandas.DataFrame(
                {'fix': self.demand_values}
            ), check_like=True
        )

    def test_flows_without_none_exclusion(self):
        b_el2 = self.es.groups['b_el2']
        demand = self.es.groups['demand_el']
        param_results = processing.parameter_as_dict(self.es,
                                                     exclude_none=False)
        scalar_attributes = {
            'integer': None,
            'investment': None,
            'nominal_value': 1,
            'nonconvex': None,
            'summed_max': None,
            'summed_min': None,
            'max': 1,
            'min': 0,
            'negative_gradient_ub': None,
            'negative_gradient_costs': 0,
            'positive_gradient_ub': None,
            'positive_gradient_costs': 0,
            'variable_costs': 0,
            'flow': None,
            'values': None,
            'label': str(b_el2.outputs[demand].label),
        }
        assert_series_equal(
            param_results[(b_el2, demand)]['scalars'].sort_index(),
            pandas.Series(scalar_attributes).sort_index()
        )
        sequences_attributes = {
            'fix': self.demand_values,
        }

        assert_frame_equal(
            param_results[(b_el2, demand)]['sequences'],
            pandas.DataFrame(sequences_attributes), check_like=True
        )

    def test_nodes_with_none_exclusion(self):
        param_results = processing.parameter_as_dict(
            self.es, exclude_none=True)
        param_results = processing.convert_keys_to_strings(param_results)
        assert_series_equal(
            param_results[('storage', 'None')]['scalars'],
            pandas.Series({
                'balanced': True,
                'initial_storage_level': 0,
                'invest_relation_input_capacity': 1/6,
                'invest_relation_output_capacity': 1/6,
                'investment_ep_costs': 0.4,
                'investment_existing': 0,
                'investment_maximum': float('inf'),
                'investment_minimum': 0,
                'investment_nonconvex': False,
                'investment_offset': 0,
                'label': 'storage',
                'fixed_losses_absolute': 0,
                'fixed_losses_relative': 0,
                'inflow_conversion_factor': 1,
                'loss_rate': 0,
                'max_storage_level': 1,
                'min_storage_level': 0,
                'outflow_conversion_factor': 0.8,
            })
        )
        assert_frame_equal(
            param_results[('storage', 'None')]['sequences'],
            pandas.DataFrame()
        )

    def test_nodes_with_none_exclusion_old_name(self):
        param_results = processing.parameter_as_dict(
            self.es, exclude_none=True)
        param_results = processing.convert_keys_to_strings(
            param_results, keep_none_type=True)
        assert_series_equal(
            param_results[('storage', None)]['scalars'],
            pandas.Series({
                'balanced': True,
                'initial_storage_level': 0,
                'invest_relation_input_capacity': 1/6,
                'invest_relation_output_capacity': 1/6,
                'investment_ep_costs': 0.4,
                'investment_existing': 0,
                'investment_maximum': float('inf'),
                'investment_minimum': 0,
                'investment_nonconvex': False,
                'investment_offset': 0,
                'label': 'storage',
                'fixed_losses_absolute': 0,
                'fixed_losses_relative': 0,
                'inflow_conversion_factor': 1,
                'loss_rate': 0,
                'max_storage_level': 1,
                'min_storage_level': 0,
                'outflow_conversion_factor': 0.8,
            })
        )
        assert_frame_equal(
            param_results[('storage', None)]['sequences'],
            pandas.DataFrame()
        )

    def test_nodes_without_none_exclusion(self):
        diesel = self.es.groups['diesel']
        param_results = processing.parameter_as_dict(
            self.es, exclude_none=False)
        assert_series_equal(
            param_results[(diesel, None)]['scalars'],
            pandas.Series({
                'label': 'diesel',
                'conversion_factors_b_el1': 2,
                'conversion_factors_b_diesel': 1,
            })
        )
        assert_frame_equal(
            param_results[(diesel, None)]['sequences'],
            pandas.DataFrame()
        )

    def test_parameter_with_node_view(self):
        param_results = processing.parameter_as_dict(
            self.es, exclude_none=True)
        bel1 = views.node(param_results, 'b_el1')
        assert (
            bel1['scalars'][[(('b_el1', 'storage'), 'variable_costs')]].values
            == 3
        )

        bel1_m = views.node(param_results, 'b_el1', multiindex=True)
        eq_(bel1_m['scalars'][('b_el1', 'storage', 'variable_costs')], 3)

    def test_multiindex_sequences(self):
        results = processing.results(self.om)
        bel1 = views.node(results, 'b_el1', multiindex=True)
        eq_(int(bel1['sequences'][('diesel', 'b_el1', 'flow')].sum()), 2875)

    def test_error_from_nan_values(self):
        trsf = self.es.groups['diesel']
        bus = self.es.groups['b_el1']
        self.mod.flow[trsf, bus, 5] = float('nan')
        with assert_raises(ValueError):
            processing.results(self.mod)

    def test_duals(self):
        results = processing.results(self.om)
        bel = views.node(results, 'b_el1', multiindex=True)
        eq_(int(bel['sequences']['b_el1', 'None', 'duals'].sum()), 48)

    def test_node_weight_by_type(self):
        results = processing.results(self.om)
        storage_content = views.node_weight_by_type(
            results, node_type=GenericStorage)
        eq_(round(float(storage_content.sum()), 6),
            1437.500003)

    def test_output_by_type_view(self):
        results = processing.results(self.om)
        transformer_output = views.node_output_by_type(results,
                                                       node_type=Transformer)
        compare = views.node(
            results, 'diesel', multiindex=True)['sequences'][(
                'diesel', 'b_el1', 'flow')]
        eq_(int(transformer_output.sum()), int(compare.sum()))

    def test_input_by_type_view(self):
        results = processing.results(self.om)
        sink_input = views.node_input_by_type(results, node_type=Sink)
        compare = views.node(results, 'demand_el', multiindex=True)
        eq_(int(sink_input.sum()),
            int(compare['sequences'][('b_el2', 'demand_el', 'flow')].sum()))

    def test_net_storage_flow(self):
        results = processing.results(self.om)
        storage_flow = views.net_storage_flow(
            results, node_type=GenericStorage)
        compare = views.node(
            results, 'storage', multiindex=True)['sequences']
        eq_(
            ((compare[('storage', 'b_el2', 'flow')] -
              compare[('b_el1', 'storage', 'flow')]).to_frame() ==
             storage_flow.values).all()[0], True)

    def test_output_by_type_view_empty(self):
        results = processing.results(self.om)
        view = views.node_output_by_type(results, node_type=Flow)
        ok_(view is None)

    def test_input_by_type_view_empty(self):
        results = processing.results(self.om)
        view = views.node_input_by_type(results, node_type=Flow)
        ok_(view is None)

    def test_net_storage_flow_empty(self):
        results = processing.results(self.om)
        view = views.net_storage_flow(results, node_type=Sink)
        ok_(view is None)
        view2 = views.net_storage_flow(results, node_type=Flow)
        ok_(view2 is None)

    def test_node_weight_by_type_empty(self):
        results = processing.results(self.om)
        view = views.node_weight_by_type(results, node_type=Flow)
        ok_(view is None)
