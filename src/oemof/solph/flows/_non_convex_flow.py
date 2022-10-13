# -*- coding: utf-8 -*-

"""Creating sets, variables, constraints and parts of the objective function
for nonconvex FlowBlock objects.

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

from pyomo.core import Binary
from pyomo.core import BuildAction
from pyomo.core import Constraint
from pyomo.core import Expression
from pyomo.core import Set
from pyomo.core import Var
from pyomo.core.base.block import ScalarBlock

from oemof.solph._options import NonConvex

from ._flow import Flow


class NonConvexFlow(Flow):
    r"""
    Flow with a binary variable that states whether it is active or not.

    Parameters
    ----------
    startup_costs : numeric (iterable or scalar)
        Costs associated with a start of the flow (representing a unit).
    shutdown_costs : numeric (iterable or scalar)
        Costs associated with the shutdown of the flow (representing a unit).
    activity_costs : numeric (iterable or scalar)
        Costs associated with the active operation of the flow, independently
        from the actual output.
    minimum_uptime : numeric (1 or positive integer)
        Minimum time that a flow must be greater then its minimum flow after
        startup. Be aware that minimum up and downtimes can contradict each
        other and may lead to infeasible problems.
    minimum_downtime : numeric (1 or positive integer)
        Minimum time a flow is forced to zero after shutting down.
        Be aware that minimum up and downtimes can contradict each
        other and may to infeasible problems.
    maximum_startups : numeric (0 or positive integer)
        Maximum number of start-ups.
    maximum_shutdowns : numeric (0 or positive integer)
        Maximum number of shutdowns.
    initial_status : numeric (0 or 1)
        Integer value indicating the status of the flow in the first time step
        (0 = off, 1 = on). For minimum up and downtimes, the initial status
        is set for the respective values in the edge regions e.g. if a
        minimum uptime of four timesteps is defined, the initial status is
        fixed for the four first and last timesteps of the optimization period.
        If both, up and downtimes are defined, the initial status is set for
        the maximum of both e.g. for six timesteps if a minimum downtime of
        six timesteps is defined in addition to a four timestep minimum uptime.
    positive_gradient : :obj:`dict`, default: `{'ub': None, 'costs': 0}`
        A dictionary containing the following two keys:

         * `'ub'`: numeric (iterable, scalar or None), the normed *upper
           bound* on the positive difference (`flow[t-1] < flow[t]`) of
           two consecutive flow values.
         * `'costs``: numeric (scalar or None), the gradient cost per
           unit.

    negative_gradient : :obj:`dict`, default: `{'ub': None, 'costs': 0}`
        A dictionary containing the following two keys:

          * `'ub'`: numeric (iterable, scalar or None), the normed *upper
            bound* on the negative difference (`flow[t-1] > flow[t]`) of
            two consecutive flow values.
          * `'costs``: numeric (scalar or None), the gradient cost per
            unit.
    """

    def __init__(
        self,
        startup_costs=None,
        shutdown_costs=None,
        activity_costs=None,
        inactivity_costs=None,
        minimum_uptime=None,
        minimum_downtime=None,
        maximum_startups=None,
        maximum_shutdowns=None,
        initial_status=0,
        positive_gradient=None,
        negative_gradient=None,
        **kwargs,
    ):
        default_gradient = {"ub": None, "costs": 0}
        if positive_gradient is None:
            positive_gradient = default_gradient
        if negative_gradient is None:
            negative_gradient = default_gradient
        nonconvex = NonConvex(
            startup_costs=startup_costs,
            shutdown_costs=shutdown_costs,
            activity_costs=activity_costs,
            inactivity_costs=inactivity_costs,
            minimum_uptime=minimum_uptime,
            minimum_downtime=minimum_downtime,
            maximum_startups=maximum_startups,
            maximum_shutdowns=maximum_shutdowns,
            initial_status=initial_status,
            positive_gradient=positive_gradient,
            negative_gradient=negative_gradient,
        )
        super().__init__(nonconvex=nonconvex, **kwargs)


class NonConvexFlowBlock(ScalarBlock):
    r"""
    **The following sets are created:** (-> see basic sets at
    :class:`.Model` )

    A set of flows with the attribute `nonconvex` of type
        :class:`.options.NonConvex`.
    MIN_FLOWS
        A subset of set NONCONVEX_FLOWS with the attribute `min`
        being not None in the first timestep.
    ACTIVITYCOSTFLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        `activity_costs` being not None.
    INACTIVITYCOSTFLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        `inactivity_costs` being not None.
    STARTUPFLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        `maximum_startups` or `startup_costs`
        being not None.
    MAXSTARTUPFLOWS
        A subset of set STARTUPFLOWS with the attribute
        `maximum_startups` being not None.
    SHUTDOWNFLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        `maximum_shutdowns` or `shutdown_costs`
        being not None.
    MAXSHUTDOWNFLOWS
        A subset of set SHUTDOWNFLOWS with the attribute
        `maximum_shutdowns` being not None.
    MINUPTIMEFLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        `minimum_uptime` being not None.
    MINDOWNTIMEFLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        `minimum_downtime` being not None.
    POSITIVE_GRADIENT_FLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        `positive_gradient` being not None.
    NEGATIVE_GRADIENT_FLOWS
        A subset of set NONCONVEX_FLOWS with the attribute
        `negative_gradient` being not None.

    **The following variables are created:**

    Status variable (binary) `om.NonConvexFlowBlock.status`:
        Variable indicating if flow is >= 0 indexed by FLOWS

    Startup variable (binary) `om.NonConvexFlowBlock.startup`:
        Variable indicating startup of flow (component) indexed by
        STARTUPFLOWS

    Shutdown variable (binary) `om.NonConvexFlowBlock.shutdown`:
        Variable indicating shutdown of flow (component) indexed by
        SHUTDOWNFLOWS

    Positive gradient (continuous) `om.NonConvexFlowBlock.positive_gradient`:
        Variable indicating the positive gradient, i.e. the load increase
        between two consecutive timesteps, indexed by
        POSITIVE_GRADIENT_FLOWS

    Negative gradient (continuous) `om.NonConvexFlowBlock.negative_gradient`:
        Variable indicating the negative gradient, i.e. the load decrease
        between two consecutive timesteps, indexed by
        NEGATIVE_GRADIENT_FLOWS


    **The following constraints are created:**

    Minimum flow constraint `om.NonConvexFlowBlock.min[i,o,t]`
        .. math::
            flow(i, o, t) \geq min(i, o, t) \cdot nominal\_value \
                \cdot status(i, o, t), \\
            \forall t \in \textrm{TIMESTEPS}, \\
            \forall (i, o) \in \textrm{NONCONVEX\_FLOWS}.

    Maximum flow constraint `om.NonConvexFlowBlock.max[i,o,t]`
        .. math::
            flow(i, o, t) \leq max(i, o, t) \cdot nominal\_value \
                \cdot status(i, o, t), \\
            \forall t \in \textrm{TIMESTEPS}, \\
            \forall (i, o) \in \textrm{NONCONVEX\_FLOWS}.

    Startup constraint `om.NonConvexFlowBlock.startup_constr[i,o,t]`
        .. math::
            startup(i, o, t) \geq \
                status(i,o,t) - status(i, o, t-1) \\
            \forall t \in \textrm{TIMESTEPS}, \\
            \forall (i,o) \in \textrm{STARTUPFLOWS}.

    Maximum startups constraint
      `om.NonConvexFlowBlock.max_startup_constr[i,o,t]`
        .. math::
            \sum_{t \in \textrm{TIMESTEPS}} startup(i, o, t) \leq \
                N_{start}(i,o)
            \forall (i,o) \in \textrm{MAXSTARTUPFLOWS}.

    Shutdown constraint `om.NonConvexFlowBlock.shutdown_constr[i,o,t]`
        .. math::
            shutdown(i, o, t) \geq \
                status(i, o, t-1) - status(i, o, t) \\
            \forall t \in \textrm{TIMESTEPS}, \\
            \forall (i, o) \in \textrm{SHUTDOWNFLOWS}.

    Maximum shutdowns constraint
      `om.NonConvexFlowBlock.max_startup_constr[i,o,t]`
        .. math::
            \sum_{t \in \textrm{TIMESTEPS}} startup(i, o, t) \leq \
                N_{shutdown}(i,o)
            \forall (i,o) \in \textrm{MAXSHUTDOWNFLOWS}.

    Minimum uptime constraint `om.NonConvexFlowBlock.uptime_constr[i,o,t]`
        .. math::
            (status(i, o, t)-status(i, o, t-1)) \cdot minimum\_uptime(i, o) \\
            \leq \sum_{n=0}^{minimum\_uptime-1} status(i,o,t+n) \\
            \forall t \in \textrm{TIMESTEPS} | \\
            t \neq \{0..minimum\_uptime\} \cup \
            \{t\_max-minimum\_uptime..t\_max\} , \\
            \forall (i,o) \in \textrm{MINUPTIMEFLOWS}.
            \\ \\
            status(i, o, t) = initial\_status(i, o) \\
            \forall t \in \textrm{TIMESTEPS} | \\
            t = \{0..minimum\_uptime\} \cup \
            \{t\_max-minimum\_uptime..t\_max\} , \\
            \forall (i,o) \in \textrm{MINUPTIMEFLOWS}.

    Minimum downtime constraint `om.NonConvexFlowBlock.downtime_constr[i,o,t]`
        .. math::
            (status(i, o, t-1)-status(i, o, t)) \
            \cdot minimum\_downtime(i, o) \\
            \leq minimum\_downtime(i, o) \
            - \sum_{n=0}^{minimum\_downtime-1} status(i,o,t+n) \\
            \forall t \in \textrm{TIMESTEPS} | \\
            t \neq \{0..minimum\_downtime\} \cup \
            \{t\_max-minimum\_downtime..t\_max\} , \\
            \forall (i,o) \in \textrm{MINDOWNTIMEFLOWS}.
            \\ \\
            status(i, o, t) = initial\_status(i, o) \\
            \forall t \in \textrm{TIMESTEPS} | \\
            t = \{0..minimum\_downtime\} \cup \
            \{t\_max-minimum\_downtime..t\_max\} , \\
            \forall (i,o) \in \textrm{MINDOWNTIMEFLOWS}.

    Positive gradient constraint
      `om.NonConvexFlowBlock.positive_gradient_constr[i, o]`:
        .. math:: flow(i, o, t) \cdot status(i, o, t)
            - flow(i, o, t-1) \cdot status(i, o, t-1)  \geq \
            positive\_gradient(i, o, t), \\
            \forall (i, o) \in \textrm{POSITIVE\_GRADIENT\_FLOWS}, \\
            \forall t \in \textrm{TIMESTEPS}.

    Negative gradient constraint
      `om.NonConvexFlowBlock.negative_gradient_constr[i, o]`:
        .. math::
            flow(i, o, t-1) \cdot status(i, o, t-1)
            - flow(i, o, t) \cdot status(i, o, t) \geq \
            negative\_gradient(i, o, t), \\
            \forall (i, o) \in \textrm{NEGATIVE\_GRADIENT\_FLOWS}, \\
            \forall t \in \textrm{TIMESTEPS}.


    **The following parts of the objective function are created:**

    If `nonconvex.startup_costs` is set by the user:
        .. math::
            \sum_{i, o \in STARTUPFLOWS} \sum_t  startup(i, o, t) \
            \cdot startup\_costs(i, o)

    If `nonconvex.shutdown_costs` is set by the user:
        .. math::
            \sum_{i, o \in SHUTDOWNFLOWS} \sum_t shutdown(i, o, t) \
            \cdot shutdown\_costs(i, o)

    If `nonconvex.activity_costs` is set by the user:
        .. math::
            \sum_{i, o \in ACTIVITYCOSTFLOWS} \sum_t status(i, o, t) \
            \cdot activity\_costs(i, o)

    If `nonconvex.inactivity_costs` is set by the user:
        .. math::
            \sum_{i, o \in INACTIVITYCOSTFLOWS} \sum_t (1 - status(i, o, t)) \
            \cdot inactivity\_costs(i, o)

    If `nonconvex.positive_gradient["costs"]` is set by the user:
        .. math::
            \sum_{i, o \in POSITIVE_GRADIENT_FLOWS} \sum_t
            positive_gradient(i, o, t) \cdot positive\_gradient\_costs(i, o)

    If `nonconvex.negative_gradient["costs"]` is set by the user:
        .. math::
            \sum_{i, o \in NEGATIVE_GRADIENT_FLOWS} \sum_t
            negative_gradient(i, o, t) \cdot negative\_gradient\_costs(i, o)

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """Creates set, variables, constraints for all flow object with
        an attribute flow of type class:`.NonConvexFlowBlock`.

        Parameters
        ----------
        group : list
            List of oemof.solph.NonConvexFlowBlock objects for which
            the constraints are build.
        """
        if group is None:
            return None

        m = self.parent_block()
        # ########################## SETS #####################################
        self.NONCONVEX_FLOWS = Set(initialize=[(g[0], g[1]) for g in group])

        self.MIN_FLOWS = Set(
            initialize=[(g[0], g[1]) for g in group if g[2].min[0] is not None]
        )
        self.STARTUPFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.startup_costs[0] is not None
                or g[2].nonconvex.maximum_startups is not None
            ]
        )
        self.MAXSTARTUPFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.maximum_startups is not None
            ]
        )
        self.SHUTDOWNFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.shutdown_costs[0] is not None
                or g[2].nonconvex.maximum_shutdowns is not None
            ]
        )
        self.MAXSHUTDOWNFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.maximum_shutdowns is not None
            ]
        )
        self.MINUPTIMEFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.minimum_uptime is not None
            ]
        )
        self.MAXUPTIMEFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.maximum_uptime is not None
            ]
        )

        self.MINDOWNTIMEFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.minimum_downtime is not None
            ]
        )

        self.ACTIVITYCOSTFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.activity_costs[0] is not None
            ]
        )

        self.INACTIVITYCOSTFLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.inactivity_costs[0] is not None
            ]
        )

        self.NEGATIVE_GRADIENT_FLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.negative_gradient["ub"][0] is not None
            ]
        )

        self.POSITIVE_GRADIENT_FLOWS = Set(
            initialize=[
                (g[0], g[1])
                for g in group
                if g[2].nonconvex.positive_gradient["ub"][0] is not None
            ]
        )

        # ################### VARIABLES AND CONSTRAINTS #######################
        self.status = Var(self.NONCONVEX_FLOWS, m.TIMESTEPS, within=Binary)

        if self.STARTUPFLOWS:
            self.startup = Var(self.STARTUPFLOWS, m.TIMESTEPS, within=Binary)

        if self.SHUTDOWNFLOWS:
            self.shutdown = Var(self.SHUTDOWNFLOWS, m.TIMESTEPS, within=Binary)

        if self.POSITIVE_GRADIENT_FLOWS:
            self.positive_gradient = Var(
                self.POSITIVE_GRADIENT_FLOWS, m.TIMESTEPS
            )

        if self.NEGATIVE_GRADIENT_FLOWS:
            self.negative_gradient = Var(
                self.NEGATIVE_GRADIENT_FLOWS, m.TIMESTEPS
            )

        def _minimum_flow_rule(block, i, o, t):
            """Rule definition for MILP minimum flow constraints."""
            expr = (
                self.status[i, o, t]
                * m.flows[i, o].min[t]
                * m.flows[i, o].nominal_value
                <= m.flow[i, o, t]
            )
            return expr

        self.min = Constraint(
            self.MIN_FLOWS, m.TIMESTEPS, rule=_minimum_flow_rule
        )

        def _maximum_flow_rule(block, i, o, t):
            """Rule definition for MILP maximum flow constraints."""
            expr = (
                self.status[i, o, t]
                * m.flows[i, o].max[t]
                * m.flows[i, o].nominal_value
                >= m.flow[i, o, t]
            )
            return expr

        self.max = Constraint(
            self.MIN_FLOWS, m.TIMESTEPS, rule=_maximum_flow_rule
        )

        def _startup_rule(block, i, o, t):
            """Rule definition for startup constraint of nonconvex flows."""
            if t > m.TIMESTEPS[1]:
                expr = (
                    self.startup[i, o, t]
                    >= self.status[i, o, t] - self.status[i, o, t - 1]
                )
            else:
                expr = (
                    self.startup[i, o, t]
                    >= self.status[i, o, t]
                    - m.flows[i, o].nonconvex.initial_status
                )
            return expr

        self.startup_constr = Constraint(
            self.STARTUPFLOWS, m.TIMESTEPS, rule=_startup_rule
        )

        def _max_startup_rule(block, i, o):
            """Rule definition for maximum number of start-ups."""
            lhs = sum(self.startup[i, o, t] for t in m.TIMESTEPS)
            return lhs <= m.flows[i, o].nonconvex.maximum_startups

        self.max_startup_constr = Constraint(
            self.MAXSTARTUPFLOWS, rule=_max_startup_rule
        )

        def _shutdown_rule(block, i, o, t):
            """Rule definition for shutdown constraints of nonconvex flows."""
            if t > m.TIMESTEPS[1]:
                expr = (
                    self.shutdown[i, o, t]
                    >= self.status[i, o, t - 1] - self.status[i, o, t]
                )
            else:
                expr = (
                    self.shutdown[i, o, t]
                    >= m.flows[i, o].nonconvex.initial_status
                    - self.status[i, o, t]
                )
            return expr

        self.shutdown_constr = Constraint(
            self.SHUTDOWNFLOWS, m.TIMESTEPS, rule=_shutdown_rule
        )

        def _max_shutdown_rule(block, i, o):
            """Rule definition for maximum number of start-ups."""
            lhs = sum(self.shutdown[i, o, t] for t in m.TIMESTEPS)
            return lhs <= m.flows[i, o].nonconvex.maximum_shutdowns

        self.max_shutdown_constr = Constraint(
            self.MAXSHUTDOWNFLOWS, rule=_max_shutdown_rule
        )

        def _min_uptime_rule(block, i, o, t):
            """
            Rule definition for min-uptime constraints of nonconvex flows.
            """
            if (
                m.flows[i, o].nonconvex.max_up_down
                <= t
                <= m.TIMESTEPS[-1] - m.flows[i, o].nonconvex.max_up_down
            ):
                expr = 0
                expr += (
                    self.status[i, o, t] - self.status[i, o, t - 1]
                ) * m.flows[i, o].nonconvex.minimum_uptime
                expr += -sum(
                    self.status[i, o, t + u]
                    for u in range(0, m.flows[i, o].nonconvex.minimum_uptime)
                )
                return expr <= 0
            else:
                expr = 0
                expr += self.status[i, o, t]
                expr += -m.flows[i, o].nonconvex.initial_status
                return expr == 0

        self.min_uptime_constr = Constraint(
            self.MINUPTIMEFLOWS, m.TIMESTEPS, rule=_min_uptime_rule
        )

        def _max_uptime_rule(block, i, o, t):
            """
            Rule definition for max-uptime constraints of nonconvex flows.
            """
            if (
                m.flows[i, o].nonconvex.max_up_down
                <= t
                <= m.TIMESTEPS[-1] - m.flows[i, o].nonconvex.max_up_down
            ):
                expr = 0
                expr += m.flows[i, o].nonconvex.maximum_uptime
                expr += -sum(
                    self.status[i, o, t - u]
                    for u in range(
                        0, m.flows[i, o].nonconvex.maximum_uptime + 1
                    )
                )
                return expr >= 0
            else:
                expr = 0
                expr += self.status[i, o, t]
                expr += -m.flows[i, o].nonconvex.initial_status
                return expr == 0

        self.max_uptime_constr = Constraint(
            self.MAXUPTIMEFLOWS, m.TIMESTEPS, rule=_max_uptime_rule
        )

        def _min_downtime_rule(block, i, o, t):
            """
            Rule definition for min-downtime constraints of nonconvex flows.
            """
            if (
                m.flows[i, o].nonconvex.max_up_down
                <= t
                <= m.TIMESTEPS[-1] - m.flows[i, o].nonconvex.max_up_down
            ):
                expr = 0
                expr += (
                    self.status[i, o, t - 1] - self.status[i, o, t]
                ) * m.flows[i, o].nonconvex.minimum_downtime
                expr += -m.flows[i, o].nonconvex.minimum_downtime
                expr += sum(
                    self.status[i, o, t + d]
                    for d in range(0, m.flows[i, o].nonconvex.minimum_downtime)
                )
                return expr <= 0
            else:
                expr = 0
                expr += self.status[i, o, t]
                expr += -m.flows[i, o].nonconvex.initial_status
                return expr == 0

        self.min_downtime_constr = Constraint(
            self.MINDOWNTIMEFLOWS, m.TIMESTEPS, rule=_min_downtime_rule
        )

        def _positive_gradient_flow_rule(block):
            """Rule definition for positive gradient constraint."""
            for i, o in self.POSITIVE_GRADIENT_FLOWS:
                for t in m.TIMESTEPS:
                    if t > 0:
                        lhs = (
                            m.flow[i, o, t] * self.status[i, o, t]
                            - m.flow[i, o, t - 1] * self.status[i, o, t - 1]
                        )
                        rhs = self.positive_gradient[i, o, t]
                        self.positive_gradient_constr.add(
                            (i, o, t), lhs <= rhs
                        )
                    else:
                        pass  # return(Constraint.Skip)

        self.positive_gradient_constr = Constraint(
            self.POSITIVE_GRADIENT_FLOWS, m.TIMESTEPS, noruleinit=True
        )
        self.positive_gradient_build = BuildAction(
            rule=_positive_gradient_flow_rule
        )

        def _negative_gradient_flow_rule(block):
            """Rule definition for negative gradient constraint."""
            for i, o in self.NEGATIVE_GRADIENT_FLOWS:
                for t in m.TIMESTEPS:
                    if t > 0:
                        lhs = (
                            m.flow[i, o, t - 1] * self.status[i, o, t - 1]
                            - m.flow[i, o, t] * self.status[i, o, t]
                        )
                        rhs = self.negative_gradient[i, o, t]
                        self.negative_gradient_constr.add(
                            (i, o, t), lhs <= rhs
                        )
                    else:
                        pass  # return(Constraint.Skip)

        self.negative_gradient_constr = Constraint(
            self.NEGATIVE_GRADIENT_FLOWS, m.TIMESTEPS, noruleinit=True
        )
        self.negative_gradient_build = BuildAction(
            rule=_negative_gradient_flow_rule
        )

    def _objective_expression(self):
        r"""Objective expression for nonconvex flows."""
        if not hasattr(self, "NONCONVEX_FLOWS"):
            return 0

        m = self.parent_block()

        startup_costs = 0
        shutdown_costs = 0
        activity_costs = 0
        inactivity_costs = 0
        gradient_costs = 0

        if self.STARTUPFLOWS:
            for i, o in self.STARTUPFLOWS:
                if m.flows[i, o].nonconvex.startup_costs[0] is not None:
                    startup_costs += sum(
                        self.startup[i, o, t]
                        * m.flows[i, o].nonconvex.startup_costs[t]
                        for t in m.TIMESTEPS
                    )
            self.startup_costs = Expression(expr=startup_costs)

        if self.SHUTDOWNFLOWS:
            for i, o in self.SHUTDOWNFLOWS:
                if m.flows[i, o].nonconvex.shutdown_costs[0] is not None:
                    shutdown_costs += sum(
                        self.shutdown[i, o, t]
                        * m.flows[i, o].nonconvex.shutdown_costs[t]
                        for t in m.TIMESTEPS
                    )
            self.shutdown_costs = Expression(expr=shutdown_costs)

        if self.ACTIVITYCOSTFLOWS:
            for i, o in self.ACTIVITYCOSTFLOWS:
                if m.flows[i, o].nonconvex.activity_costs[0] is not None:
                    activity_costs += sum(
                        self.status[i, o, t]
                        * m.flows[i, o].nonconvex.activity_costs[t]
                        for t in m.TIMESTEPS
                    )

            self.activity_costs = Expression(expr=activity_costs)

        if self.INACTIVITYCOSTFLOWS:
            for i, o in self.INACTIVITYCOSTFLOWS:
                if m.flows[i, o].nonconvex.inactivity_costs[0] is not None:
                    inactivity_costs += sum(
                        (1 - self.status[i, o, t])
                        * m.flows[i, o].nonconvex.inactivity_costs[t]
                        for t in m.TIMESTEPS
                    )

            self.inactivity_costs = Expression(expr=inactivity_costs)

        return (
            startup_costs
            + shutdown_costs
            + activity_costs
            + inactivity_costs
            + gradient_costs
        )
