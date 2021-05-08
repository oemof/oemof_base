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
SPDX-FileCopyrightText: Johannes Kochems (jokochems)

SPDX-License-Identifier: MIT

"""

from warnings import warn

from pyomo.core import Binary
from pyomo.core import BuildAction
from pyomo.core import Constraint
from pyomo.core import Expression
from pyomo.core import NonNegativeReals
from pyomo.core import Set
from pyomo.core import Var
from pyomo.core.base.block import SimpleBlock

from oemof.tools import economics
from oemof.tools import debugging


class MultiPeriodInvestmentFlow(SimpleBlock):
    r"""Block for all flows with :attr:`multiperiodinvestment` being not None.

    See :class:`oemof.solph.options.MultiPeriodInvestment` for all parameters
    of the *MultiPeriodInvestment* class.

    See :class:`oemof.solph.network.Flow` for all parameters of the *Flow*
    class.

    **Variables**

    All *MultiPeriodInvestmentFlow* are indexed by a starting and ending node
    :math:`(i, o)`, which is omitted in the following for the sake
    of convenience. The following variables are created:

    * :math:`P(p, t)`

        Actual flow value (created in :class:`oemof.solph.models.BaseModel`).

    * :math:`P_{invest}(p)`

        Value of the investment variable in period p, i.e. equivalent to
        the nominal value of the flows after optimization. Note that
        investments resp. decommissionings occur at the beginning of a period
        such that the unit can already be dispatched in the period where the
        investments occured.

    * :math:`P_{total}(p)`

        Value of the total installed capacity in period p accounting for
        decommissionings due to unit lifetime.

    * :math:`P_{old}(p)`

        Capacity to be decommissioned in a certain period p due to reaching
        its lifetime.

    * :math:`b_{invest}(p)`

        Binary variable for the status of the investment in period p, if
        :attr:`nonconvex` is `True`.

    **Constraints**

    Depending on the attributes of the *MultiPeriodInvestmentFlow* and *Flow*,
    different constraints are created. The following constraint is created
    for all *MultiPeriodInvestmentFlow*:\

            Upper bound for the flow value

        .. math::
            P(p, t) \le P_{total}(p) \cdot f_{max}(p, t)

    Depeding on the attribute :attr:`nonconvex`, the constraints for the bounds
    of the decision variable :math:`P_{invest}(p)` are different:\

        * :attr:`nonconvex = False`

        .. math::
            P_{invest, min}(p) \le P_{invest}(p) \le P_{invest, max}(p)

        * :attr:`nonconvex = True`

        .. math::
            &
            P_{invest, min}(p) \cdot b_{invest}(p) \le P_{invest}(p)\\
            &
            P_{invest}(p) \le P_{invest, max}(p) \cdot b_{invest}(p)\\

    Total capacity is determined based on calculating the difference between
    new investments and decommissionings of old units that have reached their
    lifetimes (n). Hereby, for old units, a distinction is made between
    existing, i.e. exogenous capacities at the beginning of the
    simulation run and endogenous installations:

        .. math::
            P_{total}(p) = P_{invest}(p) + P_{total}(p-1) - P_{old}(p) \forall
            p > 0\\
            &
            P_{total}(p) = P_{invest}(p) + P_{existing}
            for p = 0

        .. math::
            P_{old, end}(p) = P_{invest}(p-n) \forall p \geq n\\
            &
            P_{old, end}(p) = 0 else\\
            &
            P_{old, exo}(p) = P_{existing} \forall p == n - age\\
            &
            P_{old, exo}(p) = 0 else\\
            &
            P_{old}(p) = P_{old, end}(p) + P_{old, exo}(p)\\
            &

    For all *MultiPeriodInvestmentFlow* (independent of the attribute
    :attr:`nonconvex`), the following additional constraints are created,
    if the appropriate attribute of the *Flow*
    (see :class:`oemof.solph.network.Flow`) is set:

        * :attr:`fix` is not None

            Actual value constraint for investments with fixed flow values

        .. math::
            P(p, t) = ( P_{total}(p) ) \cdot f_{fix}(t)

        * :attr:`min != 0`

            Lower bound for the flow values

        .. math::
            P(p, t) \geq P_{total}(p) \cdot f_{min}(t)

        * :attr:`summed_max is not None`

            Upper bound for the sum of all flow values (e.g. maximum full load
            hours)

        .. math::
            \sum_{p, t} P(p, t) \cdot \tau(t) \leq P_{total}(p)
            \cdot f_{sum, max}

        * :attr:`summed_min is not None`

            Lower bound for the sum of all flow values (e.g. minimum full load
            hours)

        .. math::
            \sum_{p, t} P(p, t) \cdot \tau(t) \geq P_{total}(p)
            \cdot f_{sum, min}

        * :attr:`overall_maximum is not None`

            An overall maximum investment limit is introduced, imposing an
            upper bound to the total installed capacity in all periods

        .. math::
            P_{total}(p) \leq P_{overall_max} \forall p in PERIODS

        * :attr:`overall_minimum is not None`

            An overall minimum investment limit is introduced, forcing the
            total installed capacity in the last period to at least equal this
            minimum value

        .. math::
            P_{total}(p) \geq P_{overall_min} for the last period

    **Objective function**

    The part of the objective function added by the *MultiPeriodInvestmentFlow*
    also depends on whether a convex or nonconvex
    *MultiPeriodInvestmentFlow* is selected. Costs occur only for new
    investments, whereby existing capacities are treated to only account for
    sunk investments. The following parts of the  objective function are
    created:

        * :attr:`nonconvex = False`

            .. math::
                P_{invest}(p) \cdot annuity(c_{invest}(p), n, i) \cdot n
                \cdot DF(p)
                \forall p \in PERIODS

        * :attr:`nonconvex = True`

            .. math::
                (P_{invest}(p) \cdot annuity(c_{invest}(p), n, i)
                + b_{invest} \cdot c_{invest, fix})
                \cdot DF(p)
                \forall p \in PERIODS\\

    with lifetime n, interest rate i, discount factor DF(p),
    investment expenses c_{invest}(p) and

        .. math::
            annuity(c_{invest}(p), n, i) = \frac {(1+i)^n \cdot i}{(1+i)^n - 1}
            \cdot c_{invest}(p)
            &
            DF(p) = (1+d)^{-p}

    whereby d is the discount rate. The interest rate i may deviate from the
    discount rate (if a microeconomic perspective is taken).

    Fixed costs in turn are calculated the same manner for all
    MultiPeriodInvestmentFlows and added to the objective value:

        .. math::
            \sum_{pp=p}^{p+n} P_{invest}(p) \cdot c_{fixed}(pp) \cdot DF(pp)
            \cdot DF(p)
            \space \forall p \in PERIODS\\

    The total value of all costs of all *MultiPeriodInvestmentFlow*
    can be retrieved calling :meth:`om.InvestmentFlow.investment_costs.expr()`.

    .. csv-table:: List of Variables (in csv table syntax)
        :header: "symbol", "attribute", "explanation"
        :widths: 1, 1, 1

        ":math:`P(p, t)`", ":py:obj:`flow[n, o, p, t]`", "Actual flow value"
        ":math:`P_{invest}(p)`", ":py:obj:`invest[i, o, p]`", "Invested flow
        capacity"
        ":math:`P_{total}(p)`", ":py:obj:`total[i, o, p]`", "Total installed
        capacity"
        ":math:`P_{old}(p)`", ":py:obj:`old[i, o, p]`", "Capacity being
        decommissioned due to unit age"
        ":math:`P_{old, exo}(p)`", ":py:obj:`old_exo[i, o, p]`", "Existing
        (exogeneously given) capacity at the beginning being decommissioned
        due to unit age"
        ":math:`P_{old, end}(p)`", ":py:obj:`old_end[i, o, p]`", "Endogenously
        installed capacity being decommissioned due to reaching its lifetime
        in the course of the simulation"
        ":math:`b_{invest}(p)`", ":py:obj:`invest_status[i, o, p]`", "Binary
        status of investment"

    .. csv-table:: List of Parameters
        :header: "symbol", "attribute", "explanation"
        :widths: 1, 1, 1

        ":math:`P_{exist}`", ":py:obj:`flows[i, o].investment.existing`", "
        Existing flow capacity"
        ":math:`P_{invest,min}(p)`", ":py:obj:`
        flows[i, o].investment.minimum[p]`", "
        Minimum investment capacity in period p"
        ":math:`P_{invest,max}(p)`", ":py:obj:
        `flows[i, o].investment.maximum`", "
        Maximum investment capacity in period p"
        ":math:`c_{invest}(p)`", ":py:obj:`flows[i, o].investment.ep_costs`
        ", "Investment expenses (are transformed to annuities)"
        ":math:`c_{invest,fix}(p)`", ":py:obj:
        `flows[i, o].investment.offset`", "
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
        ":math:`P_{overall_max}`", ":py:obj:`flows[i, o].overall_maximum`",
        "Overall maximum capacity limitm applicable for each period"
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
    :class:`oemof.solph.blocks.MultiPeriodFlow` and
    :class:`oemof.solph.options.MultiPeriodInvestment`

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
        self.MULTIPERIODINVESTFLOWS = Set(initialize=[
            (g[0], g[1]) for g in group])

        self.CONVEX_MULTIPERIODINVESTFLOWS = Set(initialize=[
            (g[0], g[1]) for g in group
            if g[2].multiperiodinvestment.nonconvex is False])

        self.NON_CONVEX_MULTIPERIODINVESTFLOWS = Set(initialize=[
            (g[0], g[1]) for g in group
            if g[2].multiperiodinvestment.nonconvex is True])

        self.FIXED_MULTIPERIODINVESTFLOWS = Set(
            initialize=[(g[0], g[1]) for g in group if g[2].fix[0] is not
                        None])

        self.NON_FIXED_MULTIPERIODINVESTFLOWS = Set(
            initialize=[(g[0], g[1]) for g in group if g[2].fix[0] is None])

        self.SUMMED_MAX_MULTIPERIODINVESTFLOWS = Set(initialize=[
            (g[0], g[1]) for g in group if g[2].summed_max is not None])

        self.SUMMED_MIN_MULTIPERIODINVESTFLOWS = Set(initialize=[
            (g[0], g[1]) for g in group if g[2].summed_min is not None])

        self.MIN_MULTIPERIODINVESTFLOWS = Set(initialize=[
            (g[0], g[1]) for g in group if (
                g[2].min[0] != 0 or len(g[2].min) > 1)])

        self.OVERALL_MAXIMUM_MULTIPERIODINVESTFLOWS = Set(initialize=[
            (g[0], g[1]) for g in group
            if g[2].multiperiodinvestment.overall_maximum is not None])

        self.OVERALL_MINIMUM_MULTIPERIODINVESTFLOWS = Set(initialize=[
            (g[0], g[1]) for g in group
            if g[2].multiperiodinvestment.overall_minimum is not None])

        # ######################### VARIABLES #################################
        def _investvar_bound_rule(block, i, o, p):
            """Rule definition for bounds of invest variable.
            """
            if (i, o) in self.CONVEX_MULTIPERIODINVESTFLOWS:
                return (m.flows[i, o].multiperiodinvestment.minimum[p],
                        m.flows[i, o].multiperiodinvestment.maximum[p])
            elif (i, o) in self.NON_CONVEX_MULTIPERIODINVESTFLOWS:
                return 0, m.flows[i, o].multiperiodinvestment.maximum[p]

        # create invest variable for a multiperiodinvestment flow
        self.invest = Var(self.MULTIPERIODINVESTFLOWS,
                          m.PERIODS,
                          within=NonNegativeReals,
                          bounds=_investvar_bound_rule)

        # Total capacity
        self.total = Var(self.MULTIPERIODINVESTFLOWS,
                         m.PERIODS,
                         within=NonNegativeReals)

        # Old capacity to be decommissioned (due to lifetime)
        # Old capacity is built out of old exogenous and endogenous capacities
        self.old = Var(self.MULTIPERIODINVESTFLOWS,
                       m.PERIODS,
                       within=NonNegativeReals)

        # Old endogenous capacity to be decommissioned (due to lifetime)
        self.old_end = Var(self.MULTIPERIODINVESTFLOWS,
                           m.PERIODS,
                           within=NonNegativeReals)

        # Old exogenous capacity to be decommissioned (due to lifetime)
        self.old_exo = Var(self.MULTIPERIODINVESTFLOWS,
                           m.PERIODS,
                           within=NonNegativeReals)

        # create status variable for a non-convex multiperiodinvestment flow
        self.invest_status = Var(self.NON_CONVEX_MULTIPERIODINVESTFLOWS,
                                 m.PERIODS,
                                 within=Binary)

        # ######################### CONSTRAINTS ###############################

        def _min_invest_rule(block):
            """Rule definition for applying a minimum investment
            """
            for i, o in self.NON_CONVEX_MULTIPERIODINVESTFLOWS:
                for p in m.PERIODS:
                    expr = (m.flows[i, o].multiperiodinvestment.minimum[p]
                            * self.invest_status[i, o, p]
                            <= self.invest[i, o, p])
                    self.minimum_rule.add((i, o, p), expr)

        self.minimum_rule = Constraint(
            self.NON_CONVEX_MULTIPERIODINVESTFLOWS, m.PERIODS,
            noruleinit=True)
        self.minimum_rule_build = BuildAction(
            rule=_min_invest_rule)

        def _max_invest_rule(block):
            """Rule definition for applying a minimum investment
            """
            for i, o in self.NON_CONVEX_MULTIPERIODINVESTFLOWS:
                for p in m.PERIODS:
                    expr = self.invest[i, o, p] <= (
                        m.flows[i, o].multiperiodinvestment.maximum[p]
                        * self.invest_status[i, o, p])
                    self.maximum_rule.add((i, o, p), expr)

        self.maximum_rule = Constraint(
            self.NON_CONVEX_MULTIPERIODINVESTFLOWS, m.PERIODS,
            noruleinit=True)
        self.maximum_rule_build = BuildAction(
            rule=_max_invest_rule)

        # Handle unit lifetimes
        def _total_capacity_rule(block):
            """Rule definition for determining total installed
            capacity (taking decommissioning into account)
            """
            for i, o in self.MULTIPERIODINVESTFLOWS:
                for p in m.PERIODS:
                    if p == 0:
                        expr = (self.total[i, o, p]
                                == self.invest[i, o, p]
                                + m.flows[i, o].multiperiodinvestment.existing)
                        self.total_rule.add((i, o, p), expr)
                    else:
                        expr = (self.total[i, o, p]
                                == self.invest[i, o, p]
                                + self.total[i, o, p - 1]
                                - self.old[i, o, p])
                        self.total_rule.add((i, o, p), expr)

        self.total_rule = Constraint(self.MULTIPERIODINVESTFLOWS, m.PERIODS,
                                     noruleinit=True)
        self.total_rule_build = BuildAction(
            rule=_total_capacity_rule)

        def _old_capacity_rule_end(block):
            """Rule definition for determining old endogenously installed
            capacity to be decommissioned due to reaching its lifetime
            """
            for i, o in self.MULTIPERIODINVESTFLOWS:
                lifetime = m.flows[i, o].multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    if lifetime <= p:
                        expr = (self.old_end[i, o, p]
                                == self.invest[i, o, p - lifetime])
                        self.old_rule_end.add((i, o, p), expr)
                    else:
                        expr = (self.old_end[i, o, p]
                                == 0)
                        self.old_rule_end.add((i, o, p), expr)

        self.old_rule_end = Constraint(self.MULTIPERIODINVESTFLOWS, m.PERIODS,
                                       noruleinit=True)
        self.old_rule_end_build = BuildAction(
            rule=_old_capacity_rule_end)

        def _old_capacity_rule_exo(block):
            """Rule definition for determining old exogenously given capacity
            to be decommissioned due to reaching its lifetime
            """
            for i, o in self.MULTIPERIODINVESTFLOWS:
                age = m.flows[i, o].multiperiodinvestment.age
                lifetime = m.flows[i, o].multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    if lifetime - age == p:
                        expr = (
                            self.old_exo[i, o, p]
                            == m.flows[i, o].multiperiodinvestment.existing)
                        self.old_rule_exo.add((i, o, p), expr)
                    else:
                        expr = (self.old_exo[i, o, p]
                                == 0)
                        self.old_rule_exo.add((i, o, p), expr)

        self.old_rule_exo = Constraint(self.MULTIPERIODINVESTFLOWS, m.PERIODS,
                                       noruleinit=True)
        self.old_rule_exo_build = BuildAction(
            rule=_old_capacity_rule_exo)

        def _old_capacity_rule(block):
            """Rule definition for determining (overall) old capacity
            to be decommissioned due to reaching its lifetime
            """
            for i, o in self.MULTIPERIODINVESTFLOWS:
                for p in m.PERIODS:
                    expr = (
                        self.old[i, o, p]
                        == self.old_end[i, o, p] + self.old_exo[i, o, p])
                    self.old_rule.add((i, o, p), expr)

        self.old_rule = Constraint(self.MULTIPERIODINVESTFLOWS, m.PERIODS,
                                   noruleinit=True)
        self.old_rule_build = BuildAction(
            rule=_old_capacity_rule)

        def _investflow_fixed_rule(block):
            """Rule definition of constraint to fix flow variable
            of multiperiodinvestment flow to (normed) actual value
            """
            for i, o in self.FIXED_MULTIPERIODINVESTFLOWS:
                for p, t in m.TIMEINDEX:
                    expr = (m.flow[i, o, p, t] == (
                        self.total[i, o, p]
                        * m.flows[i, o].fix[t]))
                    self.fixed.add((i, o, p, t), expr)

        self.fixed = Constraint(self.FIXED_MULTIPERIODINVESTFLOWS,
                                m.TIMEINDEX,
                                noruleinit=True)
        self.fixed_build = BuildAction(
            rule=_investflow_fixed_rule)

        def _max_investflow_rule(block):
            """Rule definition of constraint setting an upper bound of flow
            variable in multiperiodinvestment case.
            """
            for i, o in self.NON_FIXED_MULTIPERIODINVESTFLOWS:
                for p, t in m.TIMEINDEX:
                    expr = (m.flow[i, o, p, t] <= (
                        self.total[i, o, p]
                        * m.flows[i, o].max[t]))
                    self.max.add((i, o, p, t), expr)

        self.max = Constraint(self.NON_FIXED_MULTIPERIODINVESTFLOWS,
                              m.TIMEINDEX,
                              noruleinit=True)
        self.max_build = BuildAction(
            rule=_max_investflow_rule)

        def _min_investflow_rule(block):
            """Rule definition of constraint setting a lower bound on flow
            variable in multiperiodinvestment case.
            """
            for i, o in self.MIN_MULTIPERIODINVESTFLOWS:
                for p, t in m.TIMEINDEX:
                    expr = (m.flow[i, o, p, t] >= (
                        self.total[i, o, p]
                        * m.flows[i, o].min[t]))
                    self.min.add((i, o, p, t), expr)

        self.min = Constraint(self.MIN_MULTIPERIODINVESTFLOWS, m.TIMEINDEX,
                              noruleinit=True)
        self.min_build = BuildAction(
            rule=_min_investflow_rule)

        def _summed_max_investflow_rule(block, i, o):
            """Rule definition for build action of max. sum flow constraint
            in multiperiodinvestment case.
            """
            expr = (sum(m.flow[i, o, p, t] * m.timeincrement[t]
                        for p, t in m.TIMEINDEX)
                    <= (m.flows[i, o].summed_max
                        * sum(self.total[i, o, p] for p in m.PERIODS)))
            return expr

        self.summed_max = Constraint(self.SUMMED_MAX_MULTIPERIODINVESTFLOWS,
                                     rule=_summed_max_investflow_rule)

        def _summed_min_investflow_rule(block, i, o):
            """Rule definition for build action of min. sum flow constraint
            in multiperiodinvestment case.
            """
            expr = (sum(m.flow[i, o, p, t] * m.timeincrement[t]
                        for p, t in m.TIMEINDEX)
                    >= (sum(self.total[i, o, p] for p in m.PERIODS)
                        * m.flows[i, o].summed_min))
            return expr

        self.summed_min = Constraint(self.SUMMED_MIN_MULTIPERIODINVESTFLOWS,
                                     rule=_summed_min_investflow_rule)

        def _overall_maximum_investflow_rule(block):
            """Rule definition for maximum overall investment
            in multiperiodinvestment case.

            Note: In general, there are two different options to define
            an overall maximum:
            1.) overall_max = limit for (net) installed capacity
            for each period. This is the constraint used here
            2.) overall max = sum of all (gross) investments occuring
            """
            for i, o in self.OVERALL_MAXIMUM_MULTIPERIODINVESTFLOWS:
                for p in m.PERIODS:
                    expr = (
                        self.total[i, o, p]
                        <= m.flows[i, o].multiperiodinvestment.overall_maximum
                    )
                    self.overall_maximum.add((i, o, p), expr)

        self.overall_maximum = Constraint(
            self.OVERALL_MAXIMUM_MULTIPERIODINVESTFLOWS,
            m.PERIODS,
            noruleinit=True)
        self.overall_maximum_build = BuildAction(
            rule=_overall_maximum_investflow_rule)

        def _overall_minimum_investflow_rule(block, i, o):
            """Rule definition for minimum overall investment
            in multiperiodinvestment case.

            Note: This is only applicable for the last period
            """
            expr = (
                m.flows[i, o].multiperiodinvestment.overall_minimum
                <= self.total[i, o, m.PERIODS[-1]]
            )
            return expr

        self.overall_minimum = Constraint(
            self.OVERALL_MINIMUM_MULTIPERIODINVESTFLOWS,
            rule=_overall_minimum_investflow_rule)

    def _objective_expression(self):
        r""" Objective expression for flows with multiperiodinvestment
        attribute of type class:`.MultiPeriod`. The returned costs are fixed,
        variable and multiperiodinvestment costs.
        """
        if not hasattr(self, 'MULTIPERIODINVESTFLOWS'):
            return 0

        m = self.parent_block()
        investment_costs = 0
        fixed_costs = 0

        for i, o in self.CONVEX_MULTIPERIODINVESTFLOWS:
            lifetime = m.flows[i, o].multiperiodinvestment.lifetime
            interest = m.flows[i, o].multiperiodinvestment.interest_rate
            if interest == 0:
                msg = ("You did not specify an interest rate.\n"
                       "It will be set equal to the discount_rate of {} "
                       "of the model as a default.\nThis corresponds to a "
                       "social planner point of view and does not reflect "
                       "microeconomic interest requirements.")
                warn(msg.format(m.discount_rate),
                     debugging.SuspiciousUsageWarning)
                interest = m.discount_rate
            for p in m.PERIODS:
                annuity = economics.annuity(
                    capex=m.flows[i, o].multiperiodinvestment.ep_costs[p],
                    n=lifetime,
                    wacc=interest)
                investment_costs += (
                    self.invest[i, o, p] * annuity * lifetime
                    * ((1 + m.discount_rate) ** (-p))
                )
        for i, o in self.NON_CONVEX_MULTIPERIODINVESTFLOWS:
            lifetime = m.flows[i, o].multiperiodinvestment.lifetime
            interest = m.flows[i, o].multiperiodinvestment.interest_rate
            if interest == 0:
                msg = ("You did not specify an interest rate.\n"
                       "It will be set equal to the discount_rate of {} "
                       "of the model as a default.\nThis corresponds to a "
                       "social planner point of view and does not reflect "
                       "microeconomic interest requirements.")
                warn(msg.format(m.discount_rate),
                     debugging.SuspiciousUsageWarning)
                interest = m.discount_rate
            for p in m.PERIODS:
                annuity = economics.annuity(
                    capex=m.flows[i, o].multiperiodinvestment.ep_costs[p],
                    n=lifetime,
                    wacc=interest)
                investment_costs += (
                    (self.invest[i, o, p] * annuity * lifetime
                     + self.invest_status[i, o, p]
                     * m.flows[i, o].multiperiodinvestment.offset[p])
                    * ((1 + m.discount_rate) ** (-p))
                )
        for i, o in self.MULTIPERIODINVESTFLOWS:
            if m.flows[i, o].multiperiodinvestment.fixed_costs[0] is not None:
                lifetime = m.flows[i, o].multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    fixed_costs += (
                        sum(self.invest[i, o, p]
                            * m.flows[i, o].multiperiodinvestment
                            .fixed_costs[pp]
                            * ((1 + m.discount_rate) ** (-pp))
                            for pp in range(p, p + lifetime)
                            )
                        * ((1 + m.discount_rate) ** (-p))
                    )

        self.costs = Expression(expr=investment_costs + fixed_costs)
        return investment_costs + fixed_costs
