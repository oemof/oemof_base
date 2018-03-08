# -*- coding: utf-8 -*-

"""Modules for providing a convenient data structure for solph results.

Information about the possible usage is provided within the examples.

This file is part of project oemof (github.com/oemof/oemof). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location oemof/oemof/outputlib/processing.py

SPDX-License-Identifier: GPL-3.0-or-later
"""

import pandas as pd
from oemof.network import Node
from oemof.tools.helpers import flatten
from itertools import groupby
from pyomo.core.base.var import Var


def get_tuple(x):
    """
    Get oemof tuple within iterable or create it.

    Tuples from Pyomo are of type `(n, n, int)`, `(n, n)` and `(n, int)`.
    For single nodes `n` a tuple with one object `(n,)` is created.
    """
    for i in x:
        if isinstance(i, tuple):
            return i
        elif issubclass(type(i), Node):
            return i,
        else:
            pass


def get_timestep(x):
    """
    Get the timestep from oemof tuples.

    The timestep from tuples `(n, n, int)`, `(n, n)`, `(n, int)` and (n,)
    is fetched as the last element. For time-independent data (scalars)
    zero ist returned.
    """
    if all(issubclass(type(n), Node) for n in x):
        return 0
    else:
        return x[-1]


def remove_timestep(x):
    """
    Remove the timestep from oemof tuples.

    The timestep is removed from tuples of type `(n, n, int)` and `(n, int)`.
    """
    if all(issubclass(type(n), Node) for n in x):
        return x
    else:
        return x[:-1]


def create_dataframe(om):
    """
    Create a result dataframe with all optimization data.

    Results from Pyomo are written into pandas DataFrame where separate columns
    are created for the variable index e.g. for tuples of the flows and
    components or the timesteps.
    """
    # get all pyomo variables including their block
    block_vars = []
    for bv in om.component_data_objects(Var):
        block_vars.append(bv.parent_component())
    block_vars = list(set(block_vars))

    # write them into a dict with tuples as keys
    var_dict = {(str(bv).split('.')[0], str(bv).split('.')[-1], i): bv[i].value
                for bv in block_vars for i in getattr(bv, '_index')}

    # use this to create a pandas dataframe
    df = pd.DataFrame(list(var_dict.items()), columns=['pyomo_tuple', 'value'])
    df['variable_name'] = df['pyomo_tuple'].str[1]

    # adapt the dataframe by separating tuple data into columns depending
    # on which dimension the variable/parameter has (scalar/sequence).
    # columns for the oemof tuple and timestep are created
    df['oemof_tuple'] = df['pyomo_tuple'].map(get_tuple)
    df['timestep'] = df['oemof_tuple'].map(get_timestep)
    df['oemof_tuple'] = df['oemof_tuple'].map(remove_timestep)

    # order the data by oemof tuple and timestep
    df = df.sort_values(['oemof_tuple', 'timestep'], ascending=[True, True])

    # drop empty decision variables
    df = df.dropna(subset=['value'])

    return df


def results(om):
    """
    Create a result dictionary from the result DataFrame.

    Results from Pyomo are written into a dictionary of pandas objects where
    a Series holds all scalar values and a dataframe all sequences for nodes
    and flows.
    The dictionary is keyed by the nodes e.g. `results[idx]['scalars']`
    and flows e.g. `results[n, n]['sequences']`.
    """
    df = create_dataframe(om)

    # create a dict of dataframes keyed by oemof tuples
    df_dict = {k if len(k) > 1 else (k[0], None):
               v[['timestep', 'variable_name', 'value']]
               for k, v in df.groupby('oemof_tuple')}

    # create final result dictionary by splitting up the dataframes in the
    # dataframe dict into a series for scalar data and dataframe for sequences
    result = {}
    for k in df_dict:
        df_dict[k].set_index('timestep', inplace=True)
        df_dict[k] = df_dict[k].pivot(columns='variable_name', values='value')
        df_dict[k].index = om.timeindex
        try:
            condition = df_dict[k].isnull().any()
            scalars = df_dict[k].loc[:, condition].dropna().iloc[0]
            sequences = df_dict[k].loc[:, ~condition]
            result[k] = {'scalars': scalars, 'sequences': sequences}
        except IndexError:
            error_message = ('Cannot access index on result data. ' +
                             'Did the optimization terminate' +
                             ' without errors?')
            raise IndexError(error_message)

    # add dual variables for bus constraints
    if hasattr(om, 'dual'):
        grouped = groupby(sorted(om.Bus.balance.iterkeys()), lambda p: p[0])
        for bus, timesteps in grouped:
            duals = [om.dual[om.Bus.balance[bus, t]] for _, t in timesteps]
            df = pd.DataFrame({'duals': duals}, index=om.es.timeindex)
            if (bus, None) not in result.keys():
                result[(bus, None)] = {
                    'sequences': df, 'scalars': pd.Series()}
            else:
                result[(bus, None)]['sequences']['duals'] = duals

    return result


def convert_keys_to_strings(results):
    """
    Convert the dictionary keys to strings.

    All (tuple) keys of the result object e.g. results[(pp1, bus1)] are
    converted into strings that represent the object labels
    e.g. results[('pp1','bus1')].
    """
    converted = {
        tuple([str(e) for e in k]) if isinstance(k, tuple) else str(k): v
        for k, v in results.items()
    }
    return converted


