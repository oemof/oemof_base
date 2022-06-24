# -*- coding: utf-8 -*-

"""Creating sets, variables, constraints and parts of the objective function
for Flow objects with investment option.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: Birgit Schachler
SPDX-FileCopyrightText: jnnr
SPDX-FileCopyrightText: jmloenneberga

SPDX-License-Identifier: MIT

"""

from pyomo.core import Binary
from pyomo.core import Constraint
from pyomo.core import Expression
from pyomo.core import NonNegativeReals
from pyomo.core import Set
from pyomo.core import Var
from pyomo.core.base.block import SimpleBlock


class InvestmentFlow(SimpleBlock):
    r"""Block for all flows with :attr:`Investment` being not None.

    See :class:`oemof.solph.options.Investment` for all parameters of the
    *Investment* class.

    See :class:`oemof.solph.network.Flow` for all parameters of the *Flow*
    class.

    **Variables**

    All *InvestmentFlow* are indexed by a starting and ending node
    :math:`(i, o)`, which is omitted in the following for the sake
    of convenience. The following variables are created:

    * :math:`P(t)`

        Actual flow value (created in :class:`oemof.solph.models.BaseModel`).

    * :math:`P_{invest}`

        Value of the investment variable, i.e. equivalent to the nominal
        value of the flows after optimization.

    * :math:`b_{invest}`

        Binary variable for the status of the investment, if
        :attr:`nonconvex` is `True`.

    **Constraints**

    Depending on the attributes of the *InvestmentFlow* and *Flow*, different
    constraints are created. The following constraint is created for all
    *InvestmentFlow*:\

            Upper bound for the flow value

        .. math::
            P(t) \le ( P_{invest} + P_{exist} ) \cdot f_{max}(t)

    Depeding on the attribute :attr:`nonconvex`, the constraints for the bounds
    of the decision variable :math:`P_{invest}` are different:\

        * :attr:`nonconvex = False`

        .. math::
            P_{invest, min} \le P_{invest} \le P_{invest, max}

        * :attr:`nonconvex = True`

        .. math::
            &
            P_{invest, min} \cdot b_{invest} \le P_{invest}\\
            &
            P_{invest} \le P_{invest, max} \cdot b_{invest}\\

    For all *InvestmentFlow* (independent of the attribute :attr:`nonconvex`),
    the following additional constraints are created, if the appropriate
    attribute of the *Flow* (see :class:`oemof.solph.network.Flow`) is set:

        * :attr:`fix` is not None

            Actual value constraint for investments with fixed flow values

        .. math::
            P(t) = ( P_{invest} + P_{exist} ) \cdot f_{fix}(t)

        * :attr:`min != 0`

            Lower bound for the flow values

        .. math::
            P(t) \geq ( P_{invest} + P_{exist} ) \cdot f_{min}(t)

        * :attr:`summed_max is not None`

            Upper bound for the sum of all flow values (e.g. maximum full load
            hours)

        .. math::
            \sum_t P(t) \cdot \tau(t) \leq ( P_{invest} + P_{exist} )
            \cdot f_{sum, min}

        * :attr:`summed_min is not None`

            Lower bound for the sum of all flow values (e.g. minimum full load
            hours)

        .. math::
            \sum_t P(t) \cdot \tau(t) \geq ( P_{invest} + P_{exist} )
            \cdot f_{sum, min}


    **Objective function**

    The part of the objective function added by the *InvestmentFlow*
    also depends on whether a convex or nonconvex
    *InvestmentFlow* is selected. The following parts of the objective function
    are created:

        * :attr:`nonconvex = False`

            .. math::
                P_{invest} \cdot c_{invest,var}

        * :attr:`nonconvex = True`

            .. math::
                P_{invest} \cdot c_{invest,var}
                + c_{invest,fix} \cdot b_{invest}\\

    The total value of all costs of all *InvestmentFlow* can be retrieved
    calling :meth:`om.InvestmentFlow.investment_costs.expr()`.

    .. csv-table:: List of Variables (in csv table syntax)
        :header: "symbol", "attribute", "explanation"
        :widths: 1, 1, 1

        ":math:`P(t)`", ":py:obj:`flow[n, o, t]`", "Actual flow value"
        ":math:`P_{invest}`", ":py:obj:`invest[i, o]`", "Invested flow
        capacity"
        ":math:`b_{invest}`", ":py:obj:`invest_status[i, o]`", "Binary status
        of investment"

    List of Variables (in rst table syntax):

    ===================  =============================  =========
    symbol               attribute                      explanation
    ===================  =============================  =========
    :math:`P(t)`         :py:obj:`flow[n, o, t]`         Actual flow value

    :math:`P_{invest}`   :py:obj:`invest[i, o]`          Invested flow capacity

    :math:`b_{invest}`   :py:obj:`invest_status[i, o]`   Binary status of investment

    ===================  =============================  =========

    Grid table style:

    +--------------------+-------------------------------+-----------------------------+
    | symbol             | attribute                     | explanation                 |
    +====================+===============================+=============================+
    | :math:`P(t)`       | :py:obj:`flow[n, o, t]`       | Actual flow value           |
    +--------------------+-------------------------------+-----------------------------+
    | :math:`P_{invest}` | :py:obj:`invest[i, o]`        | Invested flow capacity      |
    +--------------------+-------------------------------+-----------------------------+
    | :math:`b_{invest}` | :py:obj:`invest_status[i, o]` | Binary status of investment |
    +--------------------+-------------------------------+-----------------------------+

    .. csv-table:: List of Parameters
        :header: "symbol", "attribute", "explanation"
        :widths: 1, 1, 1

        ":math:`P_{exist}`", ":py:obj:`flows[i, o].investment.existing`", "
        Existing flow capacity"
        ":math:`P_{invest,min}`", ":py:obj:`flows[i, o].investment.minimum`", "
        Minimum investment capacity"
        ":math:`P_{invest,max}`", ":py:obj:`flows[i, o].investment.maximum`", "
        Maximum investment capacity"
        ":math:`c_{invest,var}`", ":py:obj:`flows[i, o].investment.ep_costs`
        ", "Variable investment costs"
        ":math:`c_{invest,fix}`", ":py:obj:`flows[i, o].investment.offset`", "
        Fix investment costs"
        ":math:`f_{actual}`", ":py:obj:`flows[i, o].fix[t]`", "Normed
        fixed value for the flow variable"
        ":math:`f_{max}`", ":py:obj:`flows[i, o].max[t]`", "Normed maximum
        value of the flow"
        ":math:`f_{min}`", ":py:obj:`flows[i, o].min[t]`", "Normed minimum
        value of the flow"
        ":math:`f_{sum,max}`", ":py:obj:`flows[i, o].summed_max`", "Specific
        maximum of summed flow values (per installed capacity)"
        ":math:`f_{sum,min}`", ":py:obj:`flows[i, o].summed_min`", "Specific
        minimum of summed flow values (per installed capacity)"
        ":math:`\tau(t)`", ":py:obj:`timeincrement[t]`", "Time step width for
        each time step"

    Note
    ----
    In case of a nonconvex investment flow (:attr:`nonconvex=True`),
    the existing flow capacity :math:`P_{exist}` needs to be zero.
    At least, it is not tested yet, whether this works out, or makes any sense
    at all.

    Note
    ----
    See also :class:`oemof.solph.network.Flow`,
    :class:`oemof.solph.blocks.Flow` and
    :class:`oemof.solph.options.Investment`

    """  # noqa: E501

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        r"""Creates sets, variables and constraints for Flow with investment
        attribute of type class:`.Investment`.

        Parameters
        ----------
        group : list
            List containing tuples containing flow (f) objects that have an
            attribute investment and the associated source (s) and target (t)
            of flow e.g. groups=[(s1, t1, f1), (s2, t2, f2),..]
        """
        if group is None:
            return None

        m = self.parent_block()

        # ######################### SETS #####################################
        self.INVESTFLOWS = Set(initialize=[(g[0], g[1]) for g in group])

        self.CONVEX_INVESTFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].investment.nonconvex is False
            ]
        )

        self.NON_CONVEX_INVESTFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].investment.nonconvex is True
            ]
        )

        self.FIXED_INVESTFLOWS = Set(
            initialize=[(g[0], g[1]) for g in group if g[2].fix[0] is not None]
        )

        self.NON_FIXED_INVESTFLOWS = Set(
            initialize=[(g[0], g[1]) for g in group if g[2].fix[0] is None]
        )

        self.SUMMED_MAX_INVESTFLOWS = Set(
            initialize=[
                (g[0], g[1]) for g in group if g[2].summed_max is not None
            ]
        )

        self.SUMMED_MIN_INVESTFLOWS = Set(
            initialize=[
                (g[0], g[1]) for g in group if g[2].summed_min is not None
            ]
        )

        self.MIN_INVESTFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if (g[2].min[0] != 0 or len(g[2].min) > 1)
            ]
        )

        # ######################### VARIABLES #################################
        def _investvar_bound_rule(block, i, o):
            """Rule definition for bounds of invest variable."""
            if (i, o) in self.CONVEX_INVESTFLOWS:
                return (
                    m.flows[i, o].investment.minimum,
                    m.flows[i, o].investment.maximum,
                )
            elif (i, o) in self.NON_CONVEX_INVESTFLOWS:
                return 0, m.flows[i, o].investment.maximum

        # create invest variable for a investment flow
        self.invest = Var(
            self.INVESTFLOWS,
            within=NonNegativeReals,
            bounds=_investvar_bound_rule,
        )

        # create status variable for a non-convex investment flow
        self.invest_status = Var(self.NON_CONVEX_INVESTFLOWS, within=Binary)
        # ######################### CONSTRAINTS ###############################

        def _min_invest_rule(block, i, o):
            """Rule definition for applying a minimum investment"""
            expr = (
                m.flows[i, o].investment.minimum * self.invest_status[i, o]
                <= self.invest[i, o]
            )
            return expr

        self.minimum_rule = Constraint(
            self.NON_CONVEX_INVESTFLOWS, rule=_min_invest_rule
        )

        def _max_invest_rule(block, i, o):
            """Rule definition for applying a minimum investment"""
            expr = self.invest[i, o] <= (
                m.flows[i, o].investment.maximum * self.invest_status[i, o]
            )
            return expr

        self.maximum_rule = Constraint(
            self.NON_CONVEX_INVESTFLOWS, rule=_max_invest_rule
        )

        def _investflow_fixed_rule(block, i, o, t):
            """Rule definition of constraint to fix flow variable
            of investment flow to (normed) actual value
            """
            expr = m.flow[i, o, t] == (
                (m.flows[i, o].investment.existing + self.invest[i, o])
                * m.flows[i, o].fix[t]
            )

            return expr

        self.fixed = Constraint(
            self.FIXED_INVESTFLOWS, m.TIMESTEPS, rule=_investflow_fixed_rule
        )

        def _max_investflow_rule(block, i, o, t):
            """Rule definition of constraint setting an upper bound of flow
            variable in investment case.
            """
            expr = m.flow[i, o, t] <= (
                (m.flows[i, o].investment.existing + self.invest[i, o])
                * m.flows[i, o].max[t]
            )
            return expr

        self.max = Constraint(
            self.NON_FIXED_INVESTFLOWS, m.TIMESTEPS, rule=_max_investflow_rule
        )

        def _min_investflow_rule(block, i, o, t):
            """Rule definition of constraint setting a lower bound on flow
            variable in investment case.
            """
            expr = m.flow[i, o, t] >= (
                (m.flows[i, o].investment.existing + self.invest[i, o])
                * m.flows[i, o].min[t]
            )
            return expr

        self.min = Constraint(
            self.MIN_INVESTFLOWS, m.TIMESTEPS, rule=_min_investflow_rule
        )

        def _summed_max_investflow_rule(block, i, o):
            """Rule definition for build action of max. sum flow constraint
            in investment case.
            """
            expr = sum(
                m.flow[i, o, t] * m.timeincrement[t] for t in m.TIMESTEPS
            ) <= m.flows[i, o].summed_max * (
                self.invest[i, o] + m.flows[i, o].investment.existing
            )
            return expr

        self.summed_max = Constraint(
            self.SUMMED_MAX_INVESTFLOWS, rule=_summed_max_investflow_rule
        )

        def _summed_min_investflow_rule(block, i, o):
            """Rule definition for build action of min. sum flow constraint
            in investment case.
            """
            expr = sum(
                m.flow[i, o, t] * m.timeincrement[t] for t in m.TIMESTEPS
            ) >= (
                (m.flows[i, o].investment.existing + self.invest[i, o])
                * m.flows[i, o].summed_min
            )
            return expr

        self.summed_min = Constraint(
            self.SUMMED_MIN_INVESTFLOWS, rule=_summed_min_investflow_rule
        )

    def _objective_expression(self):
        r"""Objective expression for flows with investment attribute of type
        class:`.Investment`. The returned costs are fixed, variable and
        investment costs.
        """
        if not hasattr(self, "INVESTFLOWS"):
            return 0

        m = self.parent_block()
        investment_costs = 0

        for i, o in self.CONVEX_INVESTFLOWS:
            if m.cellular_system:
                if i.cell_list and o.cell_list:
                    intersection = set(i.cell_list) & set(o.cell_list)
                    weight = len(intersection)
                    investment_costs += (
                        self.invest[i, o]
                        * m.flows[i, o].investment.ep_costs
                        * weight
                    )
            else:
                investment_costs += (
                    self.invest[i, o] * m.flows[i, o].investment.ep_costs
                )
        for i, o in self.NON_CONVEX_INVESTFLOWS:
            if m.cellular_system:
                if i.cell_list and o.cell_list:
                    intersection = set(i.cell_list) & set(o.cell_list)
                    weight = len(intersection)
                    investment_costs += (
                        self.invest[i, o] * m.flows[i, o].investment.ep_costs * weight
                        + self.invest_status[i, o] * m.flows[i, o].investment.offset
                    )

            else:
                investment_costs += (
                    self.invest[i, o] * m.flows[i, o].investment.ep_costs
                    + self.invest_status[i, o] * m.flows[i, o].investment.offset
                )

        self.investment_costs = Expression(expr=investment_costs)
        return investment_costs
