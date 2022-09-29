# -*- coding: utf-8 -

"""Test the created constraints against approved constraints.

This file is part of project oemof (github.com/oemof/oemof). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location oemof/tests/constraint_tests.py

SPDX-License-Identifier: MIT
"""

import logging
import re
from difflib import unified_diff
from os import path as ospath

import pandas as pd
import pytest
from nose.tools import assert_raises
from nose.tools import eq_
from oemof.network.network import Node

from oemof import solph

logging.disable(logging.INFO)


class TestsConstraint:
    @classmethod
    def setup_class(cls):
        cls.objective_pattern = re.compile(
            r"^objective.*(?=s\.t\.)", re.DOTALL | re.MULTILINE
        )

        cls.date_time_index = pd.date_range("1/1/2012", periods=3, freq="H")

        cls.tmppath = solph.helpers.extend_basic_path("tmp")
        logging.info(cls.tmppath)

    def setup(self):
        self.energysystem = solph.EnergySystem(
            groupings=solph.GROUPINGS, timeindex=self.date_time_index
        )
        Node.registry = self.energysystem

    def get_om(self):
        return solph.Model(
            self.energysystem, timeindex=self.energysystem.timeindex
        )

    def compare_lp_files(self, filename, ignored=None, my_om=None):
        r"""Compare lp-files to check constraints generated within solph.

        An lp-file is being generated automatically when the tests are
        executed. Make sure that you create an empty file first and
        transfer the content from the one that has been created automatically
        into this one afterwards. Please ensure that the content is being
        checked carefully. Otherwise, errors are included within the code base.
        """
        if my_om is None:
            om = self.get_om()
        else:
            om = my_om
        tmp_filename = filename.replace(".lp", "") + "_tmp.lp"
        new_filename = ospath.join(self.tmppath, tmp_filename)
        om.write(new_filename, io_options={"symbolic_solver_labels": True})
        logging.info("Comparing with file: {0}".format(filename))
        with open(ospath.join(self.tmppath, tmp_filename)) as generated_file:
            with open(
                ospath.join(
                    ospath.dirname(ospath.realpath(__file__)),
                    "lp_files",
                    filename,
                )
            ) as expected_file:

                def chop_trailing_whitespace(lines):
                    return [re.sub(r"\s*$", "", ln) for ln in lines]

                def remove(pattern, lines):
                    if not pattern:
                        return lines
                    return re.subn(pattern, "", "\n".join(lines))[0].split(
                        "\n"
                    )

                expected = remove(
                    ignored,
                    chop_trailing_whitespace(expected_file.readlines()),
                )
                generated = remove(
                    ignored,
                    chop_trailing_whitespace(generated_file.readlines()),
                )

                def normalize_to_positive_results(lines):
                    negative_result_indices = [
                        n
                        for n, line in enumerate(lines)
                        if re.match("^= -", line)
                    ]
                    equation_start_indices = [
                        [
                            n
                            for n in reversed(range(0, nri))
                            if re.match(".*:$", lines[n])
                        ][0]
                        + 1
                        for nri in negative_result_indices
                    ]
                    for (start, end) in zip(
                        equation_start_indices, negative_result_indices
                    ):
                        for n in range(start, end):
                            lines[n] = (
                                "-"
                                if lines[n] and lines[n][0] == "+"
                                else "+"
                                if lines[n]
                                else lines[n]
                            ) + lines[n][1:]
                        lines[end] = "= " + lines[end][3:]
                    return lines

                expected = normalize_to_positive_results(expected)
                generated = normalize_to_positive_results(generated)

                eq_(
                    generated,
                    expected,
                    "Failed matching expected with generated lp file:\n"
                    + "\n".join(
                        unified_diff(
                            expected,
                            generated,
                            fromfile=ospath.relpath(expected_file.name),
                            tofile=ospath.basename(generated_file.name),
                            lineterm="",
                        )
                    ),
                )

    def test_linear_transformer(self):
        """Constraint test of a Transformer without Investment."""
        bgas = solph.buses.Bus(label="gas")

        bel = solph.buses.Bus(label="electricity")

        solph.components.Transformer(
            label="powerplantGas",
            inputs={bgas: solph.flows.Flow()},
            outputs={
                bel: solph.flows.Flow(nominal_value=10e10, variable_costs=50)
            },
            conversion_factors={bel: 0.58},
        )

        self.compare_lp_files("linear_transformer.lp")

    def test_linear_transformer_invest(self):
        """Constraint test of a Transformer with Investment."""

        bgas = solph.buses.Bus(label="gas")

        bel = solph.buses.Bus(label="electricity")

        solph.components.Transformer(
            label="powerplant_gas",
            inputs={bgas: solph.flows.Flow()},
            outputs={
                bel: solph.flows.Flow(
                    variable_costs=50,
                    investment=solph.Investment(maximum=1000, ep_costs=20),
                )
            },
            conversion_factors={bel: 0.58},
        )

        self.compare_lp_files("linear_transformer_invest.lp")

    def test_max_source_min_sink(self):
        """ """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="wind",
            outputs={
                bel: solph.flows.Flow(nominal_value=54, max=(0.85, 0.95, 0.61))
            },
        )

        solph.components.Sink(
            label="minDemand",
            inputs={
                bel: solph.flows.Flow(
                    nominal_value=54, min=(0.84, 0.94, 0.59), variable_costs=14
                )
            },
        )

        self.compare_lp_files("max_source_min_sink.lp")

    def test_fixed_source_variable_sink(self):
        """Constraint test with a fixed source and a variable sink."""

        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="wind",
            outputs={
                bel: solph.flows.Flow(
                    fix=[0.43, 0.72, 0.29], nominal_value=10e5
                )
            },
        )

        solph.components.Sink(
            label="excess", inputs={bel: solph.flows.Flow(variable_costs=40)}
        )

        self.compare_lp_files("fixed_source_variable_sink.lp")

    def test_nominal_value_to_zero(self):
        """If the nominal value is set to zero nothing should happen."""
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="s1", outputs={bel: solph.flows.Flow(nominal_value=0)}
        )
        self.compare_lp_files("nominal_value_to_zero.lp")

    def test_fixed_source_invest_sink(self):
        """
        Wrong constraints for fixed source + invest sink w.
        `full_load_time_max`.
        """

        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="wind",
            outputs={
                bel: solph.flows.Flow(fix=[12, 16, 14], nominal_value=1000000)
            },
        )

        solph.components.Sink(
            label="excess",
            inputs={
                bel: solph.flows.InvestmentFlow(
                    full_load_time_max=2.3,
                    variable_costs=25,
                    max=0.8,
                    investment=solph.Investment(
                        ep_costs=500, maximum=10e5, existing=50
                    ),
                )
            },
        )

        self.compare_lp_files("fixed_source_invest_sink.lp")

    def test_invest_source_fixed_sink(self):
        """Constraint test with a fixed sink and a dispatch invest source."""

        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="pv",
            outputs={
                bel: solph.flows.Flow(
                    max=[45, 83, 65],
                    variable_costs=13,
                    investment=solph.Investment(ep_costs=123),
                )
            },
        )

        solph.components.Sink(
            label="excess",
            inputs={
                bel: solph.flows.Flow(fix=[0.5, 0.8, 0.3], nominal_value=10e4)
            },
        )

        self.compare_lp_files("invest_source_fixed_sink.lp")

    def test_storage(self):
        """ """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage_no_invest",
            inputs={
                bel: solph.flows.Flow(nominal_value=16667, variable_costs=56)
            },
            outputs={
                bel: solph.flows.Flow(nominal_value=16667, variable_costs=24)
            },
            nominal_storage_capacity=10e4,
            loss_rate=0.13,
            inflow_conversion_factor=0.97,
            outflow_conversion_factor=0.86,
            initial_storage_level=0.4,
        )

        self.compare_lp_files("storage.lp")

    def test_storage_invest_1(self):
        """All invest variables are coupled. The invest variables of the Flows
        will be created during the initialisation of the storage e.g. battery
        """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage1",
            inputs={bel: solph.flows.Flow(variable_costs=56)},
            outputs={bel: solph.flows.Flow(variable_costs=24)},
            nominal_storage_capacity=None,
            loss_rate=0.13,
            max_storage_level=0.9,
            min_storage_level=0.1,
            invest_relation_input_capacity=1 / 6,
            invest_relation_output_capacity=1 / 6,
            inflow_conversion_factor=0.97,
            outflow_conversion_factor=0.86,
            investment=solph.Investment(ep_costs=145, maximum=234),
        )

        self.compare_lp_files("storage_invest_1.lp")

    def test_storage_invest_2(self):
        """All can be free extended to their own cost."""
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage2",
            inputs={
                bel: solph.flows.Flow(investment=solph.Investment(ep_costs=99))
            },
            outputs={
                bel: solph.flows.Flow(investment=solph.Investment(ep_costs=9))
            },
            investment=solph.Investment(ep_costs=145),
            initial_storage_level=0.5,
        )
        self.compare_lp_files("storage_invest_2.lp")

    def test_storage_invest_3(self):
        """The storage capacity is fixed, but the Flows can be extended.
        e.g. PHES with a fixed basin but the pump and the turbine can be
        adapted
        """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage3",
            inputs={
                bel: solph.flows.Flow(investment=solph.Investment(ep_costs=99))
            },
            outputs={
                bel: solph.flows.Flow(investment=solph.Investment(ep_costs=9))
            },
            nominal_storage_capacity=5000,
        )
        self.compare_lp_files("storage_invest_3.lp")

    def test_storage_invest_4(self):
        """Only the storage capacity can be extended."""
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage4",
            inputs={bel: solph.flows.Flow(nominal_value=80)},
            outputs={bel: solph.flows.Flow(nominal_value=100)},
            investment=solph.Investment(ep_costs=145, maximum=500),
        )
        self.compare_lp_files("storage_invest_4.lp")

    def test_storage_invest_5(self):
        """The storage capacity is fixed, but the Flows can be extended.
        e.g. PHES with a fixed basin but the pump and the turbine can be
        adapted. The installed capacity of the pump is 10 % bigger than the
        the capacity of the turbine due to 'invest_relation_input_output=1.1'.
        """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage5",
            inputs={
                bel: solph.flows.Flow(
                    investment=solph.Investment(ep_costs=99, existing=110)
                )
            },
            outputs={
                bel: solph.flows.Flow(
                    investment=solph.Investment(existing=100)
                )
            },
            invest_relation_input_output=1.1,
            nominal_storage_capacity=10000,
        )
        self.compare_lp_files("storage_invest_5.lp")

    def test_storage_invest_6(self):
        """Like test_storage_invest_5 but there can also be an investment in
        the basin.
        """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage6",
            inputs={
                bel: solph.flows.InvestmentFlow(
                    investment=solph.Investment(ep_costs=99, existing=110)
                )
            },
            outputs={
                bel: solph.flows.InvestmentFlow(
                    investment=solph.Investment(existing=100)
                )
            },
            invest_relation_input_output=1.1,
            investment=solph.Investment(ep_costs=145, existing=10000),
        )
        self.compare_lp_files("storage_invest_6.lp")

    def test_storage_minimum_invest(self):
        """All invest variables are coupled. The invest variables of the Flows
        will be created during the initialisation of the storage e.g. battery
        """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage1",
            inputs={bel: solph.flows.Flow()},
            outputs={bel: solph.flows.Flow()},
            investment=solph.Investment(
                ep_costs=145, minimum=100, maximum=200
            ),
        )

        self.compare_lp_files("storage_invest_minimum.lp")

    def test_storage_unbalanced(self):
        """Testing a unbalanced storage (e.g. battery)."""
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage1",
            inputs={bel: solph.flows.Flow()},
            outputs={bel: solph.flows.Flow()},
            nominal_storage_capacity=1111,
            initial_storage_level=None,
            balanced=False,
            invest_relation_input_capacity=1,
            invest_relation_output_capacity=1,
        )
        self.compare_lp_files("storage_unbalanced.lp")

    def test_storage_invest_unbalanced(self):
        """Testing a unbalanced storage (e.g. battery)."""
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage1",
            inputs={bel: solph.flows.Flow()},
            outputs={bel: solph.flows.Flow()},
            nominal_storage_capacity=None,
            initial_storage_level=0.5,
            balanced=False,
            invest_relation_input_capacity=1,
            invest_relation_output_capacity=1,
            investment=solph.Investment(ep_costs=145),
        )
        self.compare_lp_files("storage_invest_unbalanced.lp")

    def test_storage_fixed_losses(self):
        """ """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage_no_invest",
            inputs={
                bel: solph.flows.Flow(nominal_value=16667, variable_costs=56)
            },
            outputs={
                bel: solph.flows.Flow(nominal_value=16667, variable_costs=24)
            },
            nominal_storage_capacity=1e5,
            loss_rate=0.13,
            fixed_losses_relative=0.01,
            fixed_losses_absolute=3,
            inflow_conversion_factor=0.97,
            outflow_conversion_factor=0.86,
            initial_storage_level=0.4,
        )

        self.compare_lp_files("storage_fixed_losses.lp")

    def test_storage_invest_1_fixed_losses(self):
        """All invest variables are coupled. The invest variables of the Flows
        will be created during the initialisation of the storage e.g. battery
        """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage1",
            inputs={bel: solph.flows.Flow(variable_costs=56)},
            outputs={bel: solph.flows.Flow(variable_costs=24)},
            nominal_storage_capacity=None,
            loss_rate=0.13,
            fixed_losses_relative=0.01,
            fixed_losses_absolute=3,
            max_storage_level=0.9,
            min_storage_level=0.1,
            invest_relation_input_capacity=1 / 6,
            invest_relation_output_capacity=1 / 6,
            inflow_conversion_factor=0.97,
            outflow_conversion_factor=0.86,
            investment=solph.Investment(ep_costs=145, maximum=234),
        )

        self.compare_lp_files("storage_invest_1_fixed_losses.lp")

    def test_transformer(self):
        """Constraint test of a LinearN1Transformer without Investment."""
        bgas = solph.buses.Bus(label="gasBus")
        bbms = solph.buses.Bus(label="biomassBus")
        bel = solph.buses.Bus(label="electricityBus")
        bth = solph.buses.Bus(label="thermalBus")

        solph.components.Transformer(
            label="powerplantGasCoal",
            inputs={bbms: solph.flows.Flow(), bgas: solph.flows.Flow()},
            outputs={
                bel: solph.flows.Flow(variable_costs=50),
                bth: solph.flows.Flow(nominal_value=5e10, variable_costs=20),
            },
            conversion_factors={bgas: 0.4, bbms: 0.1, bel: 0.3, bth: 0.5},
        )

        self.compare_lp_files("transformer.lp")

    def test_transformer_invest(self):
        """Constraint test of a LinearN1Transformer with Investment."""

        bgas = solph.buses.Bus(label="gasBus")
        bcoal = solph.buses.Bus(label="coalBus")
        bel = solph.buses.Bus(label="electricityBus")
        bth = solph.buses.Bus(label="thermalBus")

        solph.components.Transformer(
            label="powerplant_gas_coal",
            inputs={bgas: solph.flows.Flow(), bcoal: solph.flows.Flow()},
            outputs={
                bel: solph.flows.Flow(
                    variable_costs=50,
                    investment=solph.Investment(maximum=1000, ep_costs=20),
                ),
                bth: solph.flows.Flow(variable_costs=20),
            },
            conversion_factors={bgas: 0.58, bcoal: 0.2, bel: 0.3, bth: 0.5},
        )

        self.compare_lp_files("transformer_invest.lp")

    def test_transformer_invest_with_existing(self):
        """Constraint test of a LinearN1Transformer with Investment."""

        bgas = solph.buses.Bus(label="gasBus")
        bcoal = solph.buses.Bus(label="coalBus")
        bel = solph.buses.Bus(label="electricityBus")
        bth = solph.buses.Bus(label="thermalBus")

        solph.components.Transformer(
            label="powerplant_gas_coal",
            inputs={bgas: solph.flows.Flow(), bcoal: solph.flows.Flow()},
            outputs={
                bel: solph.flows.Flow(
                    variable_costs=50,
                    investment=solph.Investment(
                        maximum=1000, ep_costs=20, existing=200
                    ),
                ),
                bth: solph.flows.Flow(variable_costs=20),
            },
            conversion_factors={bgas: 0.58, bcoal: 0.2, bel: 0.3, bth: 0.5},
        )

        self.compare_lp_files("transformer_invest_with_existing.lp")

    def test_linear_transformer_chp(self):
        """
        Constraint test of a Transformer without Investment (two outputs).
        """
        bgas = solph.buses.Bus(label="gasBus")
        bheat = solph.buses.Bus(label="heatBus")
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Transformer(
            label="CHPpowerplantGas",
            inputs={
                bgas: solph.flows.Flow(nominal_value=10e10, variable_costs=50)
            },
            outputs={bel: solph.flows.Flow(), bheat: solph.flows.Flow()},
            conversion_factors={bel: 0.4, bheat: 0.5},
        )

        self.compare_lp_files("linear_transformer_chp.lp")

    def test_linear_transformer_chp_invest(self):
        """Constraint test of a Transformer with Investment (two outputs)."""

        bgas = solph.buses.Bus(label="gasBus")
        bheat = solph.buses.Bus(label="heatBus")
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Transformer(
            label="chp_powerplant_gas",
            inputs={
                bgas: solph.flows.Flow(
                    variable_costs=50,
                    investment=solph.Investment(maximum=1000, ep_costs=20),
                )
            },
            outputs={bel: solph.flows.Flow(), bheat: solph.flows.Flow()},
            conversion_factors={bel: 0.4, bheat: 0.5},
        )

        self.compare_lp_files("linear_transformer_chp_invest.lp")

    def test_variable_chp(self):
        """ """
        bel = solph.buses.Bus(label="electricityBus")
        bth = solph.buses.Bus(label="heatBus")
        bgas = solph.buses.Bus(label="commodityBus")

        solph.components.ExtractionTurbineCHP(
            label="variable_chp_gas1",
            inputs={bgas: solph.flows.Flow(nominal_value=100)},
            outputs={bel: solph.flows.Flow(), bth: solph.flows.Flow()},
            conversion_factors={bel: 0.3, bth: 0.5},
            conversion_factor_full_condensation={bel: 0.5},
        )

        solph.components.ExtractionTurbineCHP(
            label="variable_chp_gas2",
            inputs={bgas: solph.flows.Flow(nominal_value=100)},
            outputs={bel: solph.flows.Flow(), bth: solph.flows.Flow()},
            conversion_factors={bel: 0.3, bth: 0.5},
            conversion_factor_full_condensation={bel: 0.5},
        )

        self.compare_lp_files("variable_chp.lp")

    def test_generic_invest_limit(self):
        """ """
        bus = solph.buses.Bus(label="bus_1")

        solph.components.Source(
            label="source_0",
            outputs={
                bus: solph.flows.Flow(
                    investment=solph.Investment(ep_costs=50, space=4)
                )
            },
        )

        solph.components.Source(
            label="source_1",
            outputs={
                bus: solph.flows.Flow(
                    investment=solph.Investment(ep_costs=100, space=1)
                )
            },
        )

        solph.components.Source(
            label="source_2",
            outputs={
                bus: solph.flows.Flow(investment=solph.Investment(ep_costs=75))
            },
        )

        om = self.get_om()

        om = solph.constraints.additional_investment_flow_limit(
            om, "space", limit=20
        )

        self.compare_lp_files("generic_invest_limit.lp", my_om=om)

    def test_emission_constraints(self):
        """ """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="source1",
            outputs={
                bel: solph.flows.Flow(
                    nominal_value=100, emission_factor=[0.5, -1.0, 2.0]
                )
            },
        )
        solph.components.Source(
            label="source2",
            outputs={
                bel: solph.flows.Flow(nominal_value=100, emission_factor=3.5)
            },
        )

        # Should be ignored because the emission attribute is not defined.
        solph.components.Source(
            label="source3", outputs={bel: solph.flows.Flow(nominal_value=100)}
        )

        om = self.get_om()

        solph.constraints.emission_limit(om, limit=777)

        self.compare_lp_files("emission_limit.lp", my_om=om)

    def test_flow_count_limit(self):
        """ """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="source1",
            outputs={
                bel: solph.flows.Flow(
                    nonconvex=solph.NonConvex(),
                    nominal_value=100,
                    emission_factor=[0.5, -1.0, 2.0],
                )
            },
        )
        solph.components.Source(
            label="source2",
            outputs={
                bel: solph.flows.Flow(
                    nonconvex=solph.NonConvex(),
                    nominal_value=100,
                    emission_factor=3.5,
                )
            },
        )

        # Should be ignored because emission_factor is not defined.
        solph.components.Source(
            label="source3",
            outputs={
                bel: solph.flows.Flow(
                    nonconvex=solph.NonConvex(), nominal_value=100
                )
            },
        )

        # Should be ignored because it is not NonConvex.
        solph.components.Source(
            label="source4",
            outputs={
                bel: solph.flows.Flow(
                    emission_factor=1.5, min=0.3, nominal_value=100
                )
            },
        )

        om = self.get_om()

        # one of the two flows has to be active
        solph.constraints.limit_active_flow_count_by_keyword(
            om, "emission_factor", lower_limit=1, upper_limit=2
        )

        self.compare_lp_files("flow_count_limit.lp", my_om=om)

    def test_shared_limit(self):
        """ """
        b1 = solph.buses.Bus(label="bus")

        storage1 = solph.components.GenericStorage(
            label="storage1",
            nominal_storage_capacity=5,
            inputs={b1: solph.flows.Flow()},
            outputs={b1: solph.flows.Flow()},
        )
        storage2 = solph.components.GenericStorage(
            label="storage2",
            nominal_storage_capacity=5,
            inputs={b1: solph.flows.Flow()},
            outputs={b1: solph.flows.Flow()},
        )

        model = self.get_om()

        components = [storage1, storage2]

        solph.constraints.shared_limit(
            model,
            model.GenericStorageBlock.storage_content,
            "limit_storage",
            components,
            [0.5, 1.25],
            upper_limit=7,
        )

        self.compare_lp_files("shared_limit.lp", my_om=model)

    def test_flow_without_emission_for_emission_constraint(self):
        """ """

        def define_emission_limit():
            bel = solph.buses.Bus(label="electricityBus")
            solph.components.Source(
                label="source1",
                outputs={
                    bel: solph.flows.Flow(
                        nominal_value=100, emission_factor=0.8
                    )
                },
            )
            solph.components.Source(
                label="source2",
                outputs={bel: solph.flows.Flow(nominal_value=100)},
            )
            om = self.get_om()
            solph.constraints.emission_limit(om, om.flows, limit=777)

        assert_raises(AttributeError, define_emission_limit)

    def test_flow_without_emission_for_emission_constraint_no_error(self):
        """ """
        bel = solph.buses.Bus(label="electricityBus")
        solph.components.Source(
            label="source1",
            outputs={
                bel: solph.flows.Flow(nominal_value=100, emission_factor=0.8)
            },
        )
        solph.components.Source(
            label="source2", outputs={bel: solph.flows.Flow(nominal_value=100)}
        )
        om = self.get_om()
        solph.constraints.emission_limit(om, limit=777)

    def test_equate_variables_constraint(self):
        """Testing the equate_variables function in the constraint module."""
        bus1 = solph.buses.Bus(label="Bus1")
        storage = solph.components.GenericStorage(
            label="storage_constraint",
            invest_relation_input_capacity=0.2,
            invest_relation_output_capacity=0.2,
            inputs={bus1: solph.flows.Flow()},
            outputs={bus1: solph.flows.Flow()},
            investment=solph.Investment(ep_costs=145),
        )
        sink = solph.components.Sink(
            label="Sink",
            inputs={
                bus1: solph.flows.Flow(
                    investment=solph.Investment(ep_costs=500)
                )
            },
        )
        source = solph.components.Source(
            label="Source",
            outputs={
                bus1: solph.flows.Flow(
                    investment=solph.Investment(ep_costs=123)
                )
            },
        )
        om = self.get_om()
        solph.constraints.equate_variables(
            om,
            om.InvestmentFlowBlock.invest[source, bus1],
            om.InvestmentFlowBlock.invest[bus1, sink],
            2,
        )
        solph.constraints.equate_variables(
            om,
            om.InvestmentFlowBlock.invest[source, bus1],
            om.GenericInvestmentStorageBlock.invest[storage],
        )

        self.compare_lp_files("connect_investment.lp", my_om=om)

    def test_flow_idle(self):
        bus = solph.buses.Bus(label="Bus")
        sink = solph.components.Sink(
            label="Sink",
            inputs={
                bus: solph.flows.Flow(
                    nominal_value=1,
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

        om = self.get_om()
        solph.constraints.set_idle_time(om, (source, bus), (bus, sink), n=1)

        self.compare_lp_files("set_idle_time.lp", my_om=om)


    def test_gradient(self):
        """Testing gradient constraints and costs."""
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="powerplant",
            outputs={
                bel: solph.flows.Flow(
                    nominal_value=999,
                    variable_costs=23,
                    positive_gradient={"ub": 0.03},
                    negative_gradient={"ub": 0.05},
                )
            },
        )

        self.compare_lp_files("source_with_gradient.lp")

    def test_nonconvex_gradient(self):
        """Testing gradient constraints and costs."""
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="powerplant",
            outputs={
                bel: solph.flows.Flow(
                    nominal_value=999,
                    variable_costs=23,
                    nonconvex=solph.NonConvex(
                        positive_gradient={"ub": 0.03},
                        negative_gradient={"ub": 0.05},
                    ),
                )
            },
        )

        self.compare_lp_files("source_with_nonconvex_gradient.lp")

    def test_nonconvex_positive_gradient_error(self):
        """Testing nonconvex positive gradient error."""
        msg = (
            "You specified a positive gradient in your nonconvex "
            "option. This cannot be combined with a positive or a "
            "negative gradient for a standard flow!"
        )

        with pytest.raises(ValueError, match=msg):
            solph.flows.Flow(
                nonconvex=solph.NonConvex(
                    positive_gradient={"ub": 0.03},
                ),
                positive_gradient={"ub": 0.03},
            )

    def test_nonconvex_negative_gradient_error(self):
        """Testing nonconvex positive gradient error."""
        msg = (
            "You specified a negative gradient in your nonconvex "
            "option. This cannot be combined with a positive or a "
            "negative gradient for a standard flow!"
        )

        with pytest.raises(ValueError, match=msg):
            solph.flows.Flow(
                nonconvex=solph.NonConvex(
                    negative_gradient={"ub": 0.03, "costs": 7},
                ),
                negative_gradient={"ub": 0.03},
            )

    def test_investment_limit(self):
        """Testing the investment_limit function in the constraint module."""
        bus1 = solph.buses.Bus(label="Bus1")
        solph.components.GenericStorage(
            label="storage_invest_limit",
            invest_relation_input_capacity=0.2,
            invest_relation_output_capacity=0.2,
            inputs={bus1: solph.flows.Flow()},
            outputs={bus1: solph.flows.Flow()},
            investment=solph.Investment(ep_costs=145),
        )
        solph.components.Source(
            label="Source",
            outputs={
                bus1: solph.flows.Flow(
                    investment=solph.Investment(ep_costs=123)
                )
            },
        )
        om = self.get_om()
        solph.constraints.investment_limit(om, limit=900)

        self.compare_lp_files("investment_limit.lp", my_om=om)

    def test_min_max_runtime(self):
        """Testing min and max runtimes for nonconvex flows."""
        bus_t = solph.buses.Bus(label="Bus_T")
        solph.components.Source(
            label="cheap_plant_min_down_constraints",
            outputs={
                bus_t: solph.flows.NonConvexFlow(
                    nominal_value=10,
                    min=0.5,
                    max=1.0,
                    variable_costs=10,
                    minimum_downtime=4,
                    minimum_uptime=2,
                    initial_status=2,
                    startup_costs=5,
                    shutdown_costs=7,
                )
            },
        )
        self.compare_lp_files("min_max_runtime.lp")

    def test_activity_costs(self):
        """Testing activity_costs attribute for nonconvex flows."""
        bus_t = solph.buses.Bus(label="Bus_C")
        solph.components.Source(
            label="cheap_plant_activity_costs",
            outputs={
                bus_t: solph.flows.NonConvexFlow(
                    nominal_value=10,
                    min=0.5,
                    max=1.0,
                    variable_costs=10,
                    activity_costs=2,
                )
            },
        )
        self.compare_lp_files("activity_costs.lp")

    def test_inactivity_costs(self):
        """Testing inactivity_costs attribute for nonconvex flows."""
        bus_t = solph.buses.Bus(label="Bus_C")
        solph.components.Source(
            label="cheap_plant_inactivity_costs",
            outputs={
                bus_t: solph.flows.NonConvexFlow(
                    nominal_value=10,
                    min=0.5,
                    max=1.0,
                    variable_costs=10,
                    inactivity_costs=2,
                )
            },
        )
        self.compare_lp_files("inactivity_costs.lp")

    def test_piecewise_linear_transformer_cc(self):
        """Testing PiecewiseLinearTransformer using CC formulation."""
        bgas = solph.buses.Bus(label="gasBus")
        bel = solph.buses.Bus(label="electricityBus")
        solph.components.experimental.PiecewiseLinearTransformer(
            label="pwltf",
            inputs={
                bgas: solph.flows.Flow(nominal_value=100, variable_costs=1)
            },
            outputs={bel: solph.flows.Flow()},
            in_breakpoints=[0, 25, 50, 75, 100],
            conversion_function=lambda x: x**2,
            pw_repn="CC",
        )
        self.compare_lp_files("piecewise_linear_transformer_cc.lp")

    def test_piecewise_linear_transformer_dcc(self):
        """Testing PiecewiseLinearTransformer using DCC formulation."""
        bgas = solph.buses.Bus(label="gasBus")
        bel = solph.buses.Bus(label="electricityBus")
        solph.components.experimental.PiecewiseLinearTransformer(
            label="pwltf",
            inputs={
                bgas: solph.flows.Flow(nominal_value=100, variable_costs=1)
            },
            outputs={bel: solph.flows.Flow()},
            in_breakpoints=[0, 25, 50, 75, 100],
            conversion_function=lambda x: x**2,
            pw_repn="DCC",
        )
        self.compare_lp_files("piecewise_linear_transformer_dcc.lp")

    def test_maximum_startups(self):
        """Testing maximum_startups attribute for nonconvex flows."""
        bus_t = solph.buses.Bus(label="Bus_C")
        solph.components.Source(
            label="cheap_plant_maximum_startups",
            outputs={
                bus_t: solph.flows.Flow(
                    nominal_value=10,
                    min=0.5,
                    max=1.0,
                    variable_costs=10,
                    nonconvex=solph.NonConvex(maximum_startups=2),
                )
            },
        )
        self.compare_lp_files("maximum_startups.lp")

    def test_maximum_shutdowns(self):
        """Testing maximum_shutdowns attribute for nonconvex flows."""
        bus_t = solph.buses.Bus(label="Bus_C")
        solph.components.Source(
            label="cheap_plant_maximum_shutdowns",
            outputs={
                bus_t: solph.flows.Flow(
                    nominal_value=10,
                    min=0.5,
                    max=1.0,
                    variable_costs=10,
                    nonconvex=solph.NonConvex(maximum_shutdowns=2),
                )
            },
        )
        self.compare_lp_files("maximum_shutdowns.lp")

    def test_offsettransformer(self):
        """Constraint test of a OffsetTransformer."""
        bgas = solph.buses.Bus(label="gasBus")
        bth = solph.buses.Bus(label="thermalBus")

        solph.components.OffsetTransformer(
            label="gasboiler",
            inputs={
                bgas: solph.flows.Flow(
                    nonconvex=solph.NonConvex(),
                    nominal_value=100,
                    min=0.32,
                )
            },
            outputs={bth: solph.flows.Flow()},
            coefficients=[-17, 0.9],
        )

        self.compare_lp_files("offsettransformer.lp")

    def test_dsm_module_DIW(self):
        """Constraint test of SinkDSM with approach=DLR"""

        b_elec = solph.buses.Bus(label="bus_elec")
        solph.components.experimental.SinkDSM(
            label="demand_dsm",
            inputs={b_elec: solph.flows.Flow()},
            demand=[1] * 3,
            capacity_up=[0.5] * 3,
            capacity_down=[0.5] * 3,
            approach="DIW",
            max_demand=1,
            max_capacity_up=1,
            max_capacity_down=1,
            delay_time=1,
            cost_dsm_down_shift=2,
            shed_eligibility=False,
        )
        self.compare_lp_files("dsm_module_DIW.lp")

    def test_dsm_module_DLR(self):
        """Constraint test of SinkDSM with approach=DLR"""

        b_elec = solph.buses.Bus(label="bus_elec")
        solph.components.experimental.SinkDSM(
            label="demand_dsm",
            inputs={b_elec: solph.flows.Flow()},
            demand=[1] * 3,
            capacity_up=[0.5] * 3,
            capacity_down=[0.5] * 3,
            approach="DLR",
            max_demand=1,
            max_capacity_up=1,
            max_capacity_down=1,
            delay_time=2,
            shift_time=1,
            cost_dsm_down_shift=2,
            shed_eligibility=False,
        )
        self.compare_lp_files("dsm_module_DLR.lp")

    def test_dsm_module_oemof(self):
        """Constraint test of SinkDSM with approach=oemof"""

        b_elec = solph.buses.Bus(label="bus_elec")
        solph.components.experimental.SinkDSM(
            label="demand_dsm",
            inputs={b_elec: solph.flows.Flow()},
            demand=[1] * 3,
            capacity_up=[0.5, 0.4, 0.5],
            capacity_down=[0.5, 0.4, 0.5],
            approach="oemof",
            max_demand=1,
            max_capacity_up=1,
            max_capacity_down=1,
            shift_interval=2,
            cost_dsm_down_shift=2,
            shed_eligibility=False,
        )
        self.compare_lp_files("dsm_module_oemof.lp")

    def test_dsm_module_DIW_invest(self):
        """Constraint test of SinkDSM with approach=DLR and investments"""

        b_elec = solph.buses.Bus(label="bus_elec")
        solph.components.experimental.SinkDSM(
            label="demand_dsm",
            inputs={b_elec: solph.flows.Flow()},
            demand=[1] * 3,
            capacity_up=[0.5] * 3,
            capacity_down=[0.5] * 3,
            approach="DIW",
            flex_share_up=1,
            flex_share_down=1,
            delay_time=1,
            cost_dsm_down_shift=2,
            shed_eligibility=False,
            investment=solph.Investment(
                ep_cost=100, existing=50, minimum=33, maximum=100
            ),
        )
        self.compare_lp_files("dsm_module_DIW_invest.lp")

    def test_dsm_module_DLR_invest(self):
        """Constraint test of SinkDSM with approach=DLR and investments"""

        b_elec = solph.buses.Bus(label="bus_elec")
        solph.components.experimental.SinkDSM(
            label="demand_dsm",
            inputs={b_elec: solph.flows.Flow()},
            demand=[1] * 3,
            capacity_up=[0.5] * 3,
            capacity_down=[0.5] * 3,
            approach="DLR",
            flex_share_up=1,
            flex_share_down=1,
            delay_time=2,
            shift_time=1,
            cost_dsm_down_shift=2,
            shed_eligibility=False,
            investment=solph.Investment(
                ep_cost=100, existing=50, minimum=33, maximum=100
            ),
        )
        self.compare_lp_files("dsm_module_DLR_invest.lp")

    def test_dsm_module_oemof_invest(self):
        """Constraint test of SinkDSM with approach=oemof and investments"""

        b_elec = solph.buses.Bus(label="bus_elec")
        solph.components.experimental.SinkDSM(
            label="demand_dsm",
            inputs={b_elec: solph.flows.Flow()},
            demand=[1] * 3,
            capacity_up=[0.5, 0.4, 0.5],
            capacity_down=[0.5, 0.4, 0.5],
            approach="oemof",
            flex_share_up=1,
            flex_share_down=1,
            shift_interval=2,
            cost_dsm_down_shift=2,
            shed_eligibility=False,
            investment=solph.Investment(
                ep_cost=100, existing=50, minimum=33, maximum=100
            ),
        )
        self.compare_lp_files("dsm_module_oemof_invest.lp")

    def test_nonconvex_investment_storage_without_offset(self):
        """All invest variables are coupled. The invest variables of the Flows
        will be created during the initialisation of the storage e.g. battery
        """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storage_non_convex",
            inputs={bel: solph.flows.Flow(variable_costs=56)},
            outputs={bel: solph.flows.Flow(variable_costs=24)},
            nominal_storage_capacity=None,
            loss_rate=0.13,
            max_storage_level=0.9,
            min_storage_level=0.1,
            invest_relation_input_capacity=1 / 6,
            invest_relation_output_capacity=1 / 6,
            inflow_conversion_factor=0.97,
            outflow_conversion_factor=0.86,
            investment=solph.Investment(
                ep_costs=141, maximum=244, minimum=12, nonconvex=True
            ),
        )

        self.compare_lp_files("storage_invest_without_offset.lp")

    def test_nonconvex_investment_storage_with_offset(self):
        """All invest variables are coupled. The invest variables of the Flows
        will be created during the initialisation of the storage e.g. battery
        """
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.GenericStorage(
            label="storagenon_convex",
            inputs={bel: solph.flows.Flow(variable_costs=56)},
            outputs={bel: solph.flows.Flow(variable_costs=24)},
            nominal_storage_capacity=None,
            loss_rate=0.13,
            max_storage_level=0.9,
            min_storage_level=0.1,
            invest_relation_input_capacity=1 / 6,
            invest_relation_output_capacity=1 / 6,
            inflow_conversion_factor=0.97,
            outflow_conversion_factor=0.86,
            investment=solph.Investment(
                ep_costs=145,
                minimum=19,
                offset=5,
                nonconvex=True,
                maximum=1454,
            ),
        )

        self.compare_lp_files("storage_invest_with_offset.lp")

    def test_nonconvex_invest_storage_all_nonconvex(self):
        """All invest variables are free and nonconvex."""
        b1 = solph.buses.Bus(label="bus1")

        solph.components.GenericStorage(
            label="storage_all_nonconvex",
            inputs={
                b1: solph.flows.Flow(
                    investment=solph.Investment(
                        nonconvex=True,
                        minimum=5,
                        offset=10,
                        maximum=30,
                        ep_costs=10,
                    )
                )
            },
            outputs={
                b1: solph.flows.Flow(
                    investment=solph.Investment(
                        nonconvex=True,
                        minimum=8,
                        offset=15,
                        ep_costs=10,
                        maximum=20,
                    )
                )
            },
            investment=solph.Investment(
                nonconvex=True, ep_costs=20, offset=30, minimum=20, maximum=100
            ),
        )

        self.compare_lp_files("storage_invest_all_nonconvex.lp")

    def test_nonconvex_invest_sink_without_offset(self):
        """Non convex invest flow without offset, with minimum."""
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Sink(
            label="sink_nonconvex_invest",
            inputs={
                bel: solph.flows.Flow(
                    full_load_time_max=2.3,
                    variable_costs=25,
                    max=0.8,
                    investment=solph.Investment(
                        ep_costs=500, minimum=15, nonconvex=True, maximum=172
                    ),
                )
            },
        )
        self.compare_lp_files("flow_invest_without_offset.lp")

    def test_nonconvex_invest_source_with_offset(self):
        """Non convex invest flow with offset, with minimum."""
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="source_nonconvex_invest",
            inputs={
                bel: solph.flows.Flow(
                    full_load_time_max=2.3,
                    variable_costs=25,
                    max=0.8,
                    investment=solph.Investment(
                        ep_costs=500,
                        minimum=15,
                        maximum=20,
                        offset=34,
                        nonconvex=True,
                    ),
                )
            },
        )
        self.compare_lp_files("flow_invest_with_offset.lp")

    def test_nonconvex_invest_source_with_offset_no_minimum(self):
        """Non convex invest flow with offset, without minimum."""
        bel = solph.buses.Bus(label="electricityBus")

        solph.components.Source(
            label="source_nonconvex_invest",
            inputs={
                bel: solph.flows.Flow(
                    full_load_time_max=2.3,
                    variable_costs=25,
                    max=0.8,
                    investment=solph.Investment(
                        ep_costs=500, maximum=1234, offset=34, nonconvex=True
                    ),
                )
            },
        )
        self.compare_lp_files("flow_invest_with_offset_no_minimum.lp")

    def test_nonequidistant_storage(self):
        """Constraint test of an energysystem with nonequidistant timeindex"""
        idxh = pd.date_range("1/1/2017", periods=3, freq="H")
        idx2h = pd.date_range("1/1/2017 03:00:00", periods=2, freq="2H")
        idx30m = pd.date_range("1/1/2017 07:00:00", periods=4, freq="30min")
        timeindex = idxh.append([idx2h, idx30m])
        es = solph.EnergySystem(timeindex=timeindex, infer_last_interval=False)
        b_gas = solph.Bus(label="gas")
        b_th = solph.Bus(label="heat")
        boiler = solph.components.Transformer(
            label="boiler",
            inputs={b_gas: solph.Flow(variable_costs=100)},
            outputs={b_th: solph.Flow(nominal_value=200)},
        )
        storage = solph.components.GenericStorage(
            label="storage",
            inputs={b_th: solph.Flow(nominal_value=100, variable_costs=56)},
            outputs={b_th: solph.Flow(nominal_value=100, variable_costs=24)},
            nominal_storage_capacity=300,
            loss_rate=0.1,
            initial_storage_level=1,
        )
        es.add(b_gas, b_th, boiler, storage)
        om = solph.Model(es)
        self.compare_lp_files("nonequidistant_timeindex.lp", my_om=om)