def meta_results(om, undefined=False):
    """
    Fetch some meta data from the Solver. Feel free to add more keys.

    Valid keys of the resulting dictionary are: 'objective', 'problem',
    'solver'.

    om : oemof.solph.Model
        A solved Model.
    undefined : bool
        By default (False) only defined keys can be found in the dictionary.
        Set to True to get also the undefined keys.

    Returns
    -------
    dict
    """
    meta_res = {'objective': om.objective()}

    for k1 in ['Problem', 'Solver']:
        k1 = k1.lower()
        meta_res[k1] = {}
        for k2, v2 in om.results[k1][0].items():
            try:
                if str(om.results[k1][0][k2]) == '<undefined>':
                    if undefined:
                        meta_res[k1][k2] = str(
                            om.results[k1][0][k2])
                else:
                    meta_res[k1][k2] = om.results[k1][0][k2]
            except TypeError:
                if undefined:
                    msg = "Cannot fetch meta results of type {0}"
                    meta_res[k1][k2] = msg.format(
                        type(om.results[k1][0][k2]))

    return meta_res


def __separate_attrs(system, get_flows=False, exclude_none=True):
    def detect_scalars_and_sequences(com):
        com_data = {'scalars': {}, 'sequences': {}}

        exclusions = ('__', '_', 'registry', 'inputs', 'outputs')
        attrs = [i for i in dir(com)
                 if not (callable(i) or i.startswith(exclusions))]

        for a in attrs:
            attr_value = getattr(com, a)

            # Iterate trough investment and add scalars and sequences with
            # "investment" prefix to component data:
            if attr_value.__class__.__name__ == 'Investment':
                invest_data = detect_scalars_and_sequences(attr_value)
                com_data['scalars'].update(
                    {
                        'investment_' + str(k): v
                        for k, v in invest_data['scalars'].items()
                     }
                )
                com_data['sequences'].update(
                    {
                        'investment_' + str(k): v
                        for k, v in invest_data['sequences'].items()
                    }
                )
                continue

            if isinstance(attr_value, str):
                com_data['scalars'][a] = attr_value
                continue

            # check if attribute is iterable
            # see: https://stackoverflow.com/questions/1952464/
            # in-python-how-do-i-determine-if-an-object-is-iterable
            try:
                _ = (e for e in attr_value)
                com_data['sequences'][a] = attr_value
            except TypeError:
                com_data['scalars'][a] = attr_value

        com_data['sequences'] = flatten(com_data['sequences'])
        move_undetected_scalars(com_data)
        if exclude_none:
            remove_nones(com_data)

        return com_data

    def move_undetected_scalars(com):
        for key, value in list(com['sequences'].items()):
            if isinstance(value, str):
                com['scalars'][key] = value
                del com['sequences'][key]
                continue
            try:
                _ = (e for e in value)
            except TypeError:
                com['scalars'][key] = value
                del com['sequences'][key]
            else:
                try:
                    if not value.default_changed:
                        com['scalars'][key] = value.default
                        del com['sequences'][key]
                except AttributeError:
                    pass

    def remove_nones(com):
        for key, value in list(com['scalars'].items()):
            if value is None:
                del com['scalars'][key]
        for key, value in list(com['sequences'].items()):
            if (
                    len(value) == 0 or
                    value[0] is None
            ):
                del com['sequences'][key]
    """
    Create a dictionary with flow scalars and series.

    The dictionary is structured with flows as tuples and nested dictionaries
    holding the scalars and series e.g.
    {(node1, node2): {'scalars': {'attr1': scalar, 'attr2': 'text'},
    'sequences': {'attr1': iterable, 'attr2': iterable}}}

    om : A solved oemof.solph.Model.

    Returns
    -------
    dict
    """
    # Check if system is es or om:
    if system.__class__.__name__ == 'EnergySystem':
        components = system.flows() if get_flows else system.nodes
    else:
        components = system.flows if get_flows else system.es.nodes

    data = {}
    for com_key in components:
        component = components[com_key] if get_flows else com_key
        component_data = detect_scalars_and_sequences(component)
        key = com_key if get_flows else (com_key, None)
        data[key] = component_data
    return data


def param_results(system, exclude_none=True, keys_as_str=False):
    """
    Create a result dictionary containing node parameters.

    Results are written into a dictionary of pandas objects where
    a Series holds all scalar values and a dataframe all sequences for nodes
    and flows.
    The dictionary is keyed by the nodes e.g.
    `results['nodes'][idx]['scalars']`
    and flows e.g. `results['flows'][(n,n)]['sequences']`.

    Parameters
    ----------
    system: Model or EnergySystem
    exclude_none: bool
        If True, all scalars and sequences containing None values are excluded
    keys_as_str: bool
        If True, nodes are stored as strings

    Returns
    -------
    dict: Parameters for all nodes and flows
    """

    flow_data = __separate_attrs(system, True, exclude_none)
    node_data = __separate_attrs(system, False, exclude_none)

    flow_data.update(node_data)
    return convert_keys_to_strings(flow_data) if keys_as_str else flow_data
