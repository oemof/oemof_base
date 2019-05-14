# -*- coding: utf-8 -*-

"""Creating sets, variables, constraints and parts of the objective function
for the specified groups.

This file is part of project oemof (github.com/oemof/oemof). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location oemof/oemof/solph/blocks.py

SPDX-License-Identifier: GPL-3.0-or-later
"""

from pyomo.core import (Var, Set, Constraint, BuildAction, Expression,
                        NonNegativeReals, Binary, NonNegativeIntegers)
from pyomo.core.base.block import SimpleBlock


class Flow(SimpleBlock):
    r""" Flow block with definitions for standard flows.

    **The following variables are created**:

    negative_gradient :
        Difference of a flow in consecutive timesteps if flow is reduced
        indexed by NEGATIVE_GRADIENT_FLOWS, TIMESTEPS.

    positive_gradient :
        Difference of a flow in consecutive timesteps if flow is increased
        indexed by NEGATIVE_GRADIENT_FLOWS, TIMESTEPS.

    **The following sets are created:** (-> see basic sets at
    :class:`.Model` )

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
        A set of flows wher the attribute :attr:`integer` is True (forces flow
        to only take integer values)

    **The following constraints are build:**

    Flow max sum :attr:`om.Flow.summed_max[i, o]`
      .. math::
        \sum_t flow(i, o, t) \cdot \tau
            \leq summed\_max(i, o) \cdot nominal\_value(i, o), \\
        \forall (i, o) \in \textrm{SUMMED\_MAX\_FLOWS}.

    Flow min sum :attr:`om.Flow.summed_min[i, o]`
      .. math::
        \sum_t flow(i, o, t) \cdot \tau
            \geq summed\_min(i, o) \cdot nominal\_value(i, o), \\
        \forall (i, o) \in \textrm{SUMMED\_MIN\_FLOWS}.

    Negative gradient constraint :attr:`om.Flow.negative_gradient_constr[i, o]`:
      .. math:: flow(i, o, t-1) - flow(i, o, t) \geq \
        negative\_gradient(i, o, t), \\
        \forall (i, o) \in \textrm{NEGATIVE\_GRADIENT\_FLOWS}, \\
        \forall t \in \textrm{TIMESTEPS}.

    Positive gradient constraint :attr:`om.Flow.positive_gradient_constr[i, o]`:
        .. math:: flow(i, o, t) - flow(i, o, t-1) \geq \
            positive\__gradient(i, o, t), \\
            \forall (i, o) \in \textrm{POSITIVE\_GRADIENT\_FLOWS}, \\
            \forall t \in \textrm{TIMESTEPS}.

    **The following parts of the objective function are created:**

    If :attr:`variable_costs` are set by the user:
        .. math::
            \sum_{(i,o)} \sum_t flow(i, o, t) \cdot variable\_costs(i, o, t)

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
            (g[0], g[1]) for g in group if g[2].summed_max is not None and
            g[2].nominal_value is not None])

        self.SUMMED_MIN_FLOWS = Set(initialize=[
            (g[0], g[1]) for g in group if g[2].summed_min is not None and
            g[2].nominal_value is not None])

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
                                m.TIMESTEPS, within=NonNegativeIntegers)
        # set upper bound of gradient variable
        for i, o, f in group:
            if m.flows[i, o].positive_gradient['ub'][0] is not None:
                m.report['variables']['positive_gradient'] = {
                    'upper bound':
                        'pg_{i,o,t} \leq edge^{pg}_{i,o,t} \cdot edge^{nv}'}
                for t in m.TIMESTEPS:
                    self.positive_gradient[i, o, t].setub(
                        f.positive_gradient['ub'][t] * f.nominal_value)
            if m.flows[i, o].negative_gradient['ub'][0] is not None:
                m.report['variables']['negative_gradient'] = {
                    'upper bound':
                        'ng_{i,o,t} \ļeq edge^{ng}_{i,o,t} \cdot edge^{nv}'}
                for t in m.TIMESTEPS:
                    self.negative_gradient[i, o, t].setub(
                        f.negative_gradient['ub'][t] * f.nominal_value)

        # ######################### CONSTRAINTS ###############################

        def _flow_summed_max_rule(model):
            """Rule definition for build action of max. sum flow constraint.
            """
            for inp, out in self.SUMMED_MAX_FLOWS:
                lhs = sum(m.flow[inp, out, ts] * m.timeincrement[ts]
                          for ts in m.TIMESTEPS)
                rhs = (m.flows[inp, out].summed_max *
                       m.flows[inp, out].nominal_value)
                self.summed_max.add((inp, out), lhs <= rhs)
        self.summed_max = Constraint(self.SUMMED_MAX_FLOWS, noruleinit=True)
        if self.SUMMED_MAX_FLOWS:
            m.report['constraints']['summed max'] = (
                    r'flow_{i,o,t} \cdot \tau \leq edge^{smax}_{i,o} \cdot '
                    'edge_^{nv}_{i,o}')
        self.summed_max_build = BuildAction(rule=_flow_summed_max_rule)

        def _flow_summed_min_rule(model):
            """Rule definition for build action of min. sum flow constraint.
            """
            for inp, out in self.SUMMED_MIN_FLOWS:
                lhs = sum(m.flow[inp, out, ts] * m.timeincrement[ts]
                          for ts in m.TIMESTEPS)
                rhs = (m.flows[inp, out].summed_min *
                       m.flows[inp, out].nominal_value)
                self.summed_min.add((inp, out), lhs >= rhs)
        self.summed_min = Constraint(self.SUMMED_MIN_FLOWS, noruleinit=True)
        if self.SUMMED_MIN_FLOWS:
            m.report['constraints']['summed min'] = (
                    r'flow_{i,o,t} \cdot \tau \geq edge^{smin}_{i,o} \cdot '
                    'edge_^{nv}_{i,o}')
            self.summed_min_build = BuildAction(rule=_flow_summed_min_rule)

        def _positive_gradient_flow_rule(model):
            """Rule definition for positive gradient constraint.
            """
            for inp, out in self.POSITIVE_GRADIENT_FLOWS:
                for ts in m.TIMESTEPS:
                    if ts > 0:
                        lhs = m.flow[inp, out, ts] - m.flow[inp, out, ts-1]
                        rhs = self.positive_gradient[inp, out, ts]
                        self.positive_gradient_constr.add((inp, out, ts),
                                                          lhs <= rhs)
                    else:
                        pass  # return(Constraint.Skip)
        if self.POSITIVE_GRADIENT_FLOWS:
            self.positive_gradient_constr = Constraint(
                self.POSITIVE_GRADIENT_FLOWS, m.TIMESTEPS, noruleinit=True)
            m.report['constraints']['positive gradient'] = (
                    'pg_{i,o,t} \geq flow_{i,o,t} - flow_{i,o,t-1}')
            self.positive_gradient_build = BuildAction(
                rule=_positive_gradient_flow_rule)

        def _negative_gradient_flow_rule(model):
            """Rule definition for negative gradient constraint.
            """
            for inp, out in self.NEGATIVE_GRADIENT_FLOWS:
                for ts in m.TIMESTEPS:
                    if ts > 0:
                        lhs = m.flow[inp, out, ts-1] - m.flow[inp, out, ts]
                        rhs = self.negative_gradient[inp, out, ts]
                        self.negative_gradient_constr.add((inp, out, ts),
                                                          lhs <= rhs)
                    else:
                        pass  # return(Constraint.Skip)
        if self.NEGATIVE_GRADIENT_FLOWS:
            self.negative_gradient_constr = Constraint(
                self.NEGATIVE_GRADIENT_FLOWS, m.TIMESTEPS, noruleinit=True)
            m.report['constraints']['negative gradient'] = (
                'ng_{i,o,t} \geq flow_{i,o,t-1} - flow_{i,o,t}')
            self.negative_gradient_build = BuildAction(
                rule=_negative_gradient_flow_rule)

        def _integer_flow_rule(block, i, o, t):
            """Force flow variable to NonNegativeInteger values.
            """
            return self.integer_flow[i, o, t] == m.flow[i, o, t]
        if self.INTEGER_FLOWS:
            m.report['constraints']['integer flow'] = (
                'flow_{i,o,t} = integer_flow_{i,o,t}')
            self.integer_flow_constr = Constraint(self.INTEGER_FLOWS, m.TIMESTEPS,
                                                  rule=_integer_flow_rule)

    def _objective_expression(self):
        r""" Objective expression for all standard flows with fixed costs
        and variable costs.
        """
        m = self.parent_block()

        variable_costs = 0
        gradient_costs = 0

        for i, o in m.FLOWS:
            if m.flows[i, o].variable_costs[0] is not None:
                m.report['objective']['variable costs'] = (
                    '\sum_{i,o \in F} \sum_{t \in T} flow_{i,o,t} \cdot '
                    r'\tau^{obj} \cdot edge^{cvar}_{i,o,t}')
                for t in m.TIMESTEPS:
                    variable_costs += (m.flow[i, o, t] * m.objective_weighting[t] *
                                       m.flows[i, o].variable_costs[t])

            if m.flows[i, o].positive_gradient['ub'][0] is not None:
                m.report['objective']['positive gradient costs'] = (
                    '\sum_{i,o \in F} \sum_{t \in T} pg_{i,o,t} \cdot '
                    'edge^{pg,cost}_{i,o}')
                for t in m.TIMESTEPS:
                    gradient_costs += (self.positive_gradient[i, o, t] *
                                       m.flows[i, o].positive_gradient[
                                           'costs'])

            if m.flows[i, o].negative_gradient['ub'][0] is not None:
                m.report['objective']['negative gradient costs'] = (
                    '\sum_{i,o \in F} \sum_{t \in T} ng_{i,o,t} \cdot '
                    'edge^{ng,cost}_{i,o}')
                for t in m.TIMESTEPS:
                    gradient_costs += (self.negative_gradient[i, o, t] *
                                       m.flows[i, o].negative_gradient[
                                           'costs'])

        return variable_costs + gradient_costs


class InvestmentFlow(SimpleBlock):
    r"""Block for all flows with :attr:`investment` being not None.

    **The following sets are created:** (-> see basic sets at
    :class:`.Model` )

    FLOWS
        A set of flows with the attribute :attr:`invest` of type
        :class:`.options.Investment`.
    FIXED_FLOWS
        A set of flow with the attribute :attr:`fixed` set to `True`
    SUMMED_MAX_FLOWS
        A subset of set FLOWS with flows with the attribute :attr:`summed_max`
        being not None.
    SUMMED_MIN_FLOWS
        A subset of set FLOWS with flows with the attribute
        :attr:`summed_min` being not None.
    MIN_FLOWS
        A subset of FLOWS with flows having set a value of not None in the
        first timestep.

    **The following variables are created:**

    invest :attr:`om.InvestmentFlow.invest[i, o]`
        Value of the investment variable i.e. equivalent to the nominal
        value of the flows after optimization (indexed by FLOWS)

    **The following constraints are build:**

    Actual value constraint for fixed invest
      flows :attr:`om.InvestmentFlow.fixed[i, o, t]`
        .. math::
          flow(i, o, t) = actual\_value(i, o, t) \cdot invest(i, o), \\
          \forall (i, o) \in \textrm{FIXED\_FLOWS}, \\
          \forall t \in \textrm{TIMESTEPS}.

    Lower bound (min) constraint for invest flows
      :attr:`om.InvestmentFlow.min[i, o, t]`
        .. math::
             flow(i, o, t) \geq min(i, o, t) \cdot invest(i, o), \\
             \forall (i, o) \in \textrm{MIN\_FLOWS}, \\
             \forall t \in \textrm{TIMESTEPS}.

    Upper bound (max) constraint for invest flows
      :attr:`om.InvestmentFlow.max[i, o, t]`
        .. math::
             flow(i, o, t) \leq max(i, o, t) \cdot invest(i, o), \\
             \forall (i, o) \in \textrm{FLOWS}, \\
             \forall t \in \textrm{TIMESTEPS}.

    Flow max sum for invest flow
      :attr:`om.InvestmentFlow.summed_max[i, o]`
        .. math::
            \sum_t flow(i, o, t) \cdot \tau \leq summed\_max(i, o) \
            \cdot invest(i, o) \\
            \forall (i, o) \in \textrm{SUMMED\_MAX\_FLOWS}.

    Flow min sum for invest flow :attr:`om.InvestmentFlow.summed_min[i, o]`
        .. math::
            \sum_t flow(i, o, t) \cdot \tau \geq summed\_min(i, o) \
            \cdot invest(i, o) \\
            \forall (i, o) \in \textrm{SUMMED\_MIN\_FLOWS}.


    **The following parts of the objective function are created:**

    Equivalent periodical costs (epc) expression
      :attr:`om.InvestmentFlow.investment_costs`:
        .. math::
            \sum_{i, o} invest(i, o) \cdot ep\_costs(i, o)

    The expression can be accessed by :attr:`om.InvestmentFlow.variable_costs`
    and their value after optimization by
    :meth:`om.InvestmentFlow.variable_costs()` . This works similar for
    investment costs with :attr:`*.investment_costs` etc.
    """

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
        self.FLOWS = Set(initialize=[(g[0], g[1]) for g in group])

        self.FIXED_FLOWS = Set(
            initialize=[(g[0], g[1]) for g in group if g[2].fixed])

        self.SUMMED_MAX_FLOWS = Set(initialize=[
            (g[0], g[1]) for g in group if g[2].summed_max is not None])

        self.SUMMED_MIN_FLOWS = Set(initialize=[
            (g[0], g[1]) for g in group if g[2].summed_min is not None])

        self.MIN_FLOWS = Set(initialize=[
            (g[0], g[1]) for g in group if (
                g[2].min[0] != 0 or len(g[2].min) > 1)])

        # ######################### VARIABLES #################################
        def _investvar_bound_rule(block, i, o):
            """Rule definition for bounds of invest variable.
            """
            return (m.flows[i, o].investment.minimum,
                    m.flows[i, o].investment.maximum)
        # create variable bounded for flows with investement attribute
        if self.FLOWS:
            m.report['variables']['investment'] = {
                'ub': 'investment_{i,o} \leq edge^{inv,max}_{i,o}',
                'lb': 'investment_{i,o} \geq edge^{inv,min}_{i,o}'}
            self.invest = Var(self.FLOWS, within=NonNegativeReals,
                              bounds=_investvar_bound_rule)

        # ######################### CONSTRAINTS ###############################

        # TODO: Add gradient constraints

        def _investflow_fixed_rule(block, i, o, t):
            """Rule definition of constraint to fix flow variable
            of investment flow to (normed) actual value
            """
            return (m.flow[i, o, t] == (
                (m.flows[i, o].investment.existing + self.invest[i, o]) *
                 m.flows[i, o].actual_value[t]))
        if self.FIXED_FLOWS:
            m.report['variables']['flow'].update({
                'value': (
                    'flow_{i,o,t} = edge^{inv,exist} + investment_{i,o} \cdot '
                    r'edge^{av}_{i,o,t} \forall (i,o) \in F_{I,fix}')})
            self.fixed = Constraint(self.FIXED_FLOWS, m.TIMESTEPS,
                                    rule=_investflow_fixed_rule)

        def _max_investflow_rule(block, i, o, t):
            """Rule definition of constraint setting an upper bound of flow
            variable in investment case.
            """
            expr = (m.flow[i, o, t] <= (
                (m.flows[i, o].investment.existing + self.invest[i, o]) *
                 m.flows[i, o].max[t]))
            return expr
        if self.FLOWS:
            m.report['variables']['flow'].update({
                'upper bound contr': (
                    'flow_{i,o,t} \leq edge^{inv,exist} + investment_{i,o} '
                    r'\cdot edge^{max}_{i,o,t} \forall (i,o) \in F_I')})
            self.max = Constraint(self.FLOWS, m.TIMESTEPS,
                                  rule=_max_investflow_rule)

        def _min_investflow_rule(block, i, o, t):
            """Rule definition of constraint setting a lower bound on flow
            variable in investment case.
            """
            expr = (m.flow[i, o, t] >= (
                (m.flows[i, o].investment.existing + self.invest[i, o]) *
                 m.flows[i, o].min[t]))
            return expr
        self.min = Constraint(self.MIN_FLOWS, m.TIMESTEPS,
                              rule=_min_investflow_rule)

        def _summed_max_investflow_rule(block, i, o):
            """Rule definition for build action of max. sum flow constraint
            in investment case.
            """
            expr = (sum(m.flow[i, o, t] * m.timeincrement[t]
                        for t in m.TIMESTEPS) <=
                    m.flows[i, o].summed_max * (
                        self.invest[i, o] + m.flows[i, o].investment.existing))
            return expr
        self.summed_max = Constraint(self.SUMMED_MAX_FLOWS,
                                     rule=_summed_max_investflow_rule)

        def _summed_min_investflow_rule(block, i, o):
            """Rule definition for build action of min. sum flow constraint
            in investment case.
            """
            expr = (sum(m.flow[i, o, t] * m.timeincrement[t]
                        for t in m.TIMESTEPS) >=
                    ((m.flows[i, o].investment.existing + self.invest[i, o]) *
                     m.flows[i, o].summed_min))
            return expr
        self.summed_min = Constraint(self.SUMMED_MIN_FLOWS,
                                     rule=_summed_min_investflow_rule)

    def _objective_expression(self):
        r""" Objective expression for flows with investment attribute of type
        class:`.Investment`. The returned costs are fixed, variable and
        investment costs.
        """
        if not hasattr(self, 'FLOWS'):
            return 0

        m = self.parent_block()
        investment_costs = 0

        for i, o in self.FLOWS:
            if m.flows[i, o].investment.ep_costs is not None:
                investment_costs += (self.invest[i, o] *
                                     m.flows[i, o].investment.ep_costs)
            else:
                raise ValueError("Missing value for investment costs!")

        self.investment_costs = Expression(expr=investment_costs)
        return investment_costs


class Bus(SimpleBlock):
    r"""Block for all balanced buses.

    **The following constraints are build:**

    Bus balance  :attr:`om.Bus.balance[i, o, t]`
      .. math::
        \sum_{i \in INPUTS(n)} flow(i, n, t) \cdot \tau =
        \sum_{o \in OUTPUTS(n)} flow(n, o, t) \cdot \tau, \\
        \forall n \in \textrm{BUSES},
        \forall t \in \textrm{TIMESTEPS}.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """Creates the balance constraints for the class:`Bus` block.

        Parameters
        ----------
        group : list
            List of oemof bus (b) object for which the bus balance is created
            e.g. group = [b1, b2, b3, .....]
        """
        if group is None:
            return None

        m = self.parent_block()

        I = {}
        O = {}
        for n in group:
            I[n] = [i for i in n.inputs]
            O[n] = [o for o in n.outputs]

        def _busbalance_rule(block):
            for t in m.TIMESTEPS:
                for n in group:
                    lhs = sum(m.flow[i, n, t] * m.timeincrement[t]
                              for i in I[n])
                    rhs = sum(m.flow[n, o, t] * m.timeincrement[t]
                              for o in O[n])
                    expr = (lhs == rhs)
                    # no inflows no outflows yield: 0 == 0 which is True
                    if expr is not True:
                        block.balance.add((n, t), expr)
        self.balance = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.balance_build = BuildAction(rule=_busbalance_rule)


