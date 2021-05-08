# -*- coding: utf-8 -*-

"""Modules for providing convenient views for solph results.

Information about the possible usage is provided within the examples.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Stephan Günther
SPDX-FileCopyrightText: henhuy
SPDX-FileCopyrightText: Johannes Kochems (jokochems)

SPDX-License-Identifier: MIT

"""
import logging
from collections import OrderedDict
from enum import Enum

import pandas as pd

from oemof.solph.processing import convert_keys_to_strings

NONE_REPLACEMENT_STR = "_NONE_"


def node(results, node, multiindex=False, keep_none_type=False):
    """
    Obtain results for a single node e.g. a Bus or Component.

    Either a node or its label string can be passed.
    Results are written into a dictionary which is keyed by 'scalars'
    (resp. 'periods_scalars' for a MultiPeriodModel) and
    'sequences' holding respective data in a pandas Series (resp. DataFrame)
    and DataFrame.
    """

    def replace_none(col_list, reverse=False):
        replacement = (
            (None, NONE_REPLACEMENT_STR)
            if reverse
            else (NONE_REPLACEMENT_STR, None)
        )
        changed_col_list = [
            (
                (
                    replacement[0] if n1 is replacement[1] else n1,
                    replacement[0] if n2 is replacement[1] else n2,
                ),
                f,
            )
            for (n1, n2), f in col_list
        ]
        return changed_col_list

    # convert to keys if only a string is passed
    if type(node) is str:
        results = convert_keys_to_strings(results, keep_none_type)

    filtered = {}

    # create a series with tuples as index labels for scalars
    scalars = {}
    scalars_col = 'scalars'
    # Check for MultiPeriodModel (different naming)
    if 'period_scalars' in list(list(results.values())[0].keys()):
        scalars_col = 'period_scalars'

    scalars = {
        k: v[scalars_col] for k, v in results.items()
        if node in k and not v[scalars_col].empty
    }
    if scalars:
        # aggregate data
        filtered["scalars"] = pd.concat(scalars.values(), axis=0)
        # assign index values
        idx = {
            k: [c for c in v[scalars_col].index]
            for k, v in results.items()
            if node in k and not v[scalars_col].empty
        }
        idx = [tuple((k, m) for m in v) for k, v in idx.items()]
        idx = [i for sublist in idx for i in sublist]
        filtered["scalars"].index = idx

        # Sort index
        # (if Nones are present, they have to be replaced while sorting)
        if keep_none_type:
            filtered["scalars"].index = replace_none(
                filtered["scalars"].index.tolist()
            )
        filtered["scalars"].sort_index(axis=0, inplace=True)
        if keep_none_type:
            filtered["scalars"].index = replace_none(
                filtered["scalars"].index.tolist(), True
            )

        if multiindex:
            idx = pd.MultiIndex.from_tuples(
                [
                    tuple([row[0][0], row[0][1], row[1]])
                    for row in filtered["scalars"].index
                ]
            )
            idx.set_names(["from", "to", "type"], inplace=True)
            filtered["scalars"].index = idx

    # create a dataframe with tuples as column labels for sequences
    sequences = {
        k: v["sequences"]
        for k, v in results.items()
        if node in k and not v["sequences"].empty
    }
    if sequences:
        # aggregate data
        filtered["sequences"] = pd.concat(sequences.values(), axis=1)
        # assign column names
        cols = {
            k: [c for c in v["sequences"].columns]
            for k, v in results.items()
            if node in k and not v["sequences"].empty
        }
        cols = [tuple((k, m) for m in v) for k, v in cols.items()]
        cols = [c for sublist in cols for c in sublist]
        filtered["sequences"].columns = replace_none(cols)
        filtered["sequences"].sort_index(axis=1, inplace=True)
        filtered["sequences"].columns = replace_none(
            filtered["sequences"].columns, True
        )

        if multiindex:
            idx = pd.MultiIndex.from_tuples(
                [
                    tuple([col[0][0], col[0][1], col[1]])
                    for col in filtered["sequences"].columns
                ]
            )
            idx.set_names(["from", "to", "type"], inplace=True)
            filtered["sequences"].columns = idx

    return filtered


