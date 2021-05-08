# -*- coding: utf-8 -*-

"""Creating sets, variables, constraints and parts of the objective function
for Flow objects.

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

from pyomo.core import BuildAction
from pyomo.core import Constraint
from pyomo.core import NonNegativeIntegers
from pyomo.core import Set
from pyomo.core import Var
from pyomo.core.base.block import SimpleBlock


class MultiPeriodFlow(SimpleBlock):
    r""" Block for all flows with :attr:`multiperiod` being not None.

    **The following variables are created**:

    negative_gradient :
        Difference of a flow in consecutive timesteps if flow is reduced
        indexed by NEGATIVE_GRADIENT_FLOWS, TIMESTEPS.

    positive_gradient :
        Difference of a flow in consecutive timesteps if flow is increased
        indexed by NEGATIVE_GRADIENT_FLOWS, TIMESTEPS.

    **The following sets are created:** (-> see basic sets at :class:`.Model` )

    SUMMED_MAX_FLOWS
        A set of flows with the attribute :attr:`summed_max` being not None.
    SUMMED_MIN_FLOWS
        A set of flows with the attribute :attr:`summed_min` being not None.
    NEGATIVE_GRADIENT_FLOWS
        A set of flows with the attribute :attr:`negative_gradient` being not
        None.
    POSITIVE_GRADIENT_FLOWS
        A set of flows with the attribute :attr:`positive_gradient` being not
        None
    INTEGER_FLOWS
        A set of flows where the attribute :attr:`integer` is True (forces flow
        to only take integer values)

    **The following constraints are build:**

    Flow max sum :attr:`om.Flow.summed_max[i, o]`
      .. math::
        \sum_t flow(i, o, p, t) \cdot \tau
            \leq summed\_max(i, o) \cdot nominal\_value(i, o), \\
        \forall (i, o) \in \textrm{SUMMED\_MAX\_FLOWS}.

    Flow min sum :attr:`om.Flow.summed_min[i, o]`
      .. math::
        \sum_t flow(i, o, p, t) \cdot \tau
            \geq summed\_min(i, o) \cdot nominal\_value(i, o), \\
        \forall (i, o) \in \textrm{SUMMED\_MIN\_FLOWS}.

    Negative gradient constraint
      :attr:`om.Flow.negative_gradient_constr[i, o]`:
        .. math::
          flow(i, o, p, t-1) - flow(i, o, p, t) \geq \
          negative\_gradient(i, o, t), \\
          \forall (i, o) \in \textrm{NEGATIVE\_GRADIENT\_FLOWS}, \\
          \forall p, t \in \textrm{TIMEINDEX}.

    Positive gradient constraint
      :attr:`om.Flow.positive_gradient_constr[i, o]`:
        .. math:: flow(i, o, p, t) - flow(i, o, p, t-1) \geq \
          positive\__gradient(i, o, t), \\
          \forall (i, o) \in \textrm{POSITIVE\_GRADIENT\_FLOWS}, \\
          \forall p, t \in \textrm{TIMEINDEX}.

    **The following parts of the objective function are created:**

    If :attr:`variable_costs` are set by the user:
      .. math::
          \sum_{(i,o)} \sum_t flow(i, o, p, t) \cdot variable\_costs(i, o, t)

    The expression can be accessed by :attr:`om.Flow.variable_costs` and
    their value after optimization by :meth:`om.Flow.variable_costs()` .

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        r""" Creates sets, variables and constraints for all standard flows.

        Parameters
        ----------
        group : list
            List containing tuples containing flow (f) objects and the
            associated source (s) and target (t)
            of flow e.g. groups=[(s1, t1, f1), (s2, t2, f2),..]
        """
        if group is None:
            return None

        m = self.parent_block()

        # ########################## SETS #################################
        # set for all flows with an global limit on the flow over time
        self.SUMMED_MAX_FLOWS = Set(initialize=[
            (g[0], g[1]) for g in group
            if (g[2].summed_max is not None
                and g[2].nominal_value is not None)])

        self.SUMMED_MIN_FLOWS = Set(initialize=[
            (g[0], g[1]) for g in group
            if (g[2].summed_min is not None
                and g[2].nominal_value is not None)])

        self.NEGATIVE_GRADIENT_FLOWS = Set(
            initialize=[(g[0], g[1]) for g in group
                        if g[2].negative_gradient['ub'][0] is not None])

        self.POSITIVE_GRADIENT_FLOWS = Set(
            initialize=[(g[0], g[1]) for g in group
                        if g[2].positive_gradient['ub'][0] is not None])

        self.INTEGER_FLOWS = Set(
            initialize=[(g[0], g[1]) for g in group
                        if g[2].integer])
        # ######################### Variables  ################################

        self.positive_gradient = Var(self.POSITIVE_GRADIENT_FLOWS,
                                     m.TIMESTEPS)

        self.negative_gradient = Var(self.NEGATIVE_GRADIENT_FLOWS,
                                     m.TIMESTEPS)

        self.integer_flow = Var(self.INTEGER_FLOWS,
                                m.TIMEINDEX, within=NonNegativeIntegers)
        # set upper bound of gradient variable
        for i, o, f in group:
            if m.flows[i, o].positive_gradient['ub'][0] is not None:
                for t in m.TIMESTEPS:
                    self.positive_gradient[i, o, t].setub(
                        f.positive_gradient['ub'][t] * f.nominal_value)
            if m.flows[i, o].negative_gradient['ub'][0] is not None:
                for t in m.TIMESTEPS:
                    self.negative_gradient[i, o, t].setub(
                        f.negative_gradient['ub'][t] * f.nominal_value)

        # ######################### CONSTRAINTS ###############################

        def _flow_summed_max_rule(model):
            """Rule definition for build action of max. sum flow constraint.
            """
            for inp, out in self.SUMMED_MAX_FLOWS:
                lhs = sum(m.flow[inp, out, p, ts] * m.timeincrement[ts]
                          for p, ts in m.TIMEINDEX)
                rhs = (m.flows[inp, out].summed_max
                       * m.flows[inp, out].nominal_value)
                self.summed_max.add((inp, out), lhs <= rhs)

        self.summed_max = Constraint(self.SUMMED_MAX_FLOWS, noruleinit=True)
        self.summed_max_build = BuildAction(rule=_flow_summed_max_rule)

        def _flow_summed_min_rule(model):
            """Rule definition for build action of min. sum flow constraint.
            """
            for inp, out in self.SUMMED_MIN_FLOWS:
                lhs = sum(m.flow[inp, out, p, ts] * m.timeincrement[ts]
                          for p, ts in m.TIMEINDEX)
                rhs = (m.flows[inp, out].summed_min
                       * m.flows[inp, out].nominal_value)
                self.summed_min.add((inp, out), lhs >= rhs)

        self.summed_min = Constraint(self.SUMMED_MIN_FLOWS, noruleinit=True)
        self.summed_min_build = BuildAction(rule=_flow_summed_min_rule)

        def _positive_gradient_flow_rule(model):
            """Rule definition for positive gradient constraint.
            """
            for inp, out in self.POSITIVE_GRADIENT_FLOWS:
                for p, ts in m.TIMEINDEX:
                    if ts > 0:
                        lhs = (m.flow[inp, out, p, ts]
                               - m.flow[inp, out, p, ts - 1])
                        rhs = self.positive_gradient[inp, out, ts]
                        self.positive_gradient_constr.add((inp, out, p, ts),
                                                          lhs <= rhs)
                    else:
                        pass  # return(Constraint.Skip)

        self.positive_gradient_constr = Constraint(
            self.POSITIVE_GRADIENT_FLOWS, m.TIMEINDEX, noruleinit=True)
        self.positive_gradient_build = BuildAction(
            rule=_positive_gradient_flow_rule)

        def _negative_gradient_flow_rule(model):
            """Rule definition for negative gradient constraint.
            """
            for inp, out in self.NEGATIVE_GRADIENT_FLOWS:
                for p, ts in m.TIMEINDEX:
                    if ts > 0:
                        lhs = (m.flow[inp, out, p, ts - 1]
                               - m.flow[inp, out, p, ts])
                        rhs = self.negative_gradient[inp, out, ts]
                        self.negative_gradient_constr.add((inp, out, p, ts),
                                                          lhs <= rhs)
                    else:
                        pass  # return(Constraint.Skip)

        self.negative_gradient_constr = Constraint(
            self.NEGATIVE_GRADIENT_FLOWS, m.TIMEINDEX, noruleinit=True)
        self.negative_gradient_build = BuildAction(
            rule=_negative_gradient_flow_rule)

        def _integer_flow_rule(block, ii, oi, pi, ti):
            """Force flow variable to NonNegativeInteger values.
            """
            return self.integer_flow[ii, oi, pi, ti] == m.flow[ii, oi, pi, ti]

        self.integer_flow_constr = Constraint(self.INTEGER_FLOWS, m.TIMEINDEX,
                                              rule=_integer_flow_rule)

    def _objective_expression(self):
        r""" Objective expression for all standard flows with fixed costs
        and variable costs.

        Note that fixed costs for dispatch only plants are not
        decision-relevant, i.e. do not influence the model choices. They
        are only added to the objective function value.
        """
        m = self.parent_block()

        variable_costs = 0
        gradient_costs = 0
        fixed_costs = 0

        for i, o in m.FLOWS:
            if m.flows[i, o].variable_costs[0] is not None:
                for p, t in m.TIMEINDEX:
                    variable_costs += (m.flow[i, o, p, t]
                                       * m.objective_weighting[t]
                                       * m.flows[i, o].variable_costs[p]
                                       * ((1 + m.discount_rate) ** -p))

            if m.flows[i, o].positive_gradient['ub'][0] is not None:
                for p, t in m.TIMEINDEX:
                    gradient_costs += (self.positive_gradient[i, o, t]
                                       * m.flows[i, o].positive_gradient[
                                           'costs']
                                       * ((1 + m.discount_rate) ** -p))

            if m.flows[i, o].negative_gradient['ub'][0] is not None:
                for p, t in m.TIMEINDEX:
                    gradient_costs += (self.negative_gradient[i, o, t]
                                       * m.flows[i, o].negative_gradient[
                                           'costs']
                                       * ((1 + m.discount_rate) ** -p))

            if (m.flows[i, o].fixed_costs[0] is not None
                    and m.flows[i, o].nominal_value is not None):
                for p in m.PERIODS:
                    fixed_costs += (m.flows[i, o].nominal_value
                                    * m.flows[i, o].fixed_costs[p]
                                    * ((1 + m.discount_rate) ** -p))

        return variable_costs + gradient_costs + fixed_costs