class Transformer(SimpleBlock):
    r"""Block for the linear relation of nodes with type
    :class:`~oemof.solph.network.Transformer`

    **The following sets are created:** (-> see basic sets at
    :class:`.Model` )

    TRANSFORMERS
        A set with all :class:`~oemof.solph.network.Transformer` objects.

    **The following constraints are created:**

    Linear relation :attr:`om.Transformer.relation[i,o,t]`
        .. math::
            flow(i, n, t) / conversion\_factor(n, i, t) = \
            flow(n, o, t) / conversion\_factor(n, o, t), \\
            \forall t \in \textrm{TIMESTEPS}, \\
            \forall n \in \textrm{TRANSFORMERS}, \\
            \forall i \in \textrm{INPUTS(n)}, \\
            \forall o \in \textrm{OUTPUTS(n)}.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """ Creates the linear constraint for the class:`Transformer`
        block.
        Parameters
        ----------
        group : list
            List of oemof.solph.Transformers objects for which
            the linear relation of inputs and outputs is created
            e.g. group = [trsf1, trsf2, trsf3, ...]. Note that the relation
            is created for all existing relations of all inputs and all outputs
            of the transformer. The components inside the list need to hold
            an attribute `conversion_factors` of type dict containing the
            conversion factors for all inputs to outputs.
        """
        if group is None:
            return None

        m = self.parent_block()

        in_flows = {n: [i for i in n.inputs.keys()] for n in group}
        out_flows = {n: [o for o in n.outputs.keys()] for n in group}


        self.relation = Constraint(
            [(n, i, o, t)
             for t in m.TIMESTEPS
             for n in group
             for o in out_flows[n]
             for i in in_flows[n]], noruleinit=True)

        def _input_output_relation(block):
            for t in m.TIMESTEPS:
                for n in group:
                    for o in out_flows[n]:
                        for i in in_flows[n]:
                            try:
                                lhs = (m.flow[i, n, t] /
                                       n.conversion_factors[i][t])
                                rhs = (m.flow[n, o, t] /
                                       n.conversion_factors[o][t])
                            except ValueError:
                                raise ValueError(
                                    "Error in constraint creation",
                                    "source: {0}, target: {1}".format(
                                        n.label, o.label))
                            block.relation.add((n, i, o, t), (lhs == rhs))
        self.relation_build = BuildAction(rule=_input_output_relation)


class NonConvexFlow(SimpleBlock):
    r"""
    **The following sets are created:** (-> see basic sets at
        :class:`.Model` )

    A set of flows with the attribute :attr:`nonconvex` of type
        :class:`.options.NonConvex`.
    MIN_FLOWS
        A subset of set NONCONVEX_FLOWS with the attribute :attr:`min`
        being not None in the first timestep
    STARTUP_FLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        :attr:`startup_costs` being not None.
    SHUTDOWN_FLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        :attr:`shutdown_costs` being not None.
    ACTIVE_FLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        :attr:`activity_costs` being not None.

    MINUPTIMEFLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        :attr:`minimum_uptime` being not None.

    MINDOWNTIMEFLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        :attr:`minimum_downtime` being not None.

    **The following variables are created:**

    Status variable (binary) :attr:`om.NonConvexFlow.status`:
        Variable indicating if flow is >= 0 indexed by FLOWS

    Startup variable (binary) :attr:`om.NonConvexFlow.startup`:
        Variable indicating startup of flow (component) indexed by
        STARTUP_FLOWS

    Shutdown variable (binary) :attr:`om.NonConvexFlow.shutdown`:
        Variable indicating shutdown of flow (component) indexed by
        SHUTDOWN_FLOWS

    **The following constraints are created**:

    Minimum flow constraint :attr:`om.NonConvexFlow.min[i,o,t]`
        .. math::
            flow(i, o, t) \geq min(i, o, t) \cdot nominal\_value \
                \cdot status(i, o, t), \\
            \forall t \in \textrm{TIMESTEPS}, \\
            \forall (i, o) \in \textrm{NONCONVEX\_FLOWS}.

    Maximum flow constraint :attr:`om.NonConvexFlow.max[i,o,t]`
        .. math::
            flow(i, o, t) \leq max(i, o, t) \cdot nominal\_value \
                \cdot status(i, o, t), \\
            \forall t \in \textrm{TIMESTEPS}, \\
            \forall (i, o) \in \textrm{NONCONVEX\_FLOWS}.

    Startup constraint :attr:`om.NonConvexFlow.startup_constr[i,o,t]`
        .. math::
            startup(i, o, t) \geq \
                status(i,o,t) - status(i, o, t-1) \\
            \forall t \in \textrm{TIMESTEPS}, \\
            \forall (i,o) \in \textrm{STARTUP\_FLOWS}.

    Shutdown constraint :attr:`om.NonConvexFlow.shutdown_constr[i,o,t]`
        .. math::
            shutdown(i, o, t) \geq \
                status(i, o, t-1) - status(i, o, t) \\
            \forall t \in \textrm{TIMESTEPS}, \\
            \forall (i, o) \in \textrm{SHUTDOWN\_FLOWS}.

    Minimum uptime constraint :attr:`om.NonConvexFlow.uptime_constr[i,o,t]`
        .. math::
            (status(i, o, t)-status(i, o, t-1)) \cdot minimum\_uptime(i, o) \\
            \leq \sum_{n=0}^{minimum\_uptime-1} status(i,o,t+n) \\
            \forall t \in \textrm{TIMESTEPS} | \\
            t \neq \{0..minimum\_uptime\} \cup \
            \{t\_max-minimum\_uptime..t\_max\} , \\
            \forall (i,o) \in \textrm{MINUPTIME\_FLOWS}.
            \\ \\
            status(i, o, t) = initial\_status(i, o) \\
            \forall t \in \textrm{TIMESTEPS} | \\
            t = \{0..minimum\_uptime\} \cup \
            \{t\_max-minimum\_uptime..t\_max\} , \\
            \forall (i,o) \in \textrm{MINUPTIME\_FLOWS}.

    Minimum downtime constraint :attr:`om.NonConvexFlow.downtime_constr[i,o,t]`
        .. math::
            (status(i, o, t-1)-status(i, o, t)) \
            \cdot minimum\_downtime(i, o) \\
            \leq minimum\_downtime(i, o) \
            - \sum_{n=0}^{minimum\_downtime-1} status(i,o,t+n) \\
            \forall t \in \textrm{TIMESTEPS} | \\
            t \neq \{0..minimum\_downtime\} \cup \
            \{t\_max-minimum\_downtime..t\_max\} , \\
            \forall (i,o) \in \textrm{MINDOWNTIME\_FLOWS}.
            \\ \\
            status(i, o, t) = initial\_status(i, o) \\
            \forall t \in \textrm{TIMESTEPS} | \\
            t = \{0..minimum\_downtime\} \cup \
            \{t\_max-minimum\_downtime..t\_max\} , \\
            \forall (i,o) \in \textrm{MINDOWNTIME\_FLOWS}.

    **The following parts of the objective function are created:**

    If :attr:`nonconvex.startup_costs` is set by the user:
        .. math::
            \sum_{i, o \in STARTUP\_FLOWS} \sum_t  startup(i, o, t) \
            \cdot startup\_costs(i, o)

    If :attr:`nonconvex.shutdown_costs` is set by the user:
        .. math::
            \sum_{i, o \in SHUTDOWN\_FLOWS} \sum_t shutdown(i, o, t) \
                \cdot shutdown\_costs(i, o)

    If :attr:`nonconvex.activity_costs` is set by the user:
        .. math::
            \sum_{i, o \in ACTIVE\_FLOWS} \sum_t status(i, o, t) \
                \cdot activity\_costs(i, o)

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """ Creates set, variables, constraints for all flow object with
        an attribute flow of type class:`.NonConvexFlow`.

        Parameters
        ----------
        group : list
            List of oemof.solph.NonConvexFlow objects for which
            the constraints are build.
        """
        if group is None:
            return None

        m = self.parent_block()
        # ########################## SETS #####################################
        self.NONCONVEX_FLOWS = Set(initialize=[(g[0], g[1]) for g in group])

        self.MIN_FLOWS = Set(initialize=[(g[0], g[1]) for g in group
                                         if g[2].min[0] is not None])

        self.STARTUPFLOWS = Set(initialize=[(g[0], g[1]) for g in group
                                if g[2].nonconvex.startup_costs[0]
                                is not None])

        self.SHUTDOWNFLOWS = Set(initialize=[(g[0], g[1]) for g in group
                                 if g[2].nonconvex.shutdown_costs[0]
                                 is not None])

        self.MINUPTIMEFLOWS = Set(initialize=[(g[0], g[1]) for g in group
                                  if g[2].nonconvex.minimum_uptime
                                  is not None])

        self.MINDOWNTIMEFLOWS = Set(initialize=[(g[0], g[1]) for g in group
                                    if g[2].nonconvex.minimum_downtime
                                    is not None])

        self.ACTIVE_FLOWS = Set(initialize=[(g[0], g[1]) for g in group
                                 if g[2].nonconvex.activity_costs[0]
                                 is not None])

        # ################### VARIABLES AND CONSTRAINTS #######################
        self.status = Var(self.NONCONVEX_FLOWS, m.TIMESTEPS, within=Binary)

        if self.STARTUPFLOWS:
            self.startup = Var(self.STARTUPFLOWS, m.TIMESTEPS, within=Binary)
        if self.SHUTDOWNFLOWS:
            self.shutdown = Var(self.SHUTDOWNFLOWS, m.TIMESTEPS, within=Binary)

        def _minimum_flow_rule(block, i, o, t):
            """Rule definition for MILP minimum flow constraints.
            """
            expr = (self.status[i, o, t] *
                    m.flows[i, o].min[t] * m.flows[i, o].nominal_value <=
                    m.flow[i, o, t])
            return expr
        self.min = Constraint(self.MIN_FLOWS, m.TIMESTEPS,
                              rule=_minimum_flow_rule)

        def _maximum_flow_rule(block, i, o, t):
            """Rule definition for MILP maximum flow constraints.
            """
            expr = (self.status[i, o, t] *
                    m.flows[i, o].max[t] * m.flows[i, o].nominal_value >=
                    m.flow[i, o, t])
            return expr
        self.max = Constraint(self.MIN_FLOWS, m.TIMESTEPS,
                              rule=_maximum_flow_rule)

        def _startup_rule(block, i, o, t):
            """Rule definition for startup constraint of nonconvex flows.
            """
            if t > m.TIMESTEPS[1]:
                expr = (self.startup[i, o, t] >= self.status[i, o, t] -
                        self.status[i, o, t-1])
            else:
                expr = (self.startup[i, o, t] >= self.status[i, o, t] -
                        m.flows[i, o].nonconvex.initial_status)
            return expr
        self.startup_constr = Constraint(self.STARTUPFLOWS, m.TIMESTEPS,
                                         rule=_startup_rule)

        def _shutdown_rule(block, i, o, t):
            """Rule definition for shutdown constraints of nonconvex flows.
            """
            if t > m.TIMESTEPS[1]:
                expr = (self.shutdown[i, o, t] >= self.status[i, o, t-1] -
                        self.status[i, o, t])
            else:
                expr = (self.shutdown[i, o, t] >=
                        m.flows[i, o].nonconvex.initial_status -
                        self.status[i, o, t])
            return expr
        self.shutdown_constr = Constraint(self.SHUTDOWNFLOWS, m.TIMESTEPS,
                                          rule=_shutdown_rule)

        def _min_uptime_rule(block, i, o, t):
            """Rule definition for min-uptime constraints of nonconvex flows.
            """
            if (t >= m.flows[i, o].nonconvex.max_up_down and
                    t <= m.TIMESTEPS[-1]-m.flows[i, o].nonconvex.max_up_down):
                expr = 0
                expr += ((self.status[i, o, t]-self.status[i, o, t-1]) *
                         m.flows[i, o].nonconvex.minimum_uptime)
                expr += -sum(self.status[i, o, t+u] for u in range(0,
                             m.flows[i, o].nonconvex.minimum_uptime))
                return expr <= 0
            else:
                expr = 0
                expr += self.status[i, o, t]
                expr += -m.flows[i, o].nonconvex.initial_status
                return expr == 0
        self.min_uptime_constr = Constraint(
            self.MINUPTIMEFLOWS, m.TIMESTEPS, rule=_min_uptime_rule)

        def _min_downtime_rule(block, i, o, t):
            """Rule definition for min-downtime constraints of nonconvex flows.
            """
            if (t >= m.flows[i, o].nonconvex.max_up_down and
                    t <= m.TIMESTEPS[-1]-m.flows[i, o].nonconvex.max_up_down):
                expr = 0
                expr += ((self.status[i, o, t-1]-self.status[i, o, t]) *
                         m.flows[i, o].nonconvex.minimum_downtime)
                expr += - m.flows[i, o].nonconvex.minimum_downtime
                expr += sum(self.status[i, o, t+d] for d in range(0,
                            m.flows[i, o].nonconvex.minimum_downtime))
                return expr <= 0
            else:
                expr = 0
                expr += self.status[i, o, t]
                expr += -m.flows[i, o].nonconvex.initial_status
                return expr == 0
        self.min_downtime_constr = Constraint(
            self.MINDOWNTIMEFLOWS, m.TIMESTEPS, rule=_min_downtime_rule)

        # TODO: Add gradient constraints for nonconvex block / flows

    def _objective_expression(self):
        r"""Objective expression for nonconvex flows.
        """
        if not hasattr(self, 'NONCONVEX_FLOWS'):
            return 0

        m = self.parent_block()

        startcosts = 0
        shutdowncosts = 0
        activitycosts = 0

        if self.STARTUPFLOWS:
            for i, o in self.STARTUPFLOWS:
                if (m.flows[i, o].nonconvex.startup_costs[0] is not None):
                    startcosts += sum(self.startup[i, o, t] *
                                      m.flows[i, o].nonconvex.startup_costs[t]
                                      for t in m.TIMESTEPS)
            self.startcosts = Expression(expr=startcosts)

        if self.SHUTDOWNFLOWS:
            for i, o in self.SHUTDOWNFLOWS:
                if (m.flows[i, o].nonconvex.shutdown_costs[0] is not None):
                    shutdowncosts += sum(
                        self.shutdown[i, o, t] *
                        m.flows[i, o].nonconvex.shutdown_costs[t]
                        for t in m.TIMESTEPS)
            self.shutdowncosts = Expression(expr=shutdowncosts)

        if self.ACTIVE_FLOWS:
            for i, o in self.ACTIVE_FLOWS:
                if m.flows[i, o].nonconvex.activity_costs[0] is not None :
                    activitycosts += sum(
                        self.status[i, o, t] *
                        m.flows[i, o].nonconvex.activity_costs[t]
                        for t in m.TIMESTEPS)

            self.activitycosts = Expression(expr=activitycosts)

        return startcosts + shutdowncosts + activitycosts
