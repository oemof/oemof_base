# -*- coding: utf-8 -*-

"""Creating sets, variables, constraints and parts of the objective function
for Flow objects with investment but without nonconvex option.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: Birgit Schachler
SPDX-FileCopyrightText: jnnr
SPDX-FileCopyrightText: jmloenneberga
SPDX-FileCopyrightText: Johannes Kochems

SPDX-License-Identifier: MIT

"""
from warnings import warn

import numpy as np
from oemof.tools import debugging
from oemof.tools import economics
from pyomo.core import Binary
from pyomo.core import BuildAction
from pyomo.core import Constraint
from pyomo.core import Expression
from pyomo.core import NonNegativeReals
from pyomo.core import Set
from pyomo.core import Var
from pyomo.core.base.block import ScalarBlock

from oemof.solph._plumbing import valid_sequence


class InvestmentFlowBlock(ScalarBlock):
    r"""Block for all flows with :attr:`Investment` being not None.

    .. automethod:: _create_constraints
    .. automethod:: _create_variables
    .. automethod:: _create_sets

    .. automethod:: _objective_expression

    See :class:`oemof.solph.options.Investment` for all parameters of the
    *Investment* class.

    See :class:`oemof.solph.flows._simple_flow_block.SimpleFlowBlock`
    for all parameters of the *SimpleFlowBlock* class.

    The overall summed cost expressions for all *InvestmentFlowBlock* objects
    can be accessed by

    * :attr:`om.InvestmentFlowBlock.investment_costs`,
    * :attr:`om.InvestmentFlowBlock.fixed_costs` and
    * :attr:`om.InvestmentFlowBlock.costs`.

    Their values  after optimization can be retrieved by

    * :meth:`om.InvestmentFlowBlock.investment_costs`,
    * :attr:`om.InvestmentFlowBlock.period_investment_costs` (yielding a dict
      keyed by periods); note: this is not a Pyomo expression, but calculated,
    * :meth:`om.InvestmentFlowBlock.fixed_costs` and
    * :meth:`om.InvestmentFlowBlock.costs`.

    Note
    ----
    In case of a nonconvex investment flow (:attr:`nonconvex=True`),
    the existing flow capacity :math:`P_{exist}` needs to be zero.

    Note
    ----
    See also :class:`~oemof.solph.flows._flow.Flow`,
    :class:`~oemof.solph.flows._simple_flow_block.SimpleFlowBlock` and
    :class:`~oemof.solph._options.Investment`

    """  # noqa: E501

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        r"""Creates sets, variables and constraints for SimpleFlowBlock
        with investment attribute of type class:`.Investment`.

        Parameters
        ----------
        group : list
            List containing tuples containing flow (f) objects that have an
            attribute investment and the associated source (s) and target (t)
            of flow e.g. groups=[(s1, t1, f1), (s2, t2, f2),..]
        """
        if group is None:
            return None

        self._create_sets(group)
        self._create_variables(group)
        self._create_constraints()

    def _create_sets(self, group):
        """
        Creates all sets for investment flows.
        """
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
            initialize=[(g[0], g[1]) for g in group if g[2].fixed is True]
        )

        self.NON_FIXED_INVESTFLOWS = Set(
            initialize=[(g[0], g[1]) for g in group if g[2].fixed is True]
        )

        self.FULL_LOAD_TIME_MAX_INVESTFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].full_load_time_max is not None
            ]
        )

        self.FULL_LOAD_TIME_MIN_INVESTFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].full_load_time_min is not None
            ]
        )

        self.MIN_INVESTFLOWS = Set(
            initialize=[(g[0], g[1]) for g in group if g[2].min.min() != 0]
        )

        self.EXISTING_INVESTFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].investment.existing is not None
            ]
        )

        self.OVERALL_MAXIMUM_INVESTFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].investment.overall_maximum is not None
            ]
        )

        self.OVERALL_MINIMUM_INVESTFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].investment.overall_minimum is not None
            ]
        )

    def _create_variables(self, _):
        r"""Creates all variables for investment flows.

        All *InvestmentFlowBlock* objects are indexed by a starting and
        ending node :math:`(i, o)`, which is omitted in the following
        for the sake of convenience. The following variables are created:

        * :math:`P(p, t)`

            Actual flow value
            (created in :class:`oemof.solph.models.Model`),
            indexed by tuple of periods p and timestep t

        * :math:`P_{invest}(p)`

            Value of the investment variable in period p,
            equal to what is being invested and equivalent resp. similar to
            the nominal capacity of the flows after optimization.

        * :math:`P_{total}(p)`

            Total installed capacity / energy in period p,
            equivalent to the nominal capacity of the flows after optimization.

        * :math:`P_{old}(p)`

            Old capacity / energy to be decommissioned in period p
            due to reaching its lifetime; applicable only
            for multi-period models.

        * :math:`P_{old,exo}(p)`

            Old exogenous capacity / energy to be decommissioned in period p
            due to reaching its lifetime, i.e. the amount that has
            been specified by :attr:`existing` when it is decommisioned;
            applicable only for multi-period models.

        * :math:`P_{old,end}(p)`

            Old endogenous capacity / energy to be decommissioned in period p
            due to reaching its lifetime, i.e. the amount that has been
            invested in by the model itself that is decommissioned in
            a later period because of reaching its lifetime;
            applicable only for multi-period models.

        * :math:`Y_{invest}(p)`

            Binary variable for the status of the investment, if
            :attr:`nonconvex` is `True`.
        """
        m = self.parent_block()

        def _investvar_bound_rule(block, i, o, p):
            """Rule definition for bounds of invest variable."""
            if (i, o) in self.CONVEX_INVESTFLOWS:
                return (
                    m.flows[i, o].investment.minimum[p],
                    m.flows[i, o].investment.maximum[p],
                )
            elif (i, o) in self.NON_CONVEX_INVESTFLOWS:
                return 0, m.flows[i, o].investment.maximum[p]

        # create invest variable for an investment flow
        self.invest = Var(
            self.INVESTFLOWS,
            m.PERIODS,
            within=NonNegativeReals,
            bounds=_investvar_bound_rule,
        )

        # Total capacity
        self.total = Var(self.INVESTFLOWS, m.PERIODS, within=NonNegativeReals)

        if m.es.periods is not None:
            self.old = Var(
                self.INVESTFLOWS, m.PERIODS, within=NonNegativeReals
            )

            # Old endogenous capacity to be decommissioned (due to lifetime)
            self.old_end = Var(
                self.INVESTFLOWS, m.PERIODS, within=NonNegativeReals
            )

            # Old exogenous capacity to be decommissioned (due to lifetime)
            self.old_exo = Var(
                self.INVESTFLOWS, m.PERIODS, within=NonNegativeReals
            )

        # create status variable for a non-convex investment flow
        self.invest_status = Var(
            self.NON_CONVEX_INVESTFLOWS, m.PERIODS, within=Binary
        )

    def _create_constraints(self):
        r"""Creates all constraints for standard flows.

        Depending on the attributes of the *InvestmentFlowBlock*
        and *SimpleFlowBlock*, different constraints are created.
        The following constraints are created
        for all *InvestmentFlowBlock* objects:\

            Total capacity / energy

            .. math::
                &
                if \quad p=0:\\
                &
                P_{total}(p) = P_{invest}(p) + P_{exist}(p) \\
                &\\
                &
                else:\\
                &
                P_{total}(p) = P_{total}(p-1) + P_{invest}(p) - P_{old}(p) \\
                &\\
                &
                \forall p \in \textrm{PERIODS}

            Upper bound for the flow value

            .. math::
                &
                P(p, t) \le ( P_{total}(p) ) \cdot f_{max}(t) \\
                &
                \forall p, t \in \textrm{TIMEINDEX}

        For a multi-period model, the old capacity is defined as follows:

            .. math::
                &
                P_{old}(p) = P_{old,exo}(p) + P_{old,end}(p)\\
                &\\
                &
                if \quad p=0:\\
                &
                P_{old,end}(p) = 0\\
                &\\
                &
                else \quad if \quad l \leq year(p):\\
                &
                P_{old,end}(p) = P_{invest}(p_{comm})\\
                &\\
                &
                else:\\
                &
                P_{old,end}(p) = 0\\
                &\\
                &
                if \quad p=0:\\
                &
                P_{old,exo}(p) = 0\\
                &\\
                &
                else \quad if \quad l - a \leq year(p):\\
                &
                P_{old,exo}(p) = P_{exist} (*)\\
                &\\
                &
                else:\\
                &
                P_{old,exo}(p) = 0\\
                &\\
                &
                \forall p \in \textrm{PERIODS}

            where:

            * (*) is only performed for the first period the condition
              is True. A decommissioning flag is then set to True
              to prevent having falsely added old capacity in future periods.
            * :math:`year(p)` is the year corresponding to period p
            * :math:`p_{comm}` is the commissioning period of the flow
              (which is determined by the model itself)

        Depending on the attribute :attr:`nonconvex`, the constraints for the
        bounds of the decision variable :math:`P_{invest}(p)` are different:\

            * :attr:`nonconvex = False`

            .. math::
                &
                P_{invest, min}(p) \le P_{invest}(p) \le P_{invest, max}(p) \\
                &
                \forall p \in \textrm{PERIODS}

            * :attr:`nonconvex = True`

            .. math::
                &
                P_{invest, min}(p) \cdot Y_{invest}(p) \le P_{invest}(p)\\
                &
                P_{invest}(p) \le P_{invest, max}(p) \cdot Y_{invest}(p)\\
                &\\
                &
                \forall p \in \textrm{PERIODS}

        For all *InvestmentFlowBlock* objects
        (independent of the attribute :attr:`nonconvex`),
        the following additional constraints are created, if the appropriate
        attribute of the *SimpleFlowBlock*
        (see :class:`oemof.solph.flows._simple_flow_block.SimpleFlowBlock`)
        is set:

            * :attr:`fix` is not None

                Actual value constraint for investments with fixed flow values

            .. math::
                &
                P(p, t) = P_{total}(p) \cdot f_{fix}(t) \\
                &\\
                &
                \forall p, t \in \textrm{TIMEINDEX}

            * :attr:`min != 0`

                Lower bound for the flow values

            .. math::
                &
                P(p, t) \geq P_{total}(p) \cdot f_{min}(t) \\
                &\\
                &
                \forall p, t \in \textrm{TIMEINDEX}

            * :attr:`full_load_time_max is not None`

                Upper bound for the sum of all flow values
                (e.g. maximum full load hours)

            .. math::
                \sum_{p, t} P(p, t) \cdot \tau(t) \leq P_{total}(p)
                \cdot t_{full\_load, min}

            * :attr:`full_load_time_min is not None`

                Lower bound for the sum of all flow values
                (e.g. minimum full load hours)

            .. math::
                \sum_{p, t} P(t) \cdot \tau(t) \geq P_{total}
                \cdot t_{full\_load, min}

            * :attr:`overall_maximum` is not None
              (for multi-period model only)

                Overall maximum of total installed capacity / energy for flow

            .. math::
                &
                P_{total}(p) \leq P_{overall,max} \\
                &\\
                &
                \forall p \in \textrm{PERIODS}

            * :attr:`overall_minimum` is not None
              (for multi-period model only)

                Overall minimum of total installed capacity / energy for flow;
                applicable only in last period

            .. math::
                P_{total}(p_{last}) \geq P_{overall,min}
        """
        m = self.parent_block()

        self.minimum_rule = self._minimum_investment_constraint()
        self.maximum_rule = self._maximum_investment_constraint()

        # Handle unit lifetimes
        def _total_capacity_rule(block):
            """Rule definition for determining total installed
            capacity (taking decommissioning into account)
            """
            for i, o in self.INVESTFLOWS:
                for p in m.PERIODS:
                    if p == 0:
                        expr = (
                            self.total[i, o, p]
                            == self.invest[i, o, p]
                            + m.flows[i, o].investment.existing
                        )
                        self.total_rule.add((i, o, p), expr)
                    # applicable for multi-period model only
                    else:
                        expr = (
                            self.total[i, o, p]
                            == self.invest[i, o, p]
                            + self.total[i, o, p - 1]
                            - self.old[i, o, p]
                        )
                        self.total_rule.add((i, o, p), expr)

        self.total_rule = Constraint(
            self.INVESTFLOWS, m.PERIODS, noruleinit=True
        )
        self.total_rule_build = BuildAction(rule=_total_capacity_rule)

        if m.es.periods is not None:

            def _old_capacity_rule_end(block):
                """Rule definition for determining old endogenously installed
                capacity to be decommissioned due to reaching its lifetime.
                Investment and decommissioning periods are linked within
                the constraint. The respective decommissioning period is
                determined for every investment period based on the components
                lifetime and a matrix describing its age of each endogenous
                investment. Decommissioning can only occur at the beginning of
                each period.

                Note
                ----
                For further information on the implementation check
                PR#957 https://github.com/oemof/oemof-solph/pull/957
                """
                for i, o in self.INVESTFLOWS:
                    lifetime = m.flows[i, o].investment.lifetime
                    if lifetime is None:
                        msg = (
                            "You have to specify a lifetime "
                            "for a Flow with an associated "
                            "investment object in "
                            f"a multi-period model! Value for {(i, o)} "
                            "is missing."
                        )
                        raise ValueError(msg)

                    # get the period matrix describing the temporal distance
                    # between all period combinations.
                    periods_matrix = m.es.periods_matrix

                    # get the index of the minimum value in each row greater
                    # equal than the lifetime. This value equals the
                    # decommissioning period if not zero. The index of this
                    # value represents the investment period. If np.where
                    # condition is not met in any row, min value will be zero
                    decomm_periods = np.argmin(
                        np.where(
                            (periods_matrix >= lifetime),
                            periods_matrix,
                            np.inf,
                        ),
                        axis=1,
                    )

                    # no decommissioning in first period
                    expr = self.old_end[i, o, 0] == 0
                    self.old_rule_end.add((i, o, 0), expr)

                    # all periods not in decomm_periods have no decommissioning
                    # zero is excluded
                    for p in m.PERIODS:
                        if p not in decomm_periods and p != 0:
                            expr = self.old_end[i, o, p] == 0
                            self.old_rule_end.add((i, o, p), expr)

                    # multiple invests can be decommissioned in the same period
                    # but only sequential ones, thus a bookkeeping is
                    # introduced and constraints are added to equation one
                    # iteration later.
                    last_decomm_p = np.nan
                    # loop over invest periods (values are decomm_periods)
                    for invest_p, decomm_p in enumerate(decomm_periods):
                        # Add constraint of iteration before
                        # (skipped in first iteration by last_decomm_p = nan)
                        if (decomm_p != last_decomm_p) and (
                            last_decomm_p is not np.nan
                        ):
                            expr = self.old_end[i, o, last_decomm_p] == expr
                            self.old_rule_end.add((i, o, last_decomm_p), expr)

                        # no decommissioning if decomm_p is zero
                        if decomm_p == 0:
                            # overwrite decomm_p with zero to avoid
                            # chaining invest periods in next iteration
                            last_decomm_p = 0

                        # if decomm_p is the same as the last one chain invest
                        # period
                        elif decomm_p == last_decomm_p:
                            expr += self.invest[i, o, invest_p]
                            # overwrite decomm_p
                            last_decomm_p = decomm_p

                        # if decomm_p is not zero, not the same as the last one
                        # and it's not the first period
                        else:
                            expr = self.invest[i, o, invest_p]
                            # overwrite decomm_p
                            last_decomm_p = decomm_p

                    # Add constraint of very last iteration
                    if last_decomm_p != 0:
                        expr = self.old_end[i, o, last_decomm_p] == expr
                        self.old_rule_end.add((i, o, last_decomm_p), expr)

            self.old_rule_end = Constraint(
                self.INVESTFLOWS, m.PERIODS, noruleinit=True
            )
            self.old_rule_end_build = BuildAction(rule=_old_capacity_rule_end)

            def _old_capacity_rule_exo(block):
                """Rule definition for determining old exogenously given
                capacity to be decommissioned due to reaching its lifetime
                """
                for i, o in self.INVESTFLOWS:
                    age = m.flows[i, o].investment.age
                    lifetime = m.flows[i, o].investment.lifetime
                    is_decommissioned = False
                    for p in m.PERIODS:
                        # No shutdown in first period
                        if p == 0:
                            expr = self.old_exo[i, o, p] == 0
                            self.old_rule_exo.add((i, o, p), expr)
                        elif lifetime - age <= m.es.periods_years[p]:
                            # Track decommissioning status
                            if not is_decommissioned:
                                expr = (
                                    self.old_exo[i, o, p]
                                    == m.flows[i, o].investment.existing
                                )
                                is_decommissioned = True
                            else:
                                expr = self.old_exo[i, o, p] == 0
                            self.old_rule_exo.add((i, o, p), expr)
                        else:
                            expr = self.old_exo[i, o, p] == 0
                            self.old_rule_exo.add((i, o, p), expr)

            self.old_rule_exo = Constraint(
                self.INVESTFLOWS, m.PERIODS, noruleinit=True
            )
            self.old_rule_exo_build = BuildAction(rule=_old_capacity_rule_exo)

            def _old_capacity_rule(block):
                """Rule definition for determining (overall) old capacity
                to be decommissioned due to reaching its lifetime
                """
                for i, o in self.INVESTFLOWS:
                    for p in m.PERIODS:
                        expr = (
                            self.old[i, o, p]
                            == self.old_end[i, o, p] + self.old_exo[i, o, p]
                        )
                        self.old_rule.add((i, o, p), expr)

            self.old_rule = Constraint(
                self.INVESTFLOWS, m.PERIODS, noruleinit=True
            )
            self.old_rule_build = BuildAction(rule=_old_capacity_rule)

        def _investflow_fixed_rule(block):
            """Rule definition of constraint to fix flow variable
            of investment flow to (normed) actual value
            """
            for i, o in self.FIXED_INVESTFLOWS:
                for p, t in m.TIMEINDEX:
                    expr = (
                        m.flow[i, o, t]
                        == self.total[i, o, p] * m.flows[i, o].value[t]
                    )
                    self.fixed.add((i, o, p, t), expr)

        self.fixed = Constraint(
            self.FIXED_INVESTFLOWS, m.TIMEINDEX, noruleinit=True
        )
        self.fixed_build = BuildAction(rule=_investflow_fixed_rule)

        def _max_investflow_rule(block):
            """Rule definition of constraint setting an upper bound of flow
            variable in investment case.
            """
            for i, o in self.NON_FIXED_INVESTFLOWS:
                for p, t in m.TIMEINDEX:
                    expr = (
                        m.flow[i, o, t]
                        <= self.total[i, o, p] * m.flows[i, o].max[t]
                    )
                    self.max.add((i, o, p, t), expr)

        self.max = Constraint(
            self.NON_FIXED_INVESTFLOWS, m.TIMEINDEX, noruleinit=True
        )
        self.max_build = BuildAction(rule=_max_investflow_rule)

        def _min_investflow_rule(block):
            """Rule definition of constraint setting a lower bound on flow
            variable in investment case.
            """
            for i, o in self.MIN_INVESTFLOWS:
                for p, t in m.TIMEINDEX:
                    expr = (
                        m.flow[i, o, t]
                        >= self.total[i, o, p] * m.flows[i, o].min[t]
                    )
                    self.min.add((i, o, p, t), expr)

        self.min = Constraint(
            self.MIN_INVESTFLOWS, m.TIMEINDEX, noruleinit=True
        )
        self.min_build = BuildAction(rule=_min_investflow_rule)

        def _full_load_time_max_investflow_rule(_, i, o):
            """Rule definition for build action of max. sum flow constraint
            in investment case.
            """
            expr = sum(
                m.flow[i, o, t] * m.timeincrement[t] for t in m.TIMESTEPS
            ) <= (
                m.flows[i, o].full_load_time_max
                * sum(self.total[i, o, p] for p in m.PERIODS)
            )
            return expr

        self.full_load_time_max = Constraint(
            self.FULL_LOAD_TIME_MAX_INVESTFLOWS,
            rule=_full_load_time_max_investflow_rule,
        )

        def _full_load_time_min_investflow_rule(_, i, o):
            """Rule definition for build action of min. sum flow constraint
            in investment case.
            """
            expr = sum(
                m.flow[i, o, t] * m.timeincrement[t] for t in m.TIMESTEPS
            ) >= (
                sum(self.total[i, o, p] for p in m.PERIODS)
                * m.flows[i, o].full_load_time_min
            )
            return expr

        self.full_load_time_min = Constraint(
            self.FULL_LOAD_TIME_MIN_INVESTFLOWS,
            rule=_full_load_time_min_investflow_rule,
        )

        if m.es.periods is not None:

            def _overall_maximum_investflow_rule(block):
                """Rule definition for maximum overall investment
                in investment case.
                """
                for i, o in self.OVERALL_MAXIMUM_INVESTFLOWS:
                    for p in m.PERIODS:
                        expr = (
                            self.total[i, o, p]
                            <= m.flows[i, o].investment.overall_maximum
                        )
                        self.overall_maximum.add((i, o, p), expr)

            self.overall_maximum = Constraint(
                self.OVERALL_MAXIMUM_INVESTFLOWS, m.PERIODS, noruleinit=True
            )
            self.overall_maximum_build = BuildAction(
                rule=_overall_maximum_investflow_rule
            )

            def _overall_minimum_investflow_rule(block, i, o):
                """Rule definition for minimum overall investment
                in investment case.

                Note: This is only applicable for the last period
                """
                expr = (
                    m.flows[i, o].investment.overall_minimum
                    <= self.total[i, o, m.PERIODS[-1]]
                )
                return expr

            self.overall_minimum = Constraint(
                self.OVERALL_MINIMUM_INVESTFLOWS,
                rule=_overall_minimum_investflow_rule,
            )

    def _objective_expression(self):
        r"""Objective expression for flows with investment attribute of type
        class:`.Investment`. The returned costs are fixed and
        investment costs. Variable costs are added from the standard flow
        objective expression.

        Objective terms for a standard model and a multi-period model differ
        quite strongly. Besides, the part of the objective function added by
        the *InvestmentFlowBlock* also depends on whether a convex
        or nonconvex *InvestmentFlowBlock* is selected.
        The following parts of the objective function are created:

        *Standard model*

            * :attr:`nonconvex = False`

                .. math::
                    P_{invest}(0) \cdot c_{invest,var}(0)

            * :attr:`nonconvex = True`

                .. math::
                    P_{invest}(0) \cdot c_{invest,var}(0)
                    + c_{invest,fix}(0) \cdot Y_{invest}(0) \\

        Where 0 denotes the 0th (investment) period since
        in a standard model, there is only this one period.

        *Multi-period model*

            * :attr:`nonconvex = False`

                .. math::
                    &
                    P_{invest}(p) \cdot A(c_{invest,var}(p), l, ir)
                    \cdot \frac {1}{ANF(d, ir)} \cdot DF^{-p}\\
                    &\\
                    &
                    \forall p \in \textrm{PERIODS}

            In case, the remaining lifetime of an asset is greater than 0 and
            attribute `use_remaining_value` of the energy system is True,
            the difference in value for the investment period compared to the
            last period of the optimization horizon is accounted for
            as an adder to the investment costs:

                .. math::
                    &
                    P_{invest}(p) \cdot (A(c_{invest,var}(p), l_{r}, ir) -
                    A(c_{invest,var}(|P|), l_{r}, ir)\\
                    & \cdot \frac {1}{ANF(l_{r}, ir)} \cdot DF^{-|P|}\\
                    &\\
                    &
                    \forall p \in \textrm{PERIODS}

            * :attr:`nonconvex = True`

                .. math::
                    &
                    (P_{invest}(p) \cdot A(c_{invest,var}(p), l, ir)
                    \cdot \frac {1}{ANF(d, ir)}\\
                    &
                    +  c_{invest,fix}(p) \cdot b_{invest}(p)) \cdot DF^{-p}\\
                    &\\
                    &
                    \forall p \in \textrm{PERIODS}

            In case, the remaining lifetime of an asset is greater than 0 and
            attribute `use_remaining_value` of the energy system is True,
            the difference in value for the investment period compared to the
            last period of the optimization horizon is accounted for
            as an adder to the investment costs:

                .. math::
                    &
                    (P_{invest}(p) \cdot (A(c_{invest,var}(p), l_{r}, ir) -
                    A(c_{invest,var}(|P|), l_{r}, ir)\\
                    & \cdot \frac {1}{ANF(l_{r}, ir)} \cdot DF^{-|P|}\\
                    &
                    +  (c_{invest,fix}(p) - c_{invest,fix}(|P|))
                    \cdot b_{invest}(p)) \cdot DF^{-p}\\
                    &\\
                    &
                    \forall p \in \textrm{PERIODS}

            * :attr:`fixed_costs` not None for investments

                .. math::
                    &
                    (\sum_{pp=year(p)}^{limit_{end}}
                    P_{invest}(p) \cdot c_{fixed}(pp) \cdot DF^{-pp})
                    \cdot DF^{-p}\\
                    &\\
                    &
                    \forall p \in \textrm{PERIODS}

            * :attr:`fixed_costs` not None for existing capacity

                .. math::
                    \sum_{pp=0}^{limit_{exo}} P_{exist} \cdot c_{fixed}(pp)
                    \cdot DF^{-pp}


        where:

        * :math:`A(c_{invest,var}(p), l, ir)` A is the annuity for
          investment expenses :math:`c_{invest,var}(p)`, lifetime :math:`l`
          and interest rate :math:`ir`.
        * :math:`l_{r}` is the remaining lifetime at the end of the
          optimization horizon (in case it is greater than 0 and
          smaller than the actual lifetime).
        * :math:`ANF(d, ir)` is the annuity factor for duration :math:`d`
          and interest rate :math:`ir`.
        * :math:`d=min\{year_{max} - year(p), l\}` defines the
          number of years within the optimization horizon that investment
          annuities are accounted for.
        * :math:`year(p)` denotes the start year of period :math:`p`.
        * :math:`year_{max}` denotes the last year of the optimization
          horizon, i.e. at the end of the last period.
        * :math:`limit_{end}=min\{year_{max}, year(p) + l\}` is used as an
          upper bound to ensure fixed costs for endogenous investments
          to occur within the optimization horizon.
        * :math:`limit_{exo}=min\{year_{max}, l - a\}` is used as an
          upper bound to ensure fixed costs for existing capacities to occur
          within the optimization horizon. :math:`a` is the initial age
          of an asset.
        * :math:`DF=(1+dr)` is the discount factor.

        The annuity / annuity factor hereby is:

            .. math::
                &
                A(c_{invest,var}(p), l, ir) = c_{invest,var}(p) \cdot
                    \frac {(1+ir)^l \cdot ir} {(1+ir)^l - 1}\\
                &\\
                &
                ANF(d, ir)=\frac {(1+ir)^d \cdot ir} {(1+ir)^d - 1}

        They are derived using the reciprocal of the oemof.tools.economics
        annuity function with a capex of 1.
        The interest rate :math:`ir` for the annuity is defined as weighted
        average costs of capital (wacc) and assumed constant over time.
        """
        if not hasattr(self, "INVESTFLOWS"):
            return 0

        m = self.parent_block()
        investment_costs = 0
        period_investment_costs = {p: 0 for p in m.PERIODS}
        fixed_costs = 0

        if m.es.periods is None:
            for i, o in self.CONVEX_INVESTFLOWS:
                for p in m.PERIODS:
                    investment_costs += (
                        self.invest[i, o, p]
                        * m.flows[i, o].investment.ep_costs[p]
                    )

            for i, o in self.NON_CONVEX_INVESTFLOWS:
                for p in m.PERIODS:
                    investment_costs += (
                        self.invest[i, o, p]
                        * m.flows[i, o].investment.ep_costs[p]
                        + self.invest_status[i, o, p]
                        * m.flows[i, o].investment.offset[p]
                    )

        else:
            msg = (
                "You did not specify an interest rate.\n"
                "It will be set equal to the discount_rate of {} "
                "of the model as a default.\nThis corresponds to a "
                "social planner point of view and does not reflect "
                "microeconomic interest requirements."
            )
            for i, o in self.CONVEX_INVESTFLOWS:
                lifetime = m.flows[i, o].investment.lifetime
                interest = m.flows[i, o].investment.interest_rate
                if interest == 0:
                    warn(
                        msg.format(m.discount_rate),
                        debugging.SuspiciousUsageWarning,
                    )
                    interest = m.discount_rate
                for p in m.PERIODS:
                    annuity = economics.annuity(
                        capex=m.flows[i, o].investment.ep_costs[p],
                        n=lifetime,
                        wacc=interest,
                    )
                    duration = min(
                        m.es.end_year_of_optimization - m.es.periods_years[p],
                        lifetime,
                    )
                    present_value_factor_remaining = 1 / economics.annuity(
                        capex=1, n=duration, wacc=interest
                    )
                    investment_costs_increment = (
                        self.invest[i, o, p]
                        * annuity
                        * present_value_factor_remaining
                    ) * (1 + m.discount_rate) ** (-m.es.periods_years[p])
                    remaining_value_difference = (
                        self._evaluate_remaining_value_difference(
                            m,
                            p,
                            i,
                            o,
                            m.es.end_year_of_optimization,
                            lifetime,
                            interest,
                        )
                    )
                    investment_costs += (
                        investment_costs_increment + remaining_value_difference
                    )
                    period_investment_costs[p] += investment_costs_increment

            for i, o in self.NON_CONVEX_INVESTFLOWS:
                lifetime = m.flows[i, o].investment.lifetime
                interest = m.flows[i, o].investment.interest_rate
                if interest == 0:
                    warn(
                        msg.format(m.discount_rate),
                        debugging.SuspiciousUsageWarning,
                    )
                    interest = m.discount_rate
                for p in m.PERIODS:
                    annuity = economics.annuity(
                        capex=m.flows[i, o].investment.ep_costs[p],
                        n=lifetime,
                        wacc=interest,
                    )
                    duration = min(
                        m.es.end_year_of_optimization - m.es.periods_years[p],
                        lifetime,
                    )
                    present_value_factor_remaining = 1 / economics.annuity(
                        capex=1, n=duration, wacc=interest
                    )
                    investment_costs_increment = (
                        self.invest[i, o, p]
                        * annuity
                        * present_value_factor_remaining
                        + self.invest_status[i, o, p]
                        * m.flows[i, o].investment.offset[p]
                    ) * (1 + m.discount_rate) ** (-m.es.periods_years[p])
                    remaining_value_difference = (
                        self._evaluate_remaining_value_difference(
                            m,
                            p,
                            i,
                            o,
                            m.es.end_year_of_optimization,
                            lifetime,
                            interest,
                            nonconvex=True,
                        )
                    )
                    investment_costs += (
                        investment_costs_increment + remaining_value_difference
                    )
                    period_investment_costs[p] += investment_costs_increment

            for i, o in self.INVESTFLOWS:
                if valid_sequence(
                    m.flows[i, o].investment.fixed_costs, len(m.PERIODS)
                ):
                    lifetime = m.flows[i, o].investment.lifetime
                    for p in m.PERIODS:
                        range_limit = min(
                            m.es.end_year_of_optimization,
                            m.es.periods_years[p] + lifetime,
                        )
                        fixed_costs += sum(
                            self.invest[i, o, p]
                            * m.flows[i, o].investment.fixed_costs[pp]
                            * (1 + m.discount_rate) ** (-pp)
                            for pp in range(m.es.periods_years[p], range_limit)
                        )

            for i, o in self.EXISTING_INVESTFLOWS:
                if valid_sequence(
                    m.flows[i, o].investment.fixed_costs, len(m.PERIODS)
                ):
                    lifetime = m.flows[i, o].investment.lifetime
                    age = m.flows[i, o].investment.age
                    range_limit = min(
                        m.es.end_year_of_optimization, lifetime - age
                    )
                    fixed_costs += sum(
                        m.flows[i, o].investment.existing
                        * m.flows[i, o].investment.fixed_costs[pp]
                        * (1 + m.discount_rate) ** (-pp)
                        for pp in range(range_limit)
                    )

        self.investment_costs = Expression(expr=investment_costs)
        self.period_investment_costs = period_investment_costs
        self.fixed_costs = Expression(expr=fixed_costs)
        self.costs = Expression(expr=investment_costs + fixed_costs)

        return self.costs

    def _evaluate_remaining_value_difference(
        self,
        m,
        p,
        i,
        o,
        end_year_of_optimization,
        lifetime,
        interest,
        nonconvex=False,
    ):
        """Evaluate and return the remaining value difference of an investment

        The remaining value difference in the net present values if the asset
        was to be liquidated at the end of the optimization horizon and the
        net present value using the original investment expenses.

        Parameters
        ----------
        m : oemof.solph.models.Model
            Optimization model

        p : int
            Period in which investment occurs

        i : any instance of oemof.solph.components
            start node of flow

        o : any instance of oemof.solph.components
            end node of flow

        end_year_of_optimization : int
            Last year of the optimization horizon

        lifetime : int
            lifetime of investment considered

        interest : float
            Demanded interest rate for investment

        nonconvex : bool
            Indicating whether considered flow is nonconvex.
        """
        if m.es.use_remaining_value:
            if end_year_of_optimization - m.es.periods_years[p] < lifetime:
                remaining_lifetime = lifetime - (
                    end_year_of_optimization - m.es.periods_years[p]
                )
                remaining_annuity = economics.annuity(
                    capex=m.flows[i, o].investment.ep_costs[-1],
                    n=remaining_lifetime,
                    wacc=interest,
                )
                original_annuity = economics.annuity(
                    capex=m.flows[i, o].investment.ep_costs[p],
                    n=remaining_lifetime,
                    wacc=interest,
                )
                present_value_factor_remaining = 1 / economics.annuity(
                    capex=1, n=remaining_lifetime, wacc=interest
                )
                convex_investment_costs = (
                    self.invest[i, o, p]
                    * (remaining_annuity - original_annuity)
                    * present_value_factor_remaining
                ) * (1 + m.discount_rate) ** (-end_year_of_optimization)
                if nonconvex:
                    return convex_investment_costs + self.invest_status[
                        i, o, p
                    ] * (
                        m.flows[i, o].investment.offset[-1]
                        - m.flows[i, o].investment.offset[p]
                    ) * (
                        1 + m.discount_rate
                    ) ** (
                        -end_year_of_optimization
                    )
                else:
                    return convex_investment_costs
            else:
                return 0
        else:
            return 0

    def _minimum_investment_constraint(self):
        """Constraint factory for a minimum investment"""
        m = self.parent_block()

        def _min_invest_rule(_):
            """Rule definition for applying a minimum investment"""
            for i, o in self.NON_CONVEX_INVESTFLOWS:
                for p in m.PERIODS:
                    expr = (
                        m.flows[i, o].investment.minimum[p]
                        * self.invest_status[i, o, p]
                        <= self.invest[i, o, p]
                    )
                    self.minimum_rule.add((i, o, p), expr)

        self.minimum_rule = Constraint(
            self.NON_CONVEX_INVESTFLOWS, m.PERIODS, noruleinit=True
        )
        self.minimum_rule_build = BuildAction(rule=_min_invest_rule)

        return self.minimum_rule

    def _maximum_investment_constraint(self):
        """Constraint factory for a maximum investment"""
        m = self.parent_block()

        def _max_invest_rule(_):
            """Rule definition for applying a minimum investment"""
            for i, o in self.NON_CONVEX_INVESTFLOWS:
                for p in m.PERIODS:
                    expr = self.invest[i, o, p] <= (
                        m.flows[i, o].investment.maximum[p]
                        * self.invest_status[i, o, p]
                    )
                    self.maximum_rule.add((i, o, p), expr)

        self.maximum_rule = Constraint(
            self.NON_CONVEX_INVESTFLOWS, m.PERIODS, noruleinit=True
        )
        self.maximum_rule_build = BuildAction(rule=_max_invest_rule)

        return self.maximum_rule
