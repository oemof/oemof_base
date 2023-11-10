# -*- coding: utf-8 -*-
"""
Example that illustrates how to use component `MultiInputMultiOutputConverter`.

SPDX-License-Identifier: MIT
"""

import pandas as pd

from oemof.solph import EnergySystem
from oemof.solph import Model
from oemof.solph import processing
from oemof.solph.buses import Bus
from oemof.solph.components import Sink
from oemof.solph.components import Source
from oemof.solph.components.experimental import MultiInputMultiOutputConverter
from oemof.solph.flows import Flow


def test_mimo_converter():

    idx = pd.date_range("1/1/2017", periods=2, freq="H")
    es = EnergySystem(timeindex=idx, infer_last_interval=True)

    # resources
    b_gas = Bus(label="gas")
    es.add(b_gas)
    es.add(Source(label="gas_station", outputs={b_gas: Flow(fix=[120, 0], nominal_value=1, variable_costs=20)}))

    b_hydro = Bus(label="hydro")
    es.add(b_hydro)
    es.add(Source(label="hydro_station", outputs={b_hydro: Flow(fix=[0, 130], nominal_value=1, variable_costs=20)}))

    b_electricity = Bus(label="electricity")
    es.add(b_electricity)
    es.add(
        Sink(
            label="demand",
            inputs={b_electricity: Flow(fix=[100, 100], nominal_value=1)},
        )
    )

    es.add(
        MultiInputMultiOutputConverter(
            label="mimo",
            inputs={"in": {b_gas: Flow(), b_hydro: Flow()}},
            outputs={b_electricity: Flow()},
            conversion_factors={b_gas: 1.2, b_hydro: 1.3}
        )
    )

    # create an optimization problem and solve it
    om = Model(es)

    # solve model
    om.solve(solver="cbc")

    # create result object
    results = processing.convert_keys_to_strings(processing.results(om))
    print(results)