class NodeOption(str, Enum):
    All = "all"
    HasOutputs = "has_outputs"
    HasInputs = "has_inputs"
    HasOnlyOutputs = "has_only_outputs"
    HasOnlyInputs = "has_only_inputs"


def filter_nodes(results, option=NodeOption.All, exclude_busses=False):
    """Get set of nodes from results-dict for given node option.

    This function filters nodes from results for special needs. At the moment,
    the following options are available:

        * :attr:`NodeOption.All`: `'all'`: Returns all nodes
        * :attr:`NodeOption.HasOutputs`: `'has_outputs'`:
            Returns nodes with an output flow (eg. Transformer, Source)
        * :attr:`NodeOption.HasInputs`: `'has_inputs'`:
            Returns nodes with an input flow (eg. Transformer, Sink)
        * :attr:`NodeOption.HasOnlyOutputs`: `'has_only_outputs'`:
            Returns nodes having only output flows (eg. Source)
        * :attr:`NodeOption.HasOnlyInputs`: `'has_only_inputs'`:
            Returns nodes having only input flows (eg. Sink)

    Additionally, busses can be excluded by setting `exclude_busses` to
    `True`.

    Parameters
    ----------
    results: dict
    option: NodeOption
    exclude_busses: bool
        If set, all bus nodes are excluded from the resulting node set.

    Returns
    -------
    :obj:`set`
        A set of Nodes.
    """
    node_from, node_to = map(lambda x: set(x) - {None}, zip(*results))
    if option == NodeOption.All:
        nodes = node_from.union(node_to)
    elif option == NodeOption.HasOutputs:
        nodes = node_from
    elif option == NodeOption.HasInputs:
        nodes = node_to
    elif option == NodeOption.HasOnlyOutputs:
        nodes = node_from - node_to
    elif option == NodeOption.HasOnlyInputs:
        nodes = node_to - node_from
    else:
        raise ValueError('Invalid node option "' + str(option) + '"')

    if exclude_busses:
        return {n for n in nodes if not n.__class__.__name__ == "Bus"}
    else:
        return nodes


def get_node_by_name(results, *names):
    """
    Searches results for nodes

    Names are looked up in nodes from results and either returned single node
    (in case only one name is given) or as list of nodes. If name is not found,
    None is returned.
    """
    nodes = filter_nodes(results)
    if len(names) == 1:
        return next(filter(lambda x: str(x) == names[0], nodes), None)
    else:
        node_names = {str(n): n for n in nodes}
        return [node_names.get(n, None) for n in names]


def node_weight_by_type(results, node_type):
    """
    Extracts node weights (if exist) of all components of the specified
    `node_type`.

    Node weight are endogenous optimzation variables associated with the node
    and not the edge between two node, foxample the variable representing the
    storage level.

    Parameters
    ----------
    results: dict
        A result dictionary from a solved oemof.solph.Model object
    node_type: oemof.solph class
        Specifies the type for which node weights should be collected

    Example
    --------
    from oemof.outputlib import views

    # solve oemof model 'm'
    # Then collect node weights
    views.node_weight_by_type(m.results(), node_type=solph.GenericStorage)
    """

    group = {
        k: v["sequences"]
        for k, v in results.items()
        if isinstance(k[0], node_type) and k[1] is None
    }
    if not group:
        logging.error(
            "No node weights for nodes of type `{}`".format(node_type)
        )
        return None
    else:
        df = convert_to_multiindex(
            group, index_names=["node", "to", "weight_type"], droplevel=[1]
        )
        return df


def node_input_by_type(results, node_type, droplevel=None):
    """Gets all inputs for all nodes of the type `node_type` and returns
    a dataframe.

    Parameters
    ----------
    results: dict
        A result dictionary from a solved oemof.solph.Model object
    node_type: oemof.solph class
        Specifies the type of the node for that inputs are selected
    droplevel: list

    Notes
    -----
    from oemof import solph
    from oemof.outputlib import views

    # solve oemof solph model 'm'
    # Then collect node weights
    views.node_input_by_type(m.results(), node_type=solph.Sink)
    """
    if droplevel is None:
        droplevel = []

    group = {
        k: v["sequences"]
        for k, v in results.items()
        if isinstance(k[1], node_type) and k[0] is not None
    }

    if not group:
        logging.info("No nodes of type `{}`".format(node_type))
        return None
    else:
        df = convert_to_multiindex(group, droplevel=droplevel)
        return df


