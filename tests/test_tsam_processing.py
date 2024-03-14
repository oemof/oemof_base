# -*- coding: utf-8 -*-

import pandas as pd

from oemof.solph import processing


def test_disaggregate_timeindex():
    ti_1 = pd.date_range("2020-01-01", periods=10, freq="H")
    ti_2 = pd.date_range("2030-01-01", periods=20, freq="H")
    ti_3 = pd.date_range("2040-01-01", periods=40, freq="H")
    ti = ti_1.union(ti_2).union(ti_3)

    periods = [ti_1, ti_2, ti_3]
    tsa_parameters = [
        {"timesteps_per_period": 5, "order": [1, 0]},
        {"timesteps_per_period": 5, "order": [1, 0, 0, 1]},
        {"timesteps_per_period": 10, "order": [1, 0, 0, 1]},
    ]

    for p, period_data in enumerate(tsa_parameters):
        if p == 0:
            result_index = processing._disaggregate_tsa_timeindex(
                periods[p], period_data
            )
        else:
            result_index = result_index.union(
                processing._disaggregate_tsa_timeindex(
                    periods[p], period_data
                )
            )

    assert all(result_index == ti)
