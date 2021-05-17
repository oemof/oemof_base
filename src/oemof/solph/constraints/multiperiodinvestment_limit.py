# -*- coding: utf-8 -*-

"""Limits for investments.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: Johannes Röder
SPDX-FileCopyrightText: Johannes Kochems
SPDX-FileCopyrightText: Johannes Giehl

SPDX-License-Identifier: MIT

"""

from pyomo import environ as po

from oemof.solph.models import MultiPeriodModel


def multiperiodinvestment_limit(model, limit=None):
    r"""Set an absolute limit for the total investment costs of a
    multiperiod investment optimization problem:

    .. math:: \sum_{investment\_costs} \leq limit

    Parameters
    ----------
    model : oemof.solph.Model
        Model to which the constraint is added
    limit : float
        Absolute limit of the investment (i.e. RHS of constraint)
    """

    if not isinstance(model, MultiPeriodModel):
        msg = ("multiperiodinvestment_limit is only applicable\n"
               "for MultiPeriodModels, not standard models.")
        raise ValueError(msg)

    def multiperiodinvestment_rule(m):
        expr = 0

        if hasattr(m, "MultiPeriodInvestmentFlow"):
            expr += m.MultiPeriodInvestmentFlow.investment_costs

        if hasattr(m, "GenericMultiPeriodInvestmentStorageBlock"):
            expr += (
                m.GenericMultiPeriodInvestmentStorageBlock.investment_costs
            )

        if hasattr(m, "SinkDSMOemofMultiPeriodInvestmentBlock"):
            expr += (
                m.SinkDSMOemofMultiPeriodInvestmentBlock.investment_costs
            )

        if hasattr(m, "SinkDSMDIWMultiPeriodInvestmentBlock"):
            expr += (
                m.SinkDSMDIWMultiPeriodInvestmentBlock.investment_costs
            )

        if hasattr(m, "SinkDSMDLRMultiPeriodInvestmentBlock"):
            expr += (
                m.SinkDSMDLRMultiPeriodInvestmentBlock.investment_costs
            )

        return expr <= limit

    model.multiperiodinvestment_limit = po.Constraint(
        rule=multiperiodinvestment_rule)

    return model


def additional_multiperiodinvestment_flow_limit(model, keyword, limit=None):
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
    keyword : attribute to consider
        All flows with Investment attribute containing the keyword will be
        used.
    limit : numeric
        Global limit of keyword attribute for the energy system.

    **Constraint**

    .. math:: \sum_{i \in IF}  P_i \cdot w_i \leq limit

    With `IF` being the set of InvestmentFlows considered for the integral
    limit.

    The symbols used are defined as follows
    (with Variables (V) and Parameters (P)):

    +---------------+---------------------------------------+------+--------------------------------------------------------------+
    | symbol        | attribute                             | type | explanation                                                  |
    +===============+=======================================+======+==============================================================+
    | :math:`P_{i}` | :py:obj:`InvestmentFlow.invest[i, o]` | V    | installed capacity of investment flow                        |
    +---------------+---------------------------------------+------+--------------------------------------------------------------+
    | :math:`w_i`   | :py:obj:`keyword`                     | P    | weight given to investment flow named according to `keyword` |
    +---------------+---------------------------------------+------+--------------------------------------------------------------+
    | :math:`limit` | :py:obj:`limit`                       | P    | global limit given by keyword `limit`                        |
    +---------------+---------------------------------------+------+--------------------------------------------------------------+

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
    >>> model = solph.constraints.additional_investment_flow_limit(
    ...     model, "space", limit=1500)
    >>> a = model.solve(solver="cbc")
    >>> int(round(model.invest_limit_space()))
    1500
    """  # noqa: E501
    if not isinstance(model, MultiPeriodModel):
        msg = ("additional_multiperiodinvestment_limit is only applicable\n"
               "for MultiPeriodModels, not standard models.")
        raise ValueError(msg)

    multiperiodinvest_flows = {}

    for (i, o) in model.flows:
        if hasattr(model.flows[i, o].mutliperiodinvestment, keyword):
            multiperiodinvest_flows[(i, o)] = (
                model.flows[i, o].multiperiodinvestment
            )

    limit_name = "mutliperiodinvest_limit_" + keyword

    setattr(
        model,
        limit_name,
        po.Expression(
            expr=sum(
                model.MultiPeriodInvestmentFlow.invest[inflow, outflow]
                * getattr(multiperiodinvest_flows[inflow, outflow], keyword)
                for (inflow, outflow) in multiperiodinvest_flows
        )
        ),
    )

    setattr(
        model,
        limit_name + "_constraint",
        po.Constraint(expr=(getattr(model, limit_name) <= limit)),
    )

    return model