def node_output_by_type(results, node_type, droplevel=None):
    """Gets all outputs for all nodes of the type `node_type` and returns
    a dataframe.

    Parameters
    ----------
    results: dict
        A result dictionary from a solved oemof.solph.Model object
    node_type: oemof.solph class
        Specifies the type of the node for that outputs are selected
    droplevel: list

    Notes
    -----
    import oemof.solph as solph
    from oemof.outputlib import views

    # solve oemof solph model 'm'
    # Then collect node weights
    views.node_output_by_type(m.results(), node_type=solph.Transformer)
    """
    if droplevel is None:
        droplevel = []
    group = {
        k: v["sequences"]
        for k, v in results.items()
        if isinstance(k[0], node_type) and k[1] is not None
    }

    if not group:
        logging.info("No nodes of type `{}`".format(node_type))
        return None
    else:
        df = convert_to_multiindex(group, droplevel=droplevel)
        return df


def net_storage_flow(results, node_type):
    """Calculates the net storage flow for storage models that have one
    input edge and one output edge both with flows within the domain of
    non-negative reals.

    Parameters
    ----------
    results: dict
        A result dictionary from a solved oemof.solph.Model object
    node_type: oemof.solph class
        Specifies the type for which (storage) type net flows are calculated

    Returns
    -------
    pandas.DataFrame object with multiindex colums. Names of levels of columns
    are: from, to, net_flow.

    Examples
    --------
    import oemof.solph as solph
    from oemof.outputlib import views

    # solve oemof solph model 'm'
    # Then collect node weights
    views.net_storage_flow(m.results(), node_type=solph.GenericStorage)
    """

    group = {
        k: v["sequences"]
        for k, v in results.items()
        if isinstance(k[0], node_type) or isinstance(k[1], node_type)
    }

    if not group:
        logging.info("No nodes of type `{}`".format(node_type))
        return None

    df = convert_to_multiindex(group)

    if "storage_content" not in df.columns.get_level_values(2).unique():
        return None

    x = df.xs("storage_content", axis=1, level=2).columns.values
    labels = [s for s, t in x]

    dataframes = []

    for lb in labels:
        subset = df.groupby(
            lambda x1: (
                lambda fr, to, ty: "output"
                if (fr == lb and ty == "flow")
                else "input"
                if (to == lb and ty == "flow")
                else "level"
                if (fr == lb and ty != "flow")
                else None
            )(*x1),
            axis=1,
        ).sum()

        subset["net_flow"] = subset["output"] - subset["input"]

        subset.columns = pd.MultiIndex.from_product(
            [[lb], [o for o in lb.outputs], subset.columns]
        )

        dataframes.append(
            subset.loc[:, (slice(None), slice(None), "net_flow")]
        )

    return pd.concat(dataframes, axis=1)


def convert_to_multiindex(group, index_names=None, droplevel=None):
    """Convert dict to pandas DataFrame with multiindex

    Parameters
    ----------
    group: dict
        Sequences of the oemof.solph.Model.results dictionary
    index_names: arraylike
        Array with names of the MultiIndex
    droplevel: arraylike
        List containing levels to be dropped from the dataframe
    """
    if index_names is None:
        index_names = ["from", "to", "type"]
    if droplevel is None:
        droplevel = []

    sorted_group = OrderedDict((k, group[k]) for k in sorted(group))
    df = pd.concat(sorted_group.values(), axis=1)

    cols = OrderedDict((k, v.columns) for k, v in sorted_group.items())
    cols = [tuple((k, m) for m in v) for k, v in cols.items()]
    cols = [c for sublist in cols for c in sublist]
    idx = pd.MultiIndex.from_tuples(
        [tuple([col[0][0], col[0][1], col[1]]) for col in cols]
    )
    idx.set_names(index_names, inplace=True)
    df.columns = idx
    df.columns = df.columns.droplevel(droplevel)

    return df
