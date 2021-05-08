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
            expr += m.GenericMultiPeriodInvestmentStorageBlock.investment_costs

        return expr <= limit

    model.multiperiodinvestment_limit = po.Constraint(
        rule=multiperiodinvestment_rule)

    return model
