# -*- coding: utf-8 -*-

"""Modules for providing a convenient data structure
 for solph cost  and results.

Information about the possible usage is provided within the examples.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Stephan Günther
SPDX-FileCopyrightText: henhuy
SPDX-FileCopyrightText: Johannes Kochems
SPDX-FileCopyrightText: Patrik Schönfeldt <patrik.schoenfeldt@dlr.de>

SPDX-License-Identifier: MIT

"""

import re

import numpy as np
import pandas as pd


def get_set_costs_from_lpfile(filename, model, timeindex=[]):
    """returns costs dependent and independent of time based on lp file

    Parameters
    ----------
    filename: path
        file direction of lp file of model
    model : solph.Model
        solved oemof model
    timeindex: datetime
        regarded timeindex, otherwise timeindex get from the model

    Returns
    -------
    Dataframes:
        time_depenent_costs, time_independent_costs
    """

    with open(filename) as f:
        contents = f.read()
    rows = (
        contents.split("objective:")[1]
        .split("s.t.")[0]
        .replace("+", "")
        .split("\n")
    )

    data_frame = pd.DataFrame(i.split(" ") for i in rows).dropna()
    data_frame.columns = ["cost", "name"]
    data_frame["cost"] = data_frame["cost"].astype("float")

    # calculate time depenedent costs
    # filter time dependent values and drop invest values
    data_frame_time_dependent = data_frame[
        data_frame.name.isin(
            [
                nam
                for nam in data_frame.name
                if re.findall("_+[0-9]+_", nam)
                and not re.findall("invest", nam)
            ]
        )
    ].copy()

    # get the timevalue

    if len(timeindex) > 0:
        tmindex = timeindex

    else:
        tmindex = model.es.timeindex[:-1]
    try:
        data_frame_time_dependent["time"] = [
            tmindex[
                int(
                    re.search(r"(\(.+\))", i)
                    .group()
                    .split(")")[0]
                    .split("_")[-1]
                )
            ]
            for i in data_frame_time_dependent.name
        ]
    except ValueError:
        error_message = (
            "Timeindex has to be given as parameter "
            + "or has to be set within the model"
        )
        raise ValueError(error_message)

    flow_costs = data_frame_time_dependent[
        data_frame_time_dependent.name.str.match("flow")
    ].copy()
    flow_costs["unique_name"] = [
        re.sub(r"_\d+_\d+\)", "", re.search(r"\(.+\)", i).group()).replace(
            "(", ""
        )
        for i in flow_costs.name
    ]

    non_flow_costs = data_frame_time_dependent[
        data_frame_time_dependent.name.str.match(r"^((?!flow).)*$")
    ].copy()
    non_flow_costs["unique_name"] = [
        re.sub(r"_\d+_\d+\)", "", name.split("(")[1])
        + "_"
        + name.split("(")[0].split("_", 1)[1]
        for name in non_flow_costs.name
    ]

    data_time_dependent = pd.concat([non_flow_costs, flow_costs])

    pivot_data = pd.pivot(
        data_time_dependent,
        index=["time"],
        columns="unique_name",
        values="cost",
    )

    time_dependent_costs_all_pivot = pivot_data.replace(np.nan, 0)

    # calculation time independent costs

    # remove time independent  data

    time_independent_costs = data_frame[
        data_frame.name.isin(
            [
                nam
                for nam in data_frame.name
                if not re.findall(r"_+[0-9]+_", nam)
            ]
        )
    ].copy()

    # renaming (remove unnecessary strings)
    time_independent_costs.loc[:, "name"] = [
        name.split("_", 1)[1].split("(")[0]
        + "_"
        + name.split("(")[1].split(")")[0]
        for name in time_independent_costs.name
    ]

    # invest costs

    invest_costs = data_frame[
        data_frame.name.isin(
            [nam for nam in data_frame.name if re.findall("invest", nam)]
        )
    ].copy()

    # renaming (remove unnecessary strings)
    invest_costs.loc[:, "name"] = [
        re.sub(r"_\d+\)", "", re.search(r"invest+\(.+\)", i).group()).replace(
            "(", "_"
        )
        for i in invest_costs.name
    ]

    time_independent_costs = pd.concat([time_independent_costs, invest_costs])
    time_independent_costs = time_independent_costs.reindex(
        columns=["cost", "name"]
    )

    # transform to dataframe with name as columns
    trans_tic = time_independent_costs.T
    trans_tic.columns = trans_tic.loc["name"]
    trans_tic = (
        trans_tic.reset_index().rename_axis(None, axis=1).drop("index", axis=1)
    )
    trans_tic = trans_tic.drop([1])
    return time_dependent_costs_all_pivot, trans_tic


def time_dependent_values_as_dataframe(results, timeindex=[]):
    """returns timedependent results as dataframe

    Parameters
    ----------
    results : results
        results from oemof.solph.processing
        method results(remove_last_time_point=True)
        Note: remove_last_time_point must be set to True!
    timeindex: datetime
        add timeindex manually, otherwise timeindex is numerated

    Returns
    -------
    DataFrame
    """

    # get flows of energysystem
    flows = [x for x in results.keys() if x[1] is not None]
    if len(timeindex) > 0:
        tmindex = timeindex
    else:
        tmindex = results[flows[0]]["sequences"].index
    dataframe = {"time": tmindex}
    for flow in flows:
        name = str(flow[0].label + "_" + str(flow[1].label))
        component = results[flow]["sequences"]
        for attribute in component:
            tmp = getattr(component, attribute)
            tmp2 = getattr(tmp, "values")
            dataframe.update({str(name): list(tmp2)})

    # get nodes of energysystem
    nodes = [x for x in results.keys() if x[1] is None]

    for node in nodes:
        name = node[0].label
        component = results[node]["sequences"]
        for attribute in component:
            tmp = getattr(component, attribute)
            tmp2 = getattr(tmp, "values")
            dataframe.update({str(name + "_" + attribute): list(tmp2)})

    dataframe = pd.DataFrame(dataframe)
    dataframe = dataframe.set_index("time")
    return dataframe


def time_independent_values_as_dataframe(results, timeindex=[]):
    """

    get scalar values of nodes as dataframe


    Parameters
    ----------
    oemof_results : results
        results from oemof.solph.processing  method results()

    Returns
    -------
    Dataframe
    """
    nodes = [x for x in results.keys() if x[1] is None]

    data_scalar = {}

    for node in nodes:
        # get the scalars of the component
        scalar = results[node]["scalars"]
        for num, value in enumerate(scalar.axes[0].values):
            data_scalar.update(
                {value + "_" + str(node[0].label): [scalar.T[num]]}
            )

    # get flows of energysystem
    flows = [x for x in results.keys() if x[1] is not None]

    for flow in flows:
        # get the scalars of the component
        scalar = results[flow]["scalars"]
        for num, value in enumerate(scalar.axes[0].values):
            name = (
                str(value)
                + "_"
                + str(flow[0].label)
                + "_"
                + str(flow[1].label)
            )
            data_scalar.update({name: [scalar.T[num]]})

    return pd.DataFrame.from_dict(data_scalar)
