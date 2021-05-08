# -*- coding: utf-8 -*-

"""Groupings needed on an energy system for it to work with solph.

If you want to use solph on an energy system, you need to create it with these
groupings specified like this:

    .. code-block: python

    from oemof.network import EnergySystem
    import solph

    energy_system = EnergySystem(groupings=solph.GROUPINGS)

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Stephan Günther
SPDX-FileCopyrightText: Johannes Kochems (jokochems)

SPDX-License-Identifier: MIT

"""

from oemof.network import groupings as groupings

from oemof.solph import blocks


def constraint_grouping(node, fallback=lambda *xs, **ks: None):
    """Grouping function for constraints.

    This function can be passed in a list to :attr:`groupings` of
    :class:`oemof.solph.network.EnergySystem`.

    Parameters
    ----------
    node : :class:`Node <oemof.network.Node`
        The node for which the figure out a constraint group.
    fallback : callable, optional
        A function of one argument. If `node` doesn't have a `constraint_group`
        attribute, this is used to group the node instead. Defaults to not
        group the node at all.
    """
    # TODO: Refactor this for looser coupling between modules.
    # This code causes an unwanted tight coupling between the `groupings` and
    # `network` modules, resulting in having to do an import at runtime in the
    # init method of solph's `EnergySystem`. A better way would be to add a
    # method (maybe `constraints`, `constraint_group`, `constraint_type` or
    # something like that) to solph's node hierarchy, which gets overridden in
    # each subclass to return the appropriate value. Then we can just call the
    # method here.
    # This even gives other users/us the ability to customize/extend how
    # constraints are grouped by overriding the method in future subclasses.

    cg = getattr(node, "constraint_group", fallback)
    return cg()


standard_flow_grouping = groupings.FlowsWithNodes(constant_key=blocks.Flow)


def _investment_grouping(stf):
    if hasattr(stf[2], "investment"):
        if stf[2].investment is not None:
            return True
    else:
        return False


investment_flow_grouping = groupings.FlowsWithNodes(
    constant_key=blocks.InvestmentFlow,
    # stf: a tuple consisting of (source, target, flow), so stf[2] is the flow.
    filter=_investment_grouping,
)


def _multiperiod_grouping(stf):
    if hasattr(stf[2], "multiperiod"):
        if stf[2].multiperiod is not None:
            return True
    else:
        return False


multiperiod_flow_grouping = groupings.FlowsWithNodes(
    constant_key=blocks.MultiPeriodFlow,
    # stf: a tuple consisting of (source, target, flow), so stf[2] is the flow.
    filter=_multiperiod_grouping)


def _multiperiodinvestment_grouping(stf):
    if hasattr(stf[2], "multiperiodinvestment"):
        if stf[2].multiperiodinvestment is not None:
            return True
    else:
        return False


multiperiodinvestment_flow_grouping = groupings.FlowsWithNodes(
    constant_key=blocks.MultiPeriodInvestmentFlow,
    # stf: a tuple consisting of (source, target, flow), so stf[2] is the flow.
    filter=_multiperiodinvestment_grouping)


def _nonconvex_grouping(stf):
    if hasattr(stf[2], "nonconvex"):
        if stf[2].nonconvex is not None:
            return True
    else:
        return False


nonconvex_flow_grouping = groupings.FlowsWithNodes(
    constant_key=blocks.NonConvexFlow, filter=_nonconvex_grouping
)


GROUPINGS = [
    constraint_grouping,
    investment_flow_grouping,
    multiperiod_flow_grouping,
    multiperiodinvestment_flow_grouping,
    standard_flow_grouping,
    nonconvex_flow_grouping,
]
