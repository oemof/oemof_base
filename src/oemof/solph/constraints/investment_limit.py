# -*- coding: utf-8 -*-

"""Limits for investments.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: Johannes Röder

SPDX-License-Identifier: MIT

"""

from pyomo import environ as po


def investment_limit(model, keyword=None, limit=None):
    r"""
    Global limit for investment flows weighted by an attribute keyword.

    This constraint is only valid for Flows not for components such as an
    investment storage.

    The attribute named by keyword has to be added to every Investment
    attribute of the flow you want to take into account.
    Total value of keyword attributes after optimization can be retrieved
    calling the :attr:`oemof.solph.Model.invest_limit_${keyword}()`.

    Parameters
    ----------
    model : oemof.solph.Model
        Model to which constraints are added.
    keyword : need to consider (None: ep_costs)
        All flows with Investment attribute containing the keyword will be
        used.
    limit : numeric
        Global limit of keyword attribute for the energy system.

    **Constraint**

    .. math:: \sum_{i}  P_i \cdot w_i \leq limit

    Where :math:`i` being all investments (for keyword=None)
    or being the set of InvestmentFlows considered.

    The symbols used are defined as follows
    (with Variables (V) and Parameters (P)):

    +---------------+---------------------------------------+------+--------------------------------------------------+
    | symbol        | attribute                             | type | explanation                                      |
    +===============+=======================================+======+==================================================+
    | :math:`P_{i}` | :py:obj:`InvestmentFlow.invest[i, o]` | V    | installed capacity of investment flow            |
    +---------------+---------------------------------------+------+--------------------------------------------------+
    | :math:`w_i`   | :py:obj:`keyword`                     | P    | weight given to investment flow named according  |
    |               |                                       |      | to `keyword`, :math:`w_i = 1` if keyword is None |
    +---------------+---------------------------------------+------+--------------------------------------------------+
    | :math:`limit` | :py:obj:`limit`                       | P    | global limit given by keyword `limit`            |
    +---------------+---------------------------------------+------+--------------------------------------------------+

    Note
    ----
    The Investment attribute of the considered (Investment-)flows requires an
    attribute named like keyword!

    Examples
    --------
    >>> import pandas as pd
    >>> from oemof import solph
    >>> date_time_index = pd.date_range('1/1/2020', periods=5, freq='H')
    >>> es = solph.EnergySystem(timeindex=date_time_index)
    >>> bus = solph.Bus(label='bus_1')
    >>> sink = solph.Sink(label="sink", inputs={bus:
    ...     solph.Flow(nominal_value=10, fix=[10, 20, 30, 40, 50])})
    >>> src1 = solph.Source(label='source_0', outputs={bus: solph.Flow(
    ...     investment=solph.Investment(ep_costs=50, space=4))})
    >>> src2 = solph.Source(label='source_1', outputs={bus: solph.Flow(
    ...     investment=solph.Investment(ep_costs=100, space=1))})
    >>> es.add(bus, sink, src1, src2)
    >>> model = solph.Model(es)
    >>> model = solph.constraints.investment_limit(model, "space", limit=1500)
    >>> a = model.solve(solver="cbc")
    >>> int(round(model.invest_limit_space()))
    1500
    """  # noqa: E501
    if keyword is None:
        def investment_rule(m):
            expr = 0

            if hasattr(m, "InvestmentFlow"):
                expr += m.InvestmentFlow.investment_costs

            if hasattr(m, "GenericInvestmentStorageBlock"):
                expr += m.GenericInvestmentStorageBlock.investment_costs
            return expr <= limit

        model.investment_limit = po.Constraint(rule=investment_rule)

    else:
        invest_flows = {}

        for (i, o) in model.flows:
            if keyword in model.flows[i, o].investment.other_needs:
                invest_flows[(i, o)] = model.flows[i, o].investment

        limit_name = "invest_limit_" + keyword

        setattr(
            model,
            limit_name,
            po.Expression(
                expr=sum(
                    model.InvestmentFlow.invest[inflow, outflow]
                    * invest_flows[inflow, outflow].other_needs[keyword]
                    for (inflow, outflow) in invest_flows
                )
            ),
        )

        setattr(
            model,
            limit_name + "_constraint",
            po.Constraint(expr=(getattr(model, limit_name) <= limit)),
        )

    return model
