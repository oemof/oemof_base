# -*- coding: utf-8 -*-

"""
In-development functionality for demand-side management.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: Johannes Röder
SPDX-FileCopyrightText: jakob-wo
SPDX-FileCopyrightText: gplssm
SPDX-FileCopyrightText: jnnr
SPDX-FileCopyrightText: Johannes Kochems (jokochems)

SPDX-License-Identifier: MIT

"""
import itertools
from warnings import warn

from numpy import mean
from pyomo.core.base.block import SimpleBlock
from pyomo.environ import BuildAction
from pyomo.environ import Constraint
from pyomo.environ import Expression
from pyomo.environ import NonNegativeReals
from pyomo.environ import Set
from pyomo.environ import Var

from oemof.solph.network import Sink
from oemof.solph.options import Investment
from oemof.solph.options import MultiPeriodInvestment
from oemof.solph.plumbing import sequence
from oemof.tools import debugging
from oemof.tools import economics


class SinkDSM(Sink):
    r"""
    Demand Side Management implemented as Sink with flexibility potential.

    There are several approaches possible which can be selected:
    - DIW: Based on the paper by Zerrahn, Alexander and Schill, Wolf-Peter
    (2015): `On the representation of demand-side management in power system
    models <https://doi.org/10.1016/j.energy.2015.03.037>`_,
    in: Energy (84), pp. 840-845, 10.1016/j.energy.2015.03.037,
    accessed 08.01.2021, pp. 842-843.
    - DLR: Based on the PhD thesis of Gils, Hans Christian (2015):
    `Balancing of Intermittent Renewable Power Generation by Demand Response
    and Thermal Energy Storage`, Stuttgart,
    <http://dx.doi.org/10.18419/opus-6888>,
    accessed 08.01.2021, pp. 67-70.
    - oemof: Created by Julian Endres. A fairly simple DSM representation which
    demands the energy balance to be levelled out in fixed cycles

    An evaluation of different modeling approaches has been carried out and
    presented at the INREC 2020. Some of the results are as follows:
    - DIW: A solid implementation with the tendency of slight overestimization
    of potentials since a shift_time is not accounted for. It may get
    computationally expensive due to a high time-interlinkage in constraint
    formulations.
    - DLR: An extensive modeling approach for demand response which neither
    leads to an over- nor underestimization of potentials and balances modeling
    detail and computation intensity. :attr:`fixes` and :attr:`addition` should
    both be set to True which is the default value.
    - oemof: A very computationally efficient approach which only requires the
    energy balance to be levelled out in certain intervals. If demand response
    is not at the center of the research and/or parameter availability is
    limited, this approach should be chosen. Note that approach `oemof` does
    allow for load shedding, but does not impose a limit on maximum amount of
    shedded energy.

    SinkDSM adds additional constraints that allow to shift energy in certain
    time window constrained by :attr:`~capacity_up` and
    :attr:`~capacity_down`.

    For a MultiPeriodModel, set :attr:`multiperiod` to True or define
    :attr:`multiperiodinvestment` of type :class:`MultiPeriodInvestment
    <oemof.solph.options.MultiPeriodInvestment>`.

    Parameters
    ----------
    demand: numeric
        original electrical demand (normalized)
        For investment modeling, it is advised to use the maximum of the
        demand timeseries and the cumulated (fixed) infeed time series
        for normalization, because the balancing potential may be determined by
        both. Elsewhise, underinvestments may occur.
    capacity_up: int or array
        maximum DSM capacity that may be increased (normalized)
    capacity_down: int or array
        maximum DSM capacity that may be reduced (normalized)
    approach: 'oemof', 'DIW', 'DLR'
        Choose one of the DSM modeling approaches. Read notes about which
        parameters to be applied for which approach.

        oemof :

            Simple model in which the load shift must be compensated in a
            predefined fixed interval (:attr:`~shift_interval` is mandatory).
            Within time windows of the length :attr:`~shift_interval` DSM
            up and down shifts are balanced. See
            :class:`~SinkDSMOemofBlock` for details.

        DIW :

            Sophisticated model based on the formulation by
            Zerrahn & Schill (2015a). The load shift of the component must be
            compensated in a predefined delay time (:attr:`~delay_time` is
            mandatory).
            For details see :class:`~SinkDSMDIWBlock`.

        DLR :

            Sophisticated model based on the formulation by
            Gils (2015). The load shift of the component must be
            compensated in a predefined delay time (:attr:`~delay_time` is
            mandatory).
            For details see :class:`~SinkDSMDLRBlock`.
    shift_interval: int
        Only used when :attr:`~approach` is set to 'oemof'. Otherwise, can be
        None.
        It's the interval in which between :math:`DSM_{t}^{up}` and
        :math:`DSM_{t}^{down}` have to be compensated.
    delay_time: int
        Only used when :attr:`~approach` is set to 'DIW' or 'DLR'. Otherwise,
        can be None.
        Length of symmetrical time windows around :math:`t` in which
        :math:`DSM_{t}^{up}` and :math:`DSM_{t,tt}^{down}` have to be
        compensated.
        Note: For approach 'DLR', an iterable is constructed in order
        to model flexible delay times
    shift_time: int
        Only used when :attr:`~approach` is set to 'DLR'.
        Duration of a single upwards or downwards shift (half a shifting cycle
        if there is immediate compensation)
    shed_time: int
        Only used when :attr:`~shed_eligibility` is set to True.
        Maximum length of a load shedding process at full capacity
        (used within energy limit constraint)
    max_demand: numeric
        Maximum demand prior to demand response
    max_capacity_down: numeric
        Maximum capacity eligible for downshifts
        prior to demand response (used for dispatch mode)
    max_capacity_up: numeric
        Maximum capacity eligible for upshifts
        prior to demand response (used for dispatch mode)
    flex_share_down: float
        Flexible share of installed capacity
        eligible for downshifts (used for invest mode)
    flex_share_up: float
        Flexible share of installed capacity
        eligible for upshifts (used for invest mode)
    cost_dsm_up : int
        Cost per unit of DSM activity that increases the demand
    cost_dsm_down_shift : int
        Cost per unit of DSM activity that decreases the demand
        for load shifting
    cost_dsm_down_shed : int
        Cost per unit of DSM activity that decreases the demand
        for load shedding
    efficiency : float
        Efficiency factor for load shifts (between 0 and 1)
    recovery_time_shift : int
        Only used when :attr:`~approach` is set to 'DIW'.
        Minimum time between the end of one load shifting process
        and the start of another for load shifting processes
    recovery_time_shed : int
        Only used when :attr:`~approach` is set to 'DIW'.
        Minimum time between the end of one load shifting process
        and the start of another for load shedding processes
    ActivateYearLimit : boolean
        Only used when :attr:`~approach` is set to 'DLR'.
        Control parameter; activates constraints for year limit if set to True
    ActivateDayLimit : boolean
        Only used when :attr:`~approach` is set to 'DLR'.
        Control parameter; activates constraints for day limit if set to True
    n_yearLimit_shift : int
        Only used when :attr:`~approach` is set to 'DLR'.
        Maximum number of load shifts at full capacity per year, used to limit
        the amount of energy shifted per year. Optional parameter that is only
        needed when ActivateYearLimit is True
    n_yearLimit_shed : int
        Only used when :attr:`~approach` is set to 'DLR'.
        Maximum number of load sheds at full capacity per year, used to limit
        the amount of energy shedded per year. Mandatory parameter if load
        shedding is allowed by setting shed_eligibility to True
    t_dayLimit: int
        Only used when :attr:`~approach` is set to 'DLR'.
        Maximum duration of load shifts at full capacity per day, used to limit
        the amount of energy shifted per day. Optional parameter that is only
        needed when ActivateDayLimit is True
    addition : boolean
        Only used when :attr:`~approach` is set to 'DLR'.
        Boolean parameter indicating whether or not to include additional
        constraint (which corresponds to Eq. 10 from Zerrahn and Schill (2015a)
    fixes : boolean
        Only used when :attr:`~approach` is set to 'DLR'.
        Boolean parameter indicating whether or not to include additional
        fixes. These comprise prohibiting shifts which cannot be balanced
        within the optimization timeframe
    shed_eligibility : boolean
        Boolean parameter indicating whether unit is eligible for
        load shedding
    shift_eligibility : boolean
        Boolean parameter indicating whether unit is eligible for
        load shifting

    Note
    ----

    * :attr:`method` has been renamed to :attr:`approach`.
    * As many constraints and dependencies are created in approach 'DIW',
      computational cost might be high with a large 'delay_time' and with model
      of high temporal resolution
    * The approach 'DLR' preforms better in terms of calculation time,
      compared to the approach 'DIW'
    * Using :attr:`~approach` 'DIW' or 'DLR' might result in demand shifts that
      exceed the specified delay time by activating up and down simultaneously
      in the time steps between to DSM events. Thus, the purpose of this
      component is to model demand response portfolios rather than individual
      demand units.
    * It's not recommended to assign cost to the flow that connects
      :class:`~SinkDSM` with a bus. Instead, use :attr:`~SinkDSM.cost_dsm_up`
      or :attr:`~cost_dsm_down_shift`
    * Variable costs may be attributed to upshifts, downshifts or both.
      Costs for shedding may deviate from that for shifting
      (usually costs for shedding are much larger and equal to the value
      of lost load).

    """

    def __init__(self,
                 demand,
                 capacity_up,
                 capacity_down,
                 approach,
                 shift_interval=None,
                 delay_time=None,
                 shift_time=None,
                 shed_time=None,
                 max_demand=None,
                 max_capacity_down=None,
                 max_capacity_up=None,
                 flex_share_down=None,
                 flex_share_up=None,
                 cost_dsm_up=0,
                 cost_dsm_down_shift=0,
                 cost_dsm_down_shed=0,
                 efficiency=1,
                 recovery_time_shift=None,
                 recovery_time_shed=None,
                 ActivateYearLimit=False,
                 ActivateDayLimit=False,
                 n_yearLimit_shift=None,
                 n_yearLimit_shed=None,
                 t_dayLimit=None,
                 addition=True,
                 fixes=True,
                 shed_eligibility=True,
                 shift_eligibility=True,
                 **kwargs):
        super().__init__(**kwargs)

        self.capacity_up = sequence(capacity_up)
        self.capacity_down = sequence(capacity_down)
        self.demand = sequence(demand)
        self.approach = approach
        self.shift_interval = shift_interval
        if not approach == "DLR":
            self.delay_time = delay_time
        else:
            self.delay_time = [el for el in range(1, delay_time + 1)]
        self.shift_time = shift_time
        self.shed_time = shed_time

        # Attributes are only needed if no investments occur
        self.max_capacity_down = max_capacity_down
        self.max_capacity_up = max_capacity_up
        self.max_demand = max_demand

        # Attributes for investment modeling
        if flex_share_down is not None:
            if max_capacity_down is None and max_demand is None:
                self.flex_share_down = flex_share_down
            else:
                e1 = (
                    "Please determine either **flex_share_down "
                    "(investment modeling)\n or set "
                    "**max_demand and **max_capacity_down "
                    "(dispatch modeling).\n"
                    "Otherwise, overdetermination occurs."
                )
                raise AttributeError(e1)
        else:
            if max_capacity_down is None or max_demand is None:
                e2 = (
                    "If you do not specify **flex_share_down\n"
                    "which should be used for investment modeling,\n"
                    "you have to specify **max_capacity_down "
                    "and **max_demand\n"
                    "instead which should be used for dispatch modeling."
                )
                raise AttributeError(e2)
            else:
                self.flex_share_down = self.max_capacity_down / self.max_demand

        if flex_share_up is not None:
            if max_capacity_up is None and max_demand is None:
                self.flex_share_up = flex_share_up
            else:
                e3 = (
                    "Please determine either **flex_share_up "
                    "(investment modeling)\n or set"
                    "**max_demand and **max_capacity_up (dispatch modeling).\n"
                    "Otherwise, overdetermination occurs.")
                raise AttributeError(e3)
        else:
            if max_capacity_up is None or max_demand is None:
                e4 = (
                    "If you do not specify **flex_share_up\n"
                    "which should be used for investment modeling,\n"
                    "you have to specify **max_capacity_up "
                    "and **max_demand\n"
                    "instead which should be used for dispatch modeling."
                )
                raise AttributeError(e4)
            else:
                self.flex_share_up = self.max_capacity_up / self.max_demand

        self.cost_dsm_up = sequence(cost_dsm_up)
        self.cost_dsm_down_shift = sequence(cost_dsm_down_shift)
        self.cost_dsm_down_shed = sequence(cost_dsm_down_shed)
        self.efficiency = efficiency
        self.capacity_down_mean = mean(capacity_down)
        self.capacity_up_mean = mean(capacity_up)
        self.recovery_time_shift = recovery_time_shift
        self.recovery_time_shed = recovery_time_shed
        self.ActivateYearLimit = ActivateYearLimit
        self.ActivateDayLimit = ActivateDayLimit
        self.n_yearLimit_shift = n_yearLimit_shift
        self.n_yearLimit_shed = n_yearLimit_shed
        self.t_dayLimit = t_dayLimit
        self.addition = addition
        self.fixes = fixes
        self.shed_eligibility = shed_eligibility
        self.shift_eligibility = shift_eligibility

        # Check whether investment mode is active or not
        self.investment = kwargs.get("investment")
        self._invest_group = isinstance(self.investment, Investment)
        self.multiperiodinvestment = kwargs.get("multiperiodinvestment")
        self._multiperiodinvest_group = isinstance(
            self.multiperiodinvestment, MultiPeriodInvestment)

        # Check for multiperiod unit
        self.multiperiod = kwargs.get("multiperiod", False)

        if self._invest_group or self._multiperiodinvest_group:
            self._check_invest_attributes()

    def _check_invest_attributes(self):
        if (self.investment is not None
            or self.multiperiodinvestment is not None
            and (self.max_demand
                 or self.max_capacity_down
                 or self.max_capacity_up) is not None):
            e5 = (
                "If an investment object is defined, the invest variable "
                "replaces the max_demand, the **max_capacity_down "
                "as well as\n"
                "the **max_capacity_up values. Therefore, **max_demand,\n"
                "**max_capacity_up and **max_capacity_down values should be "
                "'None' (the default values).\n"
            )
            raise AttributeError(e5)

        if (self.investment is not None
                and self.multiperiodinvestment is not None):
            e6 = (
                "Either define an investment object "
                "(solph.options.Investment) "
                "for standard investment models\nor define a "
                "multiperiodinvestment object "
                "(solph.options.MultiPeriodInvestment) in case you want to set"
                "up a MultiPeriodModel.\nSetting both at the "
                "same time is not feasible.\n"
            )
            raise AttributeError(e6)

        if (self.multiperiod is True
                and self.multiperiodinvestment is not None):
            e7 = (
                "Either set multiperiod to True if you want to define a "
                "unit for dispatch only in a MultiPeriodModel or define a "
                "multiperiodinvestment object "
                "(solph.options.MultiPeriodInvestment) for allowing "
                "investments.\nSetting both at the same time is not allowed.\n"
            )
            raise AttributeError(e7)

        if (self.investment is not None
                and self.multiperiod is True):
            e8 = (
                "Either define an investment object if you want to build "
                "a standard investment model or set multiperiod "
                "to True if you want to simulate a dispatch only unit in a "
                "MultiPeriodModel.\nSetting both at the same time is not"
                "feasible."
            )
            raise AttributeError(e8)

    def constraint_group(self):
        possible_approaches = ["DIW", "DLR", "oemof"]

        if self.approach in [possible_approaches[0],
                             possible_approaches[1]]:
            if self.delay_time is None:
                raise ValueError(
                    "Please define: **delay_time"
                    " is a mandatory parameter"
                )
            if not self.shed_eligibility and not self.shift_eligibility:
                raise ValueError(
                    "At least one of **shed_eligibility"
                    " and **shift_eligibility must be True"
                )
            if self.shed_eligibility:
                if self.recovery_time_shed is None:
                    raise ValueError(
                        "If unit is eligible for load shedding,"
                        " **recovery_time_shed must be defined"
                    )

        if self.approach == possible_approaches[0]:
            if self._invest_group is True:
                return SinkDSMDIWInvestmentBlock
            elif self._multiperiodinvest_group is True:
                return SinkDSMDIWMultiPeriodInvestmentBlock
            elif self.multiperiod is True:
                return SinkDSMDIWMultiPeriodBlock
            else:
                return SinkDSMDIWBlock

        elif self.approach == possible_approaches[1]:
            if self._invest_group is True:
                return SinkDSMDLRInvestmentBlock
            elif self._multiperiodinvest_group is True:
                return SinkDSMDLRMultiPeriodInvestmentBlock
            elif self.multiperiod is True:
                return SinkDSMDLRMultiPeriodBlock
            else:
                return SinkDSMDLRBlock

        elif self.approach == possible_approaches[2]:
            if self.shift_interval is None:
                raise ValueError("Please define: **shift_interval"
                                 " is a mandatory parameter")
            if self._invest_group is True:
                return SinkDSMOemofInvestmentBlock
            elif self._multiperiodinvest_group is True:
                return SinkDSMOemofMultiPeriodInvestmentBlock
            elif self.multiperiod is True:
                return SinkDSMOemofMultiPeriodBlock
            else:
                return SinkDSMOemofBlock
        else:
            raise ValueError(
                'The "approach" must be one of the following set: '
                '"{}"'.format('" or "'.join(possible_approaches)))


class SinkDSMOemofBlock(SimpleBlock):
    r"""Constraints for SinkDSM with "oemof" approach

    **The following constraints are created for approach = 'oemof':**

    .. _SinkDSMOemof equations:

    .. math::
        &
        (1) \quad DSM_{t}^{up} = 0 \quad \forall t
        \quad if \space eligibility_{shift} = False \\
        &
        (2) \quad DSM_{t}^{do, shed} = 0 \quad \forall t
        \quad if \space eligibility_{shed} = False \\
        &
        (3) \quad \dot{E}_{t} = demand_{t} \cdot demand_{max} + DSM_{t}^{up}
        - DSM_{t}^{do, shift} - DSM_{t}^{do, shed}
        \quad \forall t \in \mathbb{T} \\
        &
        (4) \quad  DSM_{t}^{up} \leq E_{t}^{up} \cdot E_{up, max}
        \quad \forall t \in \mathbb{T} \\
        &
        (5) \quad DSM_{t}^{do, shift} + DSM_{t}^{do, shed}
        \leq  E_{t}^{do} \cdot E_{do, max}
        \quad \forall t \in \mathbb{T} \\
        &
        (6) \quad  \sum_{t=t_s}^{t_s+\tau} DSM_{t}^{up} \cdot \eta =
        \sum_{t=t_s}^{t_s+\tau} DSM_{t}^{do, shift} \quad \forall t_s \in
        \{k \in \mathbb{T} \mid k \mod \tau = 0\} \\
        &

    **The following parts of the objective function are created:**

    .. math::
        DSM_{t}^{up} \cdot cost_{t}^{dsm, up}
        + DSM_{t}^{do, shift} \cdot cost_{t}^{dsm, do, shift}
        + DSM_{t}^{do, shed} \cdot cost_{t}^{dsm, do, shed}
        \quad \forall t \in \mathbb{T} \\

    **Table: Symbols and attribute names of variables and parameters**

        .. csv-table:: Variables (V) and Parameters (P)
            :header: "symbol", "attribute", "type", "explanation"
            :widths: 1, 1, 1, 1

            ":math:`DSM_{t}^{up}` ",
            ":attr:`~SinkDSM.dsm_up[g, t]` ","V", "DSM
            up shift (capacity shifted upwards)"
            ":math:`DSM_{t}^{do, shift}` ",
            ":attr:`~SinkDSM.dsm_do_shift[g, t]` ",
            "V","DSM down shift (capacity shifted downwards)"
            ":math:`DSM_{t}^{do, shed}` ",
            ":attr:`~SinkDSM.dsm_do_shed[g, t]` ",
            "V","DSM shedded (capacity shedded, i.e. not compensated for)"
            ":math:`\dot{E}_{t}`",":attr:`~SinkDSM.inputs`","V", "Energy
            flowing in from (electrical) inflow bus"
            ":math:`demand_{t}`",":attr:`~SinkDSM.demand[t]`","P",
            "(Electrical) demand series (normalized)"
            ":math:`demand_{max}`",":attr:`~SinkDSM.max_demand`","P",
            "Maximum demand value"
            ":math:`E_{t}^{do}`",":attr:`~SinkDSM.capacity_down[t]`","P",
            "Capacity  allowed for a load adjustment downwards (normalized)
            (DSM down shift + DSM shedded)"
            ":math:`E_{t}^{up}`",":attr:`~SinkDSM.capacity_up[t]`","P",
            "Capacity allowed for a shift upwards (normalized) (DSM up shift)"
            ":math:`E_{do, max}`",":attr:`~SinkDSM.max_capacity_down`","P",
            "Maximum capacity allowed for a load adjustment downwards
            (DSM down shift + DSM shedded)"
            ":math:`E_{up, max}`",":attr:`~SinkDSM.max_capacity_up`","P",
            "Capacity allowed for a shift upwards (normalized) (DSM up shift)"
            ":math:`\tau`",":attr:`~SinkDSM.shift_interval`","P", "Shift
            interval (time within which the energy balance must be
            levelled out"
            ":math:`\eta`",":attr:`~SinkDSM.efficiency`","P", "Efficiency
            loss forload shifting processes"
            ":math:`\eta`",":attr:`efficiency`","P", "Efficiency loss for
            load shifting processes"
            ":math:`\mathbb{T}` "," ","P", "Time steps"
            ":math:`eligibility_{shift}` ",
            ":attr:`~SinkDSM.shift_eligibility`","P",
            "Boolean parameter indicating if unit can be used for
            load shifting"
            ":math:`eligibility_{shed}` ",
            ":attr:`~SinkDSM.shed_eligibility`","P",
            "Boolean parameter indicating if unit can be used for
            load shedding"
            ":math:`cost_{t}^{dsm, up}` ", ":attr:`~SinkDSM.cost_dsm_up[t]`",
            "P", "Variable costs for an upwards shift"
            ":math:`cost_{t}^{dsm, do, shift}` ",
            ":attr:`~SinkDSM.cost_dsm_down_shift[t]`","P",
            "Variable costs for a downwards shift (load shifting)"
            ":math:`cost_{t}^{dsm, do, shed}` ",
            ":attr:`~SinkDSM.cost_dsm_down_shed[t]`","P",
            "Variable costs for shedding load"
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all DSM components get inflow from a bus
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        # Set of DSM Components
        self.dsm = Set(initialize=[n for n in group])

        #  ************* VARIABLES *****************************

        # Variable load shift down
        self.dsm_do_shift = Var(
            self.dsm, m.TIMESTEPS, initialize=0,
            within=NonNegativeReals
        )

        # Variable load shedding
        self.dsm_do_shed = Var(
            self.dsm, m.TIMESTEPS, initialize=0,
            within=NonNegativeReals)

        # Variable load shift up
        self.dsm_up = Var(
            self.dsm, m.TIMESTEPS, initialize=0, within=NonNegativeReals
        )

        #  ************* CONSTRAINTS *****************************

        def _shift_shed_vars_rule(block):
            """Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if not g.shift_eligibility:
                        lhs = self.dsm_up[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

                    if not g.shed_eligibility:
                        lhs = self.dsm_do_shed[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Demand Production Relation
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DSM.
            Generator Production == Demand_el +- DSM
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # Inflow from bus
                    lhs = m.flow[g.inflow, g, t]

                    # Demand + DSM_up - DSM_down
                    rhs = (g.demand[t] * g.max_demand
                           + self.dsm_up[g, t] - self.dsm_do_shift[g, t]
                           - self.dsm_do_shed[g, t])

                    # add constraint
                    block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule
        )

        # Upper bounds relation
        def dsm_up_constraint_rule(block):
            """Realised upward load shift at time t has to be smaller than
            upward DSM capacity at time t.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # DSM up
                    lhs = self.dsm_up[g, t]
                    # Capacity dsm_up
                    rhs = g.capacity_up[t] * g.max_capacity_up

                    # add constraint
                    block.dsm_up_constraint.add((g, t), (lhs <= rhs))

        self.dsm_up_constraint = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.dsm_up_constraint_build = BuildAction(rule=dsm_up_constraint_rule)

        # Upper bounds relation
        def dsm_down_constraint_rule(block):
            """Realised downward load shift at time t has to be smaller than
            downward DSM capacity at time t.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # DSM down
                    lhs = self.dsm_do_shift[g, t] + self.dsm_do_shed[g, t]
                    # Capacity dsm_down
                    rhs = g.capacity_down[t] * g.max_capacity_down

                    # add constraint
                    block.dsm_down_constraint.add((g, t), (lhs <= rhs))

        self.dsm_down_constraint = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.dsm_down_constraint_build = BuildAction(
            rule=dsm_down_constraint_rule
        )

        def dsm_sum_constraint_rule(block):
            """Relation to compensate the total amount of positive
            and negative DSM in between the shift_interval.
            This constraint is building balance in full intervals starting
            with index 0. The last interval might not be full.
            """
            for g in group:
                intervals = range(m.TIMESTEPS[1],
                                  m.TIMESTEPS[-1],
                                  g.shift_interval)

                for interval in intervals:
                    if (interval + g.shift_interval - 1) > m.TIMESTEPS[-1]:
                        timesteps = range(interval,
                                          m.TIMESTEPS[-1] + 1)
                    else:
                        timesteps = range(
                            interval, interval + g.shift_interval
                        )

                    # DSM up/down
                    lhs = sum(self.dsm_up[g, tt]
                              for tt in timesteps) * g.efficiency
                    # value
                    rhs = sum(self.dsm_do_shift[g, tt]
                              for tt in timesteps)

                    # add constraint
                    block.dsm_sum_constraint.add((g, interval), (lhs == rhs))

        self.dsm_sum_constraint = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.dsm_sum_constraint_build = BuildAction(
            rule=dsm_sum_constraint_rule
        )

    def _objective_expression(self):
        r"""Objective expression with variable costs for DSM activity
        """

        m = self.parent_block()

        dsm_cost = 0

        for t in m.TIMESTEPS:
            for g in self.dsm:
                dsm_cost += (
                    self.dsm_up[g, t]
                    * m.objective_weighting[t]
                    * g.cost_dsm_up[t]
                )
                dsm_cost += (
                    (self.dsm_do_shift[g, t] * g.cost_dsm_down_shift[t]
                     + self.dsm_do_shed[g, t] * g.cost_dsm_down_shed[t])
                    * m.objective_weighting[t]
                )

        self.cost = Expression(expr=dsm_cost)

        return self.cost


class SinkDSMOemofMultiPeriodBlock(SimpleBlock):
    r"""Constraints for SinkDSM with "oemof" approach and :attr:`multiperiod`

    **The following constraints are created for approach = 'oemof' with a
    multiperiod attribute:**

    .. _SinkDSMOemof equations:

    .. math::
        &
        (1) \quad DSM_{t}^{up} = 0 \quad \forall t
        \quad if \space eligibility_{shift} = False \\
        &
        (2) \quad DSM_{t}^{do, shed} = 0 \quad \forall t
        \quad if \space eligibility_{shed} = False \\
        &
        (3) \quad \dot{E}_{t} = demand_{t} \cdot demand_{max} + DSM_{t}^{up}
        - DSM_{t}^{do, shift} - DSM_{t}^{do, shed}
        \quad \forall t \in \mathbb{T} \\
        &
        (4) \quad  DSM_{t}^{up} \leq E_{t}^{up} \cdot E_{up, max}
        \quad \forall t \in \mathbb{T} \\
        &
        (5) \quad DSM_{t}^{do, shift} + DSM_{t}^{do, shed}
        \leq  E_{t}^{do} \cdot E_{do, max}
        \quad \forall t \in \mathbb{T} \\
        &
        (6) \quad  \sum_{t=t_s}^{t_s+\tau} DSM_{t}^{up} \cdot \eta =
        \sum_{t=t_s}^{t_s+\tau} DSM_{t}^{do, shift} \quad \forall t_s \in
        \{k \in \mathbb{T} \mid k \mod \tau = 0\} \\
        &

    **The following parts of the objective function are created:**

    .. math::
        DSM_{t}^{up} \cdot cost_{t}^{dsm, up}
        + DSM_{t}^{do, shift} \cdot cost_{t}^{dsm, do, shift}
        + DSM_{t}^{do, shed} \cdot cost_{t}^{dsm, do, shed}
        \quad \forall t \in \mathbb{T} \\

    **Table: Symbols and attribute names of variables and parameters**

        .. csv-table:: Variables (V) and Parameters (P)
            :header: "symbol", "attribute", "type", "explanation"
            :widths: 1, 1, 1, 1

            ":math:`DSM_{t}^{up}` ",
            ":attr:`~SinkDSM.dsm_up[g, t]` ","V", "DSM
            up shift (capacity shifted upwards)"
            ":math:`DSM_{t}^{do, shift}` ",
            ":attr:`~SinkDSM.dsm_do_shift[g, t]` ",
            "V","DSM down shift (capacity shifted downwards)"
            ":math:`DSM_{t}^{do, shed}` ",
            ":attr:`~SinkDSM.dsm_do_shed[g, t]` ",
            "V","DSM shedded (capacity shedded, i.e. not compensated for)"
            ":math:`\dot{E}_{t}`",":attr:`~SinkDSM.inputs`","V", "Energy
            flowing in from (electrical) inflow bus"
            ":math:`demand_{t}`",":attr:`~SinkDSM.demand[t]`","P",
            "(Electrical) demand series (normalized)"
            ":math:`demand_{max}`",":attr:`~SinkDSM.max_demand`","P",
            "Maximum demand value"
            ":math:`E_{t}^{do}`",":attr:`~SinkDSM.capacity_down[t]`","P",
            "Capacity  allowed for a load adjustment downwards (normalized)
            (DSM down shift + DSM shedded)"
            ":math:`E_{t}^{up}`",":attr:`~SinkDSM.capacity_up[t]`","P",
            "Capacity allowed for a shift upwards (normalized) (DSM up shift)"
            ":math:`E_{do, max}`",":attr:`~SinkDSM.max_capacity_down`","P",
            "Maximum capacity allowed for a load adjustment downwards
            (DSM down shift + DSM shedded)"
            ":math:`E_{up, max}`",":attr:`~SinkDSM.max_capacity_up`","P",
            "Capacity allowed for a shift upwards (normalized) (DSM up shift)"
            ":math:`\tau`",":attr:`~SinkDSM.shift_interval`","P", "Shift
            interval (time within which the energy balance must be
            levelled out"
            ":math:`\eta`",":attr:`~SinkDSM.efficiency`","P", "Efficiency
            loss forload shifting processes"
            ":math:`\eta`",":attr:`efficiency`","P", "Efficiency loss for
            load shifting processes"
            ":math:`\mathbb{T}` "," ","P", "Time steps"
            ":math:`eligibility_{shift}` ",
            ":attr:`~SinkDSM.shift_eligibility`","P",
            "Boolean parameter indicating if unit can be used for
            load shifting"
            ":math:`eligibility_{shed}` ",
            ":attr:`~SinkDSM.shed_eligibility`","P",
            "Boolean parameter indicating if unit can be used for
            load shedding"
            ":math:`cost_{t}^{dsm, up}` ", ":attr:`~SinkDSM.cost_dsm_up[t]`",
            "P", "Variable costs for an upwards shift"
            ":math:`cost_{t}^{dsm, do, shift}` ",
            ":attr:`~SinkDSM.cost_dsm_down_shift[t]`","P",
            "Variable costs for a downwards shift (load shifting)"
            ":math:`cost_{t}^{dsm, do, shed}` ",
            ":attr:`~SinkDSM.cost_dsm_down_shed[t]`","P",
            "Variable costs for shedding load"
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all DSM components get inflow from a bus
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        # Set of DSM Components
        self.multiperioddsm = Set(initialize=[n for n in group])

        #  ************* VARIABLES *****************************

        # Variable load shift down
        self.dsm_do_shift = Var(
            self.multiperioddsm, m.TIMESTEPS, initialize=0,
            within=NonNegativeReals
        )

        # Variable load shedding
        self.dsm_do_shed = Var(
            self.multiperioddsm, m.TIMESTEPS, initialize=0,
            within=NonNegativeReals)

        # Variable load shift up
        self.dsm_up = Var(
            self.multiperioddsm, m.TIMESTEPS, initialize=0,
            within=NonNegativeReals
        )

        #  ************* CONSTRAINTS *****************************

        def _shift_shed_vars_rule(block):
            """Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if not g.shift_eligibility:
                        lhs = self.dsm_up[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

                    if not g.shed_eligibility:
                        lhs = self.dsm_do_shed[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Demand Production Relation
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DSM.
            Generator Production == Demand_el +- DSM
            """
            for p, t in m.TIMEINDEX:
                for g in group:
                    # Inflow from bus
                    lhs = m.flow[g.inflow, g, p, t]

                    # Demand + DSM_up - DSM_down
                    rhs = (g.demand[t] * g.max_demand
                           + self.dsm_up[g, t] - self.dsm_do_shift[g, t]
                           - self.dsm_do_shed[g, t])

                    # add constraint
                    block.input_output_relation.add((g, p, t), (lhs == rhs))

        self.input_output_relation = Constraint(
            group, m.TIMEINDEX, noruleinit=True
        )
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule
        )

        # Upper bounds relation
        def dsm_up_constraint_rule(block):
            """Realised upward load shift at time t has to be smaller than
            upward DSM capacity at time t.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # DSM up
                    lhs = self.dsm_up[g, t]
                    # Capacity dsm_up
                    rhs = g.capacity_up[t] * g.max_capacity_up

                    # add constraint
                    block.dsm_up_constraint.add((g, t), (lhs <= rhs))

        self.dsm_up_constraint = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.dsm_up_constraint_build = BuildAction(rule=dsm_up_constraint_rule)

        # Upper bounds relation
        def dsm_down_constraint_rule(block):
            """Realised downward load shift at time t has to be smaller than
            downward DSM capacity at time t.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # DSM down
                    lhs = self.dsm_do_shift[g, t] + self.dsm_do_shed[g, t]
                    # Capacity dsm_down
                    rhs = g.capacity_down[t] * g.max_capacity_down

                    # add constraint
                    block.dsm_down_constraint.add((g, t), (lhs <= rhs))

        self.dsm_down_constraint = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.dsm_down_constraint_build = BuildAction(
            rule=dsm_down_constraint_rule
        )

        def dsm_sum_constraint_rule(block):
            """Relation to compensate the total amount of positive
            and negative DSM in between the shift_interval.
            This constraint is building balance in full intervals starting
            with index 0. The last interval might not be full.
            """
            for g in group:
                intervals = range(m.TIMESTEPS[1],
                                  m.TIMESTEPS[-1],
                                  g.shift_interval)

                for interval in intervals:
                    if (interval + g.shift_interval - 1) > m.TIMESTEPS[-1]:
                        timesteps = range(interval,
                                          m.TIMESTEPS[-1] + 1)
                    else:
                        timesteps = range(
                            interval, interval + g.shift_interval
                        )

                    # DSM up/down
                    lhs = sum(self.dsm_up[g, tt]
                              for tt in timesteps) * g.efficiency
                    # value
                    rhs = sum(self.dsm_do_shift[g, tt]
                              for tt in timesteps)

                    # add constraint
                    block.dsm_sum_constraint.add((g, interval), (lhs == rhs))

        self.dsm_sum_constraint = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.dsm_sum_constraint_build = BuildAction(
            rule=dsm_sum_constraint_rule
        )

    def _objective_expression(self):
        r"""Objective expression with variable, investment and fixed costs
        for DSM """

        m = self.parent_block()

        variable_costs = 0
        fixed_costs = 0

        for g in self.multiperioddsm:
            for p, t in m.TIMEINDEX:
                variable_costs += (self.dsm_up[g, t]
                                   * m.objective_weighting[t]
                                   * g.cost_dsm_up[p]
                                   * ((1 + m.discount_rate) ** -p))
                variable_costs += (self.dsm_do_shift[g, t]
                                   * m.objective_weighting[t]
                                   * g.cost_dsm_down_shift[p]
                                   * ((1 + m.discount_rate) ** -p))

            if g.fixed_costs[0] is not None:
                for p in m.PERIODS:
                    fixed_costs += (
                        g.max_demand
                        * g.fixed_costs[p]
                        * ((1 + m.discount_rate) ** (-p))
                    )

        self.cost = Expression(expr=variable_costs + fixed_costs)

        return self.cost


class SinkDSMOemofInvestmentBlock(SimpleBlock):
    r"""Constraints for SinkDSM with "oemof" approach and :attr:`investment`

    **The following constraints are created for approach = 'oemof' with an
    investment object defined:**

    .. _SinkDSMOemof equations:

    .. math::
        &
        (1) \quad invest_{min} \leq invest \leq invest_{max} \\
        &
        (2) \quad DSM_{t}^{up} = 0 \quad \forall t
        \quad if \space eligibility_{shift} = False \\
        &
        (3) \quad DSM_{t}^{do, shed} = 0 \quad \forall t
        \quad if \space eligibility_{shed} = False \\
        &
        (4) \quad \dot{E}_{t} = demand_{t} \cdot (invest + E_{exist})
        + DSM_{t}^{up}
        - DSM_{t}^{do, shift} - DSM_{t}^{do, shed}
        \quad \forall t \in \mathbb{T} \\
        &
        (5) \quad  DSM_{t}^{up} \leq E_{t}^{up} \cdot (invest + E_{exist})
        \cdot s_{flex, up}
        \quad \forall t \in \mathbb{T} \\
        &
        (6) \quad DSM_{t}^{do, shift} +  DSM_{t}^{do, shed} \leq
        E_{t}^{do} \cdot (invest + E_{exist}) \cdot s_{flex, do}
        \quad \forall t \in \mathbb{T} \\
        &
        (7) \quad  \sum_{t=t_s}^{t_s+\tau} DSM_{t}^{up} \cdot \eta =
        \sum_{t=t_s}^{t_s+\tau} DSM_{t}^{do, shift} \quad \forall t_s \in
        \{k \in \mathbb{T} \mid k \mod \tau = 0\} \\
        &

    **The following parts of the objective function are created:**

    * Investment annuity:

    .. math::
        invest \cdot costs_{invest} \\

    * Variable costs:

    .. math::
        DSM_{t}^{up} \cdot cost_{t}^{dsm, up}
        + DSM_{t}^{do, shift} \cdot cost_{t}^{dsm, do, shift}
        + DSM_{t}^{do, shed} \cdot cost_{t}^{dsm, do, shed}
        \quad  \forall t \in \mathbb{T} \\

    See remarks in :class:`oemof.solph.custom.SinkDSMOemofBlock`.

    **Symbols and attribute names of variables and parameters**

    Please refer to :class:`oemof.solph.custom.SinkDSMOemofBlock`.

    The following variables and parameters are exclusively used for
    investment modeling:

        .. csv-table:: Variables (V) and Parameters (P)
            :header: "symbol", "attribute", "type", "explanation"
            :widths: 1, 1, 1, 1

            ":math:`invest` ",":attr:`~SinkDSM.invest` ","V", "DSM capacity
            invested in. Equals to the additionally installed capacity.
            The capacity share eligible for a shift is determined
            by flex share(s)."
            ":math:`invest_{min}` ", ":attr:`~SinkDSM.investment.minimum` ",
            "P", "minimum investment"
            ":math:`invest_{max}` ", ":attr:`~SinkDSM.investment.maximum` ",
            "P", "maximum investment"
            ":math:`E_{exist}` ",":attr:`~SinkDSM.investment.existing` ",
            "P", "existing DSM capacity"
            ":math:`s_{flex, up}` ",":attr:`~SinkDSM.flex_share_up` ",
            "P","Share of invested capacity that may be shift upwards
            at maximum"
            ":math:`s_{flex, do}` ",":attr:`~SinkDSM.flex_share_do` ",
            "P", "Share of invested capacity that may be shift downwards
            at maximum"
            ":math:`costs_{invest}` ",":attr:`~SinkDSM.investment.epcosts` ",
            "P", "specific investment annuity"
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all DSM components get inflow from a bus
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        # Set of DSM Components
        self.investdsm = Set(initialize=[n for n in group])

        #  ************* VARIABLES *****************************

        # Define bounds for investments in demand response
        def _dsm_investvar_bound_rule(block, g):
            """Rule definition to bound the
            invested demand response capacity `invest`.
            """
            return g.investment.minimum, g.investment.maximum

        # Investment in DR capacity
        self.invest = Var(self.investdsm,
                          within=NonNegativeReals,
                          bounds=_dsm_investvar_bound_rule)

        # Variable load shift down
        self.dsm_do_shift = Var(self.investdsm, m.TIMESTEPS, initialize=0,
                                within=NonNegativeReals)

        # Variable load shedding
        self.dsm_do_shed = Var(
            self.investdsm, m.TIMESTEPS, initialize=0,
            within=NonNegativeReals)

        # Variable load shift up
        self.dsm_up = Var(self.investdsm, m.TIMESTEPS, initialize=0,
                          within=NonNegativeReals)

        #  ************* CONSTRAINTS *****************************

        def _shift_shed_vars_rule(block):
            """Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if not g.shift_eligibility:
                        lhs = self.dsm_up[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

                    if not g.shed_eligibility:
                        lhs = self.dsm_do_shed[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Demand Production Relation
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DSM.
            Generator Production == Demand_el +- DSM
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # Inflow from bus
                    lhs = m.flow[g.inflow, g, t]

                    # Demand + DSM_up - DSM_down
                    rhs = (g.demand[t]
                           * (self.invest[g] + g.investment.existing)
                           + self.dsm_up[g, t] - self.dsm_do_shift[g, t]
                           - self.dsm_do_shed[g, t])

                    # add constraint
                    block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation = Constraint(group, m.TIMESTEPS,
                                                noruleinit=True)
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule)

        # Upper bounds relation
        def dsm_up_constraint_rule(block):
            """Realised upward load shift at time t has to be smaller than
            upward DSM capacity at time t.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # DSM up
                    lhs = self.dsm_up[g, t]
                    # Capacity dsm_up
                    rhs = (g.capacity_up[t]
                           * (self.invest[g] + g.investment.existing)
                           * g.flex_share_up)

                    # add constraint
                    block.dsm_up_constraint.add((g, t), (lhs <= rhs))

        self.dsm_up_constraint = Constraint(group, m.TIMESTEPS,
                                            noruleinit=True)
        self.dsm_up_constraint_build = BuildAction(rule=dsm_up_constraint_rule)

        # Upper bounds relation
        def dsm_down_constraint_rule(block):
            """Realised downward load shift at time t has to be smaller than
            downward DSM capacity at time t.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # DSM down
                    lhs = self.dsm_do_shift[g, t] + self.dsm_do_shed[g, t]
                    # Capacity dsm_down
                    rhs = (g.capacity_down[t]
                           * (self.invest[g] + g.investment.existing)
                           * g.flex_share_down)

                    # add constraint
                    block.dsm_down_constraint.add((g, t), (lhs <= rhs))

        self.dsm_down_constraint = Constraint(group, m.TIMESTEPS,
                                              noruleinit=True)
        self.dsm_down_constraint_build = BuildAction(
            rule=dsm_down_constraint_rule)

        def dsm_sum_constraint_rule(block):
            """Relation to compensate the total amount of positive
            and negative DSM in between the shift_interval.
            This constraint is building balance in full intervals starting
            with index 0. The last interval might not be full.
            """
            for g in group:
                intervals = range(m.TIMESTEPS[1],
                                  m.TIMESTEPS[-1],
                                  g.shift_interval)

                for interval in intervals:
                    if (interval + g.shift_interval - 1) > m.TIMESTEPS[-1]:
                        timesteps = range(interval,
                                          m.TIMESTEPS[-1] + 1)
                    else:
                        timesteps = range(interval,
                                          interval + g.shift_interval)

                    # DSM up/down
                    lhs = sum(self.dsm_up[g, tt]
                              for tt in timesteps) * g.efficiency
                    # value
                    rhs = sum(self.dsm_do_shift[g, tt]
                              for tt in timesteps)

                    # add constraint
                    block.dsm_sum_constraint.add((g, interval), (lhs == rhs))

        self.dsm_sum_constraint = Constraint(group, m.TIMESTEPS,
                                             noruleinit=True)
        self.dsm_sum_constraint_build = BuildAction(
            rule=dsm_sum_constraint_rule)

    def _objective_expression(self):
        r"""Objective expression with variable and investment costs for DSM
        """

        m = self.parent_block()

        investment_costs = 0
        variable_costs = 0

        for g in self.investdsm:
            if g.investment.ep_costs is not None:
                investment_costs += self.invest[g] * g.investment.ep_costs
            else:
                raise ValueError("Missing value for investment costs!")
            for t in m.TIMESTEPS:
                variable_costs += self.dsm_up[g, t] * g.cost_dsm_up[t]
                variable_costs += (
                    self.dsm_do_shift[g, t]
                    * g.cost_dsm_down_shift[t]
                    + self.dsm_do_shed[g, t]
                    * g.cost_dsm_down_shed[t]
                )

        self.cost = Expression(
            expr=investment_costs + variable_costs
        )

        return self.cost


class SinkDSMOemofMultiPeriodInvestmentBlock(SimpleBlock):
    r"""Constraints for SinkDSM with "oemof" approach and
    :attr:`multiperiodinvestment`

    **The following constraints are created for approach = 'oemof' with a
    multiperiodinvestment object defined:**

    .. _SinkDSMOemof equations:

    .. math::
        &
        (1) \quad invest_{min} \leq invest \leq invest_{max} \\
        &
        (2) \quad DSM_{t}^{up} = 0 \quad \forall t
        \quad if \space eligibility_{shift} = False \\
        &
        (3) \quad DSM_{t}^{do, shed} = 0 \quad \forall t
        \quad if \space eligibility_{shed} = False \\
        &
        (4) \quad \dot{E}_{t} = demand_{t} \cdot (invest + E_{exist})
        + DSM_{t}^{up}
        - DSM_{t}^{do, shift} - DSM_{t}^{do, shed}
        \quad \forall t \in \mathbb{T} \\
        &
        (5) \quad  DSM_{t}^{up} \leq E_{t}^{up} \cdot (invest + E_{exist})
        \cdot s_{flex, up}
        \quad \forall t \in \mathbb{T} \\
        &
        (6) \quad DSM_{t}^{do, shift} +  DSM_{t}^{do, shed} \leq
        E_{t}^{do} \cdot (invest + E_{exist}) \cdot s_{flex, do}
        \quad \forall t \in \mathbb{T} \\
        &
        (7) \quad  \sum_{t=t_s}^{t_s+\tau} DSM_{t}^{up} \cdot \eta =
        \sum_{t=t_s}^{t_s+\tau} DSM_{t}^{do, shift} \quad \forall t_s \in
        \{k \in \mathbb{T} \mid k \mod \tau = 0\} \\
        &

    **The following parts of the objective function are created:**

    * Investment annuity:

    .. math::
        invest \cdot costs_{invest} \\

    * Variable costs:

    .. math::
        DSM_{t}^{up} \cdot cost_{t}^{dsm, up}
        + DSM_{t}^{do, shift} \cdot cost_{t}^{dsm, do, shift}
        + DSM_{t}^{do, shed} \cdot cost_{t}^{dsm, do, shed}
        \quad  \forall t \in \mathbb{T} \\

    See remarks in :class:`oemof.solph.custom.SinkDSMOemofBlock`.

    **Symbols and attribute names of variables and parameters**

    Please refer to :class:`oemof.solph.custom.SinkDSMOemofBlock`.

    The following variables and parameters are exclusively used for
    investment modeling:

        .. csv-table:: Variables (V) and Parameters (P)
            :header: "symbol", "attribute", "type", "explanation"
            :widths: 1, 1, 1, 1

            ":math:`invest` ",":attr:`~SinkDSM.invest` ","V", "DSM capacity
            invested in. Equals to the additionally installed capacity.
            The capacity share eligible for a shift is determined
            by flex share(s)."
            ":math:`invest_{min}` ", ":attr:`~SinkDSM.investment.minimum` ",
            "P", "minimum investment"
            ":math:`invest_{max}` ", ":attr:`~SinkDSM.investment.maximum` ",
            "P", "maximum investment"
            ":math:`E_{exist}` ",":attr:`~SinkDSM.investment.existing` ",
            "P", "existing DSM capacity"
            ":math:`s_{flex, up}` ",":attr:`~SinkDSM.flex_share_up` ",
            "P","Share of invested capacity that may be shift upwards
            at maximum"
            ":math:`s_{flex, do}` ",":attr:`~SinkDSM.flex_share_do` ",
            "P", "Share of invested capacity that may be shift downwards
            at maximum"
            ":math:`costs_{invest}` ",":attr:`~SinkDSM.investment.epcosts` ",
            "P", "specific investment annuity"
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all DSM components get inflow from bus_elec
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        # Set of DSM Components
        self.multiperiodinvestdsm = Set(initialize=[n for n in group])

        #  ************* VARIABLES *****************************

        # Define bounds for investments in demand response
        def _dsm_investvar_bound_rule(block, g, p):
            """
            Rule definition to bound the
            invested demand response capacity `invest`.
            """
            return (g.multiperiodinvestment.minimum[p],
                    g.multiperiodinvestment.maximum[p])

        # Investment in DR capacity
        self.invest = Var(self.multiperiodinvestdsm,
                          m.PERIODS,
                          within=NonNegativeReals,
                          bounds=_dsm_investvar_bound_rule)

        # Total capacity
        self.total = Var(self.multiperiodinvestdsm,
                         m.PERIODS,
                         within=NonNegativeReals)

        # Old capacity to be decommissioned (due to lifetime)
        # Old capacity is built out of old exogenous and endogenous capacities
        self.old = Var(self.multiperiodinvestdsm,
                       m.PERIODS,
                       within=NonNegativeReals)

        # Old endogenous capacity to be decommissioned (due to lifetime)
        self.old_end = Var(self.multiperiodinvestdsm,
                           m.PERIODS,
                           within=NonNegativeReals)

        # Old exogenous capacity to be decommissioned (due to lifetime)
        self.old_exo = Var(self.multiperiodinvestdsm,
                           m.PERIODS,
                           within=NonNegativeReals)

        # Variable load shift down
        self.dsm_do_shift = Var(self.multiperiodinvestdsm, m.TIMESTEPS,
                                initialize=0,
                                within=NonNegativeReals)

        # Variable load shedding
        self.dsm_do_shed = Var(
            self.multiperioddsm, m.TIMESTEPS, initialize=0,
            within=NonNegativeReals)

        # Variable load shift up
        self.dsm_up = Var(self.multiperiodinvestdsm, m.TIMESTEPS,
                          initialize=0,
                          within=NonNegativeReals)

        #  ************* CONSTRAINTS *****************************

        # Handle unit lifetimes
        def _total_dsm_capacity_rule(block):
            """Rule definition for determining total installed
            capacity (taking decommissioning into account)
            """
            for g in group:
                for p in m.PERIODS:
                    if p == 0:
                        expr = (self.total[g, p]
                                == self.invest[g, p]
                                + g.multiperiodinvestment.existing)
                        self.total_dsm_rule.add((g, p), expr)
                    else:
                        expr = (self.total[g, p]
                                == self.invest[g, p]
                                + self.total[g, p - 1]
                                - self.old[g, p])
                        self.total_dsm_rule.add((g, p), expr)

        self.total_dsm_rule = Constraint(group, m.PERIODS,
                                         noruleinit=True)
        self.total_dsm_rule_build = BuildAction(
            rule=_total_dsm_capacity_rule)

        def _old_dsm_capacity_rule_end(block):
            """Rule definition for determining old endogenously installed
            capacity to be decommissioned due to reaching its lifetime
            """
            for g in group:
                lifetime = g.multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    if lifetime <= p:
                        expr = (self.old_end[g, p]
                                == self.invest[g, p - lifetime])
                        self.old_dsm_rule_end.add((g, p), expr)
                    else:
                        expr = (self.old_end[g, p]
                                == 0)
                        self.old_dsm_rule_end.add((g, p), expr)

        self.old_dsm_rule_end = Constraint(group,
                                           m.PERIODS,
                                           noruleinit=True)
        self.old_dsm_rule_end_build = BuildAction(
            rule=_old_dsm_capacity_rule_end)

        def _old_dsm_capacity_rule_exo(block):
            """Rule definition for determining old exogenously given capacity
            to be decommissioned due to reaching its lifetime
            """
            for g in group:
                age = g.multiperiodinvestment.age
                lifetime = g.multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    if lifetime - age == p:
                        expr = (
                            self.old_exo[g, p]
                            == g.multiperiodinvestment.existing)
                        self.old_dsm_rule_exo.add((g, p), expr)
                    else:
                        expr = (self.old_exo[g, p]
                                == 0)
                        self.old_dsm_rule_exo.add((g, p), expr)

        self.old_dsm_rule_exo = Constraint(group,
                                           m.PERIODS,
                                           noruleinit=True)
        self.old_dsm_rule_exo_build = BuildAction(
            rule=_old_dsm_capacity_rule_exo)

        def _old_dsm_capacity_rule(block):
            """Rule definition for determining (overall) old capacity
            to be decommissioned due to reaching its lifetime
            """
            for g in group:
                for p in m.PERIODS:
                    expr = (
                        self.old[g, p]
                        == self.old_end[g, p] + self.old_exo[g, p])
                    self.old_dsm_rule.add((g, p), expr)

        self.old_dsm_rule = Constraint(group,
                                       m.PERIODS,
                                       noruleinit=True)
        self.old_dsm_rule_build = BuildAction(
            rule=_old_dsm_capacity_rule)

        def _shift_shed_vars_rule(block):
            """Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if not g.shift_eligibility:
                        lhs = self.dsm_up[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

                    if not g.shed_eligibility:
                        lhs = self.dsm_do_shed[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Demand Production Relation
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DSM.
            Generator Production == Demand_el +- DSM
            """
            for p, t in m.TIMEINDEX:
                for g in group:
                    # Inflow from bus
                    lhs = m.flow[g.inflow, g, p, t]

                    # Demand + DSM_up - DSM_down
                    rhs = (g.demand[t] * self.total[g, p]
                           + self.dsm_up[g, t] - self.dsm_do_shift[g, t]
                           - self.dsm_do_shed[g, t])

                    # add constraint
                    block.input_output_relation.add((g, p, t), (lhs == rhs))

        self.input_output_relation = Constraint(
            group, m.TIMEINDEX, noruleinit=True
        )
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule
        )

        # Upper bounds relation
        def dsm_up_constraint_rule(block):
            """Realised upward load shift at time t has to be smaller than
            upward DSM capacity at time t.
            """

            for p, t in m.TIMEINDEX:
                for g in group:
                    # DSM up
                    lhs = self.dsm_up[g, t]
                    # Capacity dsm_up
                    rhs = (g.capacity_up[t] * self.total[g, p]
                           * g.flex_share_up)

                    # add constraint
                    block.dsm_up_constraint.add((g, p, t), (lhs <= rhs))

        self.dsm_up_constraint = Constraint(group, m.TIMEINDEX,
                                            noruleinit=True)
        self.dsm_up_constraint_build = BuildAction(rule=dsm_up_constraint_rule)

        # Upper bounds relation
        def dsm_down_constraint_rule(block):
            """Realised downward load shift at time t has to be smaller than
            downward DSM capacity at time t.
            """
            for p, t in m.TIMEINDEX:
                for g in group:
                    # DSM down
                    lhs = self.dsm_do_shift[g, t] + self.dsm_do_shed[g, t]
                    # Capacity dsm_down
                    rhs = (g.capacity_down[t] * self.total[g, p]
                           * g.flex_share_down)

                    # add constraint
                    block.dsm_down_constraint.add((g, p, t), (lhs <= rhs))

        self.dsm_down_constraint = Constraint(group, m.TIMEINDEX,
                                              noruleinit=True)
        self.dsm_down_constraint_build = BuildAction(
            rule=dsm_down_constraint_rule)

        def dsm_sum_constraint_rule(block):
            """Relation to compensate the total amount of positive
            and negative DSM in between the shift_interval.
            This constraint is building balance in full intervals starting
            with index 0. The last interval might not be full.
            """
            for g in group:
                intervals = range(m.TIMESTEPS[1],
                                  m.TIMESTEPS[-1],
                                  g.shift_interval)

                for interval in intervals:
                    if (interval + g.shift_interval - 1) > m.TIMESTEPS[-1]:
                        timesteps = range(interval,
                                          m.TIMESTEPS[-1] + 1)
                    else:
                        timesteps = range(interval, interval
                                          + g.shift_interval)

                    # DSM up/down
                    lhs = sum(self.dsm_up[g, tt]
                              for tt in timesteps) * g.efficiency
                    # value
                    rhs = sum(self.dsm_do_shift[g, tt]
                              for tt in timesteps)

                    # add constraint
                    block.dsm_sum_constraint.add((g, interval), (lhs == rhs))

        self.dsm_sum_constraint = Constraint(group, m.TIMESTEPS,
                                             noruleinit=True)
        self.dsm_sum_constraint_build = BuildAction(
            rule=dsm_sum_constraint_rule)

    def _objective_expression(self):
        r"""Objective expression with variable, investment and fixed costs
        for DSM"""

        m = self.parent_block()

        investment_costs = 0
        variable_costs = 0
        fixed_costs = 0

        for g in self.multiperiodinvestdsm:
            if g.multiperiodinvestment.ep_costs is not None:
                lifetime = g.multiperiodinvestment.lifetime
                interest = g.multiperiodinvestment.interest_rate
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
                        capex=g.multiperiodinvestment.ep_costs[p],
                        n=lifetime,
                        wacc=interest)
                    investment_costs += (
                        self.invest[g, p] * annuity * lifetime
                        * ((1 + m.discount_rate) ** (-p))
                    )
            else:
                raise ValueError("Missing value for investment costs!")
            for p, t in m.TIMEINDEX:
                variable_costs += (self.dsm_up[g, t]
                                   * m.objective_weighting[t]
                                   * g.cost_dsm_up[p]
                                   * ((1 + m.discount_rate) ** -p))
                variable_costs += ((self.dsm_do_shift[g, t]
                                    * g.cost_dsm_down_shift[p]
                                    + self.dsm_do_shed[g, t]
                                    * g.cost_dsm_down_shed[p])
                                   * m.objective_weighting[t]
                                   * ((1 + m.discount_rate) ** -p))

            if g.multiperiodinvestment.fixed_costs[0] is not None:
                lifetime = g.multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    fixed_costs += (
                        sum(self.invest[g, p]
                            * g.multiperiodinvestment.fixed_costs[pp]
                            * ((1 + m.discount_rate) ** (-pp))
                            for pp in range(p, p + lifetime)
                            )
                        * ((1 + m.discount_rate) ** (-p))
                    )

        self.cost = Expression(
            expr=investment_costs + fixed_costs + variable_costs
        )

        return self.cost


class SinkDSMDIWBlock(SimpleBlock):
    r"""Constraints for SinkDSM with "DIW" approach

    **The following constraints are created for approach = 'DIW':**

    .. _SinkDSMDIW equations:

    .. math::
        &
        (1) \quad DSM_{t}^{up} = 0 \quad \forall t
        \quad if \space eligibility_{shift} = False \\
        &
        (2) \quad DSM_{t}^{do, shed} = 0 \quad \forall t
        \quad if \space eligibility_{shed} = False \\
        &
        (3) \quad \dot{E}_{t} = demand_{t} \cdot demand_{max} + DSM_{t}^{up} -
        \sum_{tt=t-L}^{t+L} DSM_{tt,t}^{do, shift} - DSM_{t}^{do, shed} \quad
        \forall t \in \mathbb{T} \\
        &
        (4) \quad DSM_{t}^{up} \cdot \eta =
        \sum_{tt=t-L}^{t+L} DSM_{t,tt}^{do, shift}
        \quad \forall t \in \mathbb{T} \\
        &
        (5) \quad DSM_{t}^{up} \leq  E_{t}^{up} \cdot E_{up, max}
        \quad \forall t \in \mathbb{T} \\
        &
        (6) \quad \sum_{t=tt-L}^{tt+L} DSM_{t,tt}^{do, shift}
        + DSM_{tt}^{do, shed} \leq E_{tt}^{do} \cdot E_{do, max}
        \quad \forall tt \in \mathbb{T} \\
        &
        (7) \quad DSM_{tt}^{up} + \sum_{t=tt-L}^{tt+L} DSM_{t,tt}^{do, shift}
        + DSM_{tt}^{do, shed} \leq
        max \{ E_{tt}^{up} \cdot E_{up, max}, E_{tt}^{do} \cdot E_{do, max} \}
        \quad \forall tt \in \mathbb{T} \\
        &
        (8) \quad \sum_{tt=t}^{t+R-1} DSM_{tt}^{up}
        \leq E_{t}^{up} \cdot E_{up, max} \cdot L \cdot \Delta t
        \quad \forall t \in \mathbb{T} \\
        &
        (9) \quad \sum_{tt=t}^{t+R-1} DSM_{tt}^{do, shed}
        \leq E_{t}^{do} \cdot E_{do, max} \cdot t_{shed} \cdot \Delta t
        \quad \forall t \in \mathbb{T} \\
        &

    *Note*: For the sake of readability, the handling of indices is not
    displayed here. E.g. evaluating a variable for t-L may lead to a negative
    and therefore infeasible index.
    This is addressed by limiting the sums to non-negative indices within the
    model index bounds. Please refer to the constraints implementation
    themselves.

    **The following parts of the objective function are created:**

    .. math::
        DSM_{t}^{up} \cdot cost_{t}^{dsm, up}
        + \sum_{tt=0}^{|T|} DSM_{t, tt}^{do, shift} \cdot
        cost_{t}^{dsm, do, shift}
        + DSM_{t}^{do, shed} \cdot cost_{t}^{dsm, do, shed}
        \quad \forall t \in \mathbb{T} \\

    **Table: Symbols and attribute names of variables and parameters**

        .. csv-table:: Variables (V) and Parameters (P)
            :header: "symbol", "attribute", "type", "explanation"
            :widths: 1, 1, 1, 1

            ":math:`DSM_{t}^{up}` ",":attr:`~SinkDSM.dsm_up[g,t]`",
            "V", "DSM up shift (additional load) in hour t"
            ":math:`DSM_{t,tt}^{do, shift}` ",
            ":attr:`~SinkDSM.dsm_do_shift[g,t,tt]`",
            "V", "DSM down shift (less load) in hour tt
            to compensate for upwards shifts in hour t"
            ":math:`DSM_{t}^{do, shed}` ",":attr:`~SinkDSM.dsm_do_shed[g,t]` ",
            "V","DSM shedded (capacity shedded, i.e. not compensated for)"
            ":math:`\dot{E}_{t}` ",":attr:`flow[g,t]`","V","Energy
            flowing in from (electrical) inflow bus"
            ":math:`L`",":attr:`~SinkDSM.delay_time`","P",
            "Maximum delay time for load shift
            (time until the energy balance has to be levelled out again;
            roundtrip time of one load shifting cycle, i.e. time window
            for upshift and compensating downshift)"
            ":math:`t_{she}`",":attr:`~SinkDSM.shed_time`","P",
            "Maximum time for one load shedding process"
            ":math:`demand_{t}`",":attr:`~SinkDSM.demand[t]`","P",
            "(Electrical) demand series (normalized)"
            ":math:`demand_{max}`",":attr:`~SinkDSM.max_demand`","P",
            "Maximum demand value"
            ":math:`E_{t}^{do}`",":attr:`~SinkDSM.capacity_down[t]`","P",
            "Capacity  allowed for a load adjustment downwards (normalized)
            (DSM down shift + DSM shedded)"
            ":math:`E_{t}^{up}`",":attr:`~SinkDSM.capacity_up[t]`","P",
            "Capacity allowed for a shift upwards (normalized) (DSM up shift)"
            ":math:`E_{do, max}`",":attr:`~SinkDSM.max_capacity_down`","P",
            "Maximum capacity allowed for a load adjustment downwards
            (DSM down shift + DSM shedded)"
            ":math:`E_{up, max}`",":attr:`~SinkDSM.max_capacity_up`","P",
            "Capacity allowed for a shift upwards (normalized) (DSM up shift)"
            ":math:`\eta`",":attr:`~SinkDSM.efficiency`","P", "Efficiency
            loss for load shifting processes"
            ":math:`\mathbb{T}` "," ","P", "Time steps"
            ":math:`eligibility_{shift}` ",
            ":attr:`~SinkDSM.shift_eligibility`","P",
            "Boolean parameter indicating if unit can be used for
            load shifting"
            ":math:`eligibility_{shed}` ",
            ":attr:`~SinkDSM.shed_eligibility`","P",
            "Boolean parameter indicating if unit can be used for
            load shedding"
            ":math:`cost_{t}^{dsm, up}` ", ":attr:`~SinkDSM.cost_dsm_up[t]`",
            "P", "Variable costs for an upwards shift"
            ":math:`cost_{t}^{dsm, do, shift}` ",
            ":attr:`~SinkDSM.cost_dsm_down_shift[t]`","P",
            "Variable costs for a downwards shift (load shifting)"
            ":math:`cost_{t}^{dsm, do, shed}` ",
            ":attr:`~SinkDSM.cost_dsm_down_shed[t]`","P",
            "Variable costs for shedding load"
            ":math:`\R`",":attr:`~SinkDSM.recovery_time_shift`","P",
            "Minimum time between the end of one load shifting process
            and the start of another"
            ":math:`\Delta t`",":attr:`~models.Model.timeincrement`","P",
            "The time increment of the model"
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all DSM components get inflow from a bus
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        # Set of DSM Components
        self.dsm = Set(initialize=[g for g in group])

        #  ************* VARIABLES *****************************

        # Variable load shift down
        self.dsm_do_shift = Var(self.dsm, m.TIMESTEPS, m.TIMESTEPS,
                                initialize=0, within=NonNegativeReals)

        # Variable load shedding
        self.dsm_do_shed = Var(self.dsm, m.TIMESTEPS, initialize=0,
                               within=NonNegativeReals)

        # Variable load shift up
        self.dsm_up = Var(
            self.dsm, m.TIMESTEPS, initialize=0, within=NonNegativeReals
        )

        #  ************* CONSTRAINTS *****************************

        def _shift_shed_vars_rule(block):
            """Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if not g.shift_eligibility:
                        lhs = self.dsm_up[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

                    if not g.shed_eligibility:
                        lhs = self.dsm_do_shed[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Demand Production Relation
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DSM.
            Sink Inflow == Demand +- DSM
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # first time steps: 0 + delay time
                    if t <= g.delay_time:

                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, t]
                        # Demand +- DSM
                        rhs = (g.demand[t] * g.max_demand + self.dsm_up[g, t]
                               - sum(self.dsm_do_shift[g, tt, t]
                                     for tt in range(t + g.delay_time + 1))
                               - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add((g, t), (lhs == rhs))

                    # main use case
                    elif g.delay_time < t <= m.TIMESTEPS[-1] - g.delay_time:

                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, t]
                        # Demand +- DSM
                        rhs = (
                            g.demand[t] * g.max_demand
                            + self.dsm_up[g, t]
                            - sum(
                                self.dsm_do_shift[g, tt, t]
                                for tt in range(t - g.delay_time,
                                                t + g.delay_time + 1))
                            - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add((g, t), (lhs == rhs))

                    # last time steps: end - delay time
                    else:
                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, t]
                        # Demand +- DSM
                        rhs = (
                            g.demand[t] * g.max_demand
                            + self.dsm_up[g, t]
                            - sum(
                                self.dsm_do_shift[g, tt, t]
                                for tt in range(t - g.delay_time,
                                                m.TIMESTEPS[-1] + 1))
                            - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule
        )

        # Equation 7 (resp. 7')
        def dsm_up_down_constraint_rule(block):
            """Equation 7 (resp. 7') by Zerrahn & Schill:
            Every upward load shift has to be compensated by downward load
            shifts in a defined time frame. Slightly modified equations for
            the first and last time steps due to variable initialization.
            Efficiency value depicts possible energy losses through
            load shifting (Equation 7').
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # first time steps: 0 + delay time
                    if t <= g.delay_time:

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t + g.delay_time + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

                    # main use case
                    elif (g.delay_time < t
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t - g.delay_time,
                                                  t + g.delay_time + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

                    # last time steps: end - delay time
                    else:

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t - g.delay_time,
                                                  m.TIMESTEPS[-1] + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

        self.dsm_updo_constraint = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.dsm_updo_constraint_build = BuildAction(
            rule=dsm_up_down_constraint_rule
        )

        # Equation 8
        def dsm_up_constraint_rule(block):
            """Equation 8 by Zerrahn & Schill:
            Realised upward load shift at time t has to be smaller than
            upward DSM capacity at time t.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # DSM up
                    lhs = self.dsm_up[g, t]
                    # Capacity dsm_up
                    rhs = g.capacity_up[t] * g.max_capacity_up

                    # add constraint
                    block.dsm_up_constraint.add((g, t), (lhs <= rhs))

        self.dsm_up_constraint = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.dsm_up_constraint_build = BuildAction(
            rule=dsm_up_constraint_rule
        )

        # Equation 9 (modified)
        def dsm_do_constraint_rule(block):
            """Equation 9 by Zerrahn & Schill:
            Realised downward load shift at time t has to be smaller than
            downward DSM capacity at time t.
            """
            for tt in m.TIMESTEPS:
                for g in group:

                    # first times steps: 0 + delay
                    if tt <= g.delay_time:

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = g.capacity_down[tt] * g.max_capacity_down

                        # add constraint
                        block.dsm_do_constraint.add((g, tt), (lhs <= rhs))

                    # main use case
                    elif (g.delay_time < tt
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt - g.delay_time,
                                                  tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = g.capacity_down[tt] * g.max_capacity_down

                        # add constraint
                        block.dsm_do_constraint.add((g, tt), (lhs <= rhs))

                    # last time steps: end - delay time
                    else:

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt - g.delay_time,
                                                  m.TIMESTEPS[-1] + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = g.capacity_down[tt] * g.max_capacity_down

                        # add constraint
                        block.dsm_do_constraint.add((g, tt), (lhs <= rhs))

        self.dsm_do_constraint = Constraint(group, m.TIMESTEPS,
                                            noruleinit=True)
        self.dsm_do_constraint_build = BuildAction(
            rule=dsm_do_constraint_rule)

        # Equation 10
        def c2_constraint_rule(block):
            """Equation 10 by Zerrahn & Schill:
            The realised DSM up or down at time T has to be smaller than
            the maximum downward or upward capacity at time T. Therefore, in
            total each individual DSM unit within the modeled portfolio
            can only be shifted up OR down at a given time.
            """
            for tt in m.TIMESTEPS:
                for g in group:

                    # first times steps: 0 + delay time
                    if tt <= g.delay_time:

                        # DSM up/down
                        lhs = (self.dsm_up[g, tt]
                               + sum(self.dsm_do_shift[g, t, tt]
                                     for t in range(tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = max(g.capacity_up[tt] * g.max_capacity_up,
                                  g.capacity_down[tt] * g.max_capacity_down)

                        # add constraint
                        block.C2_constraint.add((g, tt), (lhs <= rhs))

                    elif (g.delay_time < tt
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM up/down
                        lhs = (
                            self.dsm_up[g, tt]
                            + sum(self.dsm_do_shift[g, t, tt]
                                  for t in range(tt - g.delay_time,
                                                 tt + g.delay_time + 1))
                            + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = max(g.capacity_up[tt] * g.max_capacity_up,
                                  g.capacity_down[tt] * g.max_capacity_down)

                        # add constraint
                        block.C2_constraint.add((g, tt), (lhs <= rhs))

                    else:

                        # DSM up/down
                        lhs = (self.dsm_up[g, tt] + sum(
                            self.dsm_do_shift[g, t, tt]
                            for t in range(tt - g.delay_time,
                                           m.TIMESTEPS[-1] + 1))
                               + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = max(g.capacity_up[tt] * g.max_capacity_up,
                                  g.capacity_down[tt] * g.max_capacity_down)

                        # add constraint
                        block.C2_constraint.add((g, tt), (lhs <= rhs))

        self.C2_constraint = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.C2_constraint_build = BuildAction(rule=c2_constraint_rule)

        def recovery_constraint_rule(block):
            """Equation 11 by Zerrahn & Schill:
            A recovery time is introduced to account for the fact that
            there may be some restrictions before the next load shift
            may take place. Rule is only applicable if a recovery time
            is defined.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # No need to build constraint if no recovery
                    # time is defined.
                    if g.recovery_time_shift not in [None, 0]:

                        # main use case
                        if t <= m.TIMESTEPS[-1] - g.recovery_time_shift:

                            # DSM up
                            lhs = sum(self.dsm_up[g, tt] for tt in
                                      range(t, t + g.recovery_time_shift))
                            # max energy shift for shifting process
                            rhs = (g.capacity_up[t] * g.max_capacity_up
                                   * g.delay_time * m.timeincrement[t])
                            # add constraint
                            block.recovery_constraint.add((g, t), (lhs <= rhs))

                        # last time steps: end - recovery time
                        else:

                            # DSM up
                            lhs = sum(self.dsm_up[g, tt] for tt in
                                      range(t, m.TIMESTEPS[-1] + 1))
                            # max energy shift for shifting process
                            rhs = (g.capacity_up[t] * g.max_capacity_up
                                   * g.delay_time * m.timeincrement[t])
                            # add constraint
                            block.recovery_constraint.add((g, t), (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.recovery_constraint = Constraint(group, m.TIMESTEPS,
                                              noruleinit=True)
        self.recovery_constraint_build = BuildAction(
            rule=recovery_constraint_rule)

        # Equation 9a from Zerrahn and Schill (2015b)
        def shed_limit_constraint_rule(block):
            """The following constraint is highly similar to equation 9a
            from Zerrahn and Schill (2015b): A recovery time for load
            shedding is introduced in order to limit the overall amount
            of shedded energy.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # Only applicable for load shedding
                    if g.shed_eligibility:

                        # main use case
                        if t <= m.TIMESTEPS[-1] - g.recovery_time_shed:

                            # DSM up
                            lhs = sum(self.dsm_do_shed[g, tt] for tt in
                                      range(t, t + g.recovery_time_shed))
                            # max energy shift for shifting process
                            rhs = (g.capacity_down[t] * g.max_capacity_down
                                   * g.shed_time * m.timeincrement[t])
                            # add constraint
                            block.shed_limit_constraint.add((g, t),
                                                            (lhs <= rhs))

                        # last time steps: end - recovery time
                        else:

                            # DSM up
                            lhs = sum(self.dsm_do_shed[g, tt] for tt in
                                      range(t, m.TIMESTEPS[-1] + 1))
                            # max energy shift for shifting process
                            rhs = (g.capacity_down[t] * g.max_capacity_down
                                   * g.shed_time * m.timeincrement[t])
                            # add constraint
                            block.shed_limit_constraint.add((g, t),
                                                            (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.shed_limit_constraint = Constraint(group, m.TIMESTEPS,
                                                noruleinit=True)
        self.shed_limit_constraint_build = BuildAction(
            rule=shed_limit_constraint_rule)

    def _objective_expression(self):
        r"""Objective expression with variable costs for DSM activity
        """

        m = self.parent_block()

        dsm_cost = 0

        for t in m.TIMESTEPS:
            for g in self.dsm:
                dsm_cost += (self.dsm_up[g, t]
                             * g.cost_dsm_up[t]
                             * m.objective_weigthing[t])
                dsm_cost += ((sum(self.dsm_do_shift[g, t, tt]
                                  for tt in m.TIMESTEPS)
                              * g.cost_dsm_down_shift[t]
                              + self.dsm_do_shed[g, t]
                              * g.cost_dsm_down_shed[t])
                             * m.objective_weighting[t])

        self.cost = Expression(expr=dsm_cost)

        return self.cost


class SinkDSMDIWMultiPeriodBlock(SimpleBlock):
    r"""Constraints for SinkDSM with "DIW" approach and :attr:`multiperiod`

    **The following constraints are created for approach = 'DIW' with a
    mutliperiod attribute:**

    .. _SinkDSMDIW equations:

    .. math::
        &
        (1) \quad DSM_{t}^{up} = 0 \quad \forall t
        \quad if \space eligibility_{shift} = False \\
        &
        (2) \quad DSM_{t}^{do, shed} = 0 \quad \forall t
        \quad if \space eligibility_{shed} = False \\
        &
        (3) \quad \dot{E}_{t} = demand_{t} \cdot demand_{max} + DSM_{t}^{up} -
        \sum_{tt=t-L}^{t+L} DSM_{tt,t}^{do, shift} - DSM_{t}^{do, shed} \quad
        \forall t \in \mathbb{T} \\
        &
        (4) \quad DSM_{t}^{up} \cdot \eta =
        \sum_{tt=t-L}^{t+L} DSM_{t,tt}^{do, shift}
        \quad \forall t \in \mathbb{T} \\
        &
        (5) \quad DSM_{t}^{up} \leq  E_{t}^{up} \cdot E_{up, max}
        \quad \forall t \in \mathbb{T} \\
        &
        (6) \quad \sum_{t=tt-L}^{tt+L} DSM_{t,tt}^{do, shift}
        + DSM_{tt}^{do, shed} \leq E_{tt}^{do} \cdot E_{do, max}
        \quad \forall tt \in \mathbb{T} \\
        &
        (7) \quad DSM_{tt}^{up} + \sum_{t=tt-L}^{tt+L} DSM_{t,tt}^{do, shift}
        + DSM_{tt}^{do, shed} \leq
        max \{ E_{tt}^{up} \cdot E_{up, max}, E_{tt}^{do} \cdot E_{do, max} \}
        \quad \forall tt \in \mathbb{T} \\
        &
        (8) \quad \sum_{tt=t}^{t+R-1} DSM_{tt}^{up}
        \leq E_{t}^{up} \cdot E_{up, max} \cdot L \cdot \Delta t
        \quad \forall t \in \mathbb{T} \\
        &
        (9) \quad \sum_{tt=t}^{t+R-1} DSM_{tt}^{do, shed}
        \leq E_{t}^{do} \cdot E_{do, max} \cdot t_{shed} \cdot \Delta t
        \quad \forall t \in \mathbb{T} \\
        &

    *Note*: For the sake of readability, the handling of indices is not
    displayed here. E.g. evaluating a variable for t-L may lead to a negative
    and therefore infeasible index.
    This is addressed by limiting the sums to non-negative indices within the
    model index bounds. Please refer to the constraints implementation
    themselves.

    **The following parts of the objective function are created:**

    .. math::
        DSM_{t}^{up} \cdot cost_{t}^{dsm, up}
        + \sum_{tt=0}^{|T|} DSM_{t, tt}^{do, shift} \cdot
        cost_{t}^{dsm, do, shift}
        + DSM_{t}^{do, shed} \cdot cost_{t}^{dsm, do, shed}
        \quad \forall t \in \mathbb{T} \\

    **Table: Symbols and attribute names of variables and parameters**

        .. csv-table:: Variables (V) and Parameters (P)
            :header: "symbol", "attribute", "type", "explanation"
            :widths: 1, 1, 1, 1

            ":math:`DSM_{t}^{up}` ",":attr:`~SinkDSM.dsm_up[g,t]`",
            "V", "DSM up shift (additional load) in hour t"
            ":math:`DSM_{t,tt}^{do, shift}` ",
            ":attr:`~SinkDSM.dsm_do_shift[g,t,tt]`",
            "V", "DSM down shift (less load) in hour tt
            to compensate for upwards shifts in hour t"
            ":math:`DSM_{t}^{do, shed}` ",":attr:`~SinkDSM.dsm_do_shed[g,t]` ",
            "V","DSM shedded (capacity shedded, i.e. not compensated for)"
            ":math:`\dot{E}_{t}` ",":attr:`flow[g,t]`","V","Energy
            flowing in from (electrical) inflow bus"
            ":math:`L`",":attr:`~SinkDSM.delay_time`","P",
            "Maximum delay time for load shift
            (time until the energy balance has to be levelled out again;
            roundtrip time of one load shifting cycle, i.e. time window
            for upshift and compensating downshift)"
            ":math:`t_{she}`",":attr:`~SinkDSM.shed_time`","P",
            "Maximum time for one load shedding process"
            ":math:`demand_{t}`",":attr:`~SinkDSM.demand[t]`","P",
            "(Electrical) demand series (normalized)"
            ":math:`demand_{max}`",":attr:`~SinkDSM.max_demand`","P",
            "Maximum demand value"
            ":math:`E_{t}^{do}`",":attr:`~SinkDSM.capacity_down[t]`","P",
            "Capacity  allowed for a load adjustment downwards (normalized)
            (DSM down shift + DSM shedded)"
            ":math:`E_{t}^{up}`",":attr:`~SinkDSM.capacity_up[t]`","P",
            "Capacity allowed for a shift upwards (normalized) (DSM up shift)"
            ":math:`E_{do, max}`",":attr:`~SinkDSM.max_capacity_down`","P",
            "Maximum capacity allowed for a load adjustment downwards
            (DSM down shift + DSM shedded)"
            ":math:`E_{up, max}`",":attr:`~SinkDSM.max_capacity_up`","P",
            "Capacity allowed for a shift upwards (normalized) (DSM up shift)"
            ":math:`\eta`",":attr:`~SinkDSM.efficiency`","P", "Efficiency
            loss for load shifting processes"
            ":math:`\mathbb{T}` "," ","P", "Time steps"
            ":math:`eligibility_{shift}` ",
            ":attr:`~SinkDSM.shift_eligibility`","P",
            "Boolean parameter indicating if unit can be used for
            load shifting"
            ":math:`eligibility_{shed}` ",
            ":attr:`~SinkDSM.shed_eligibility`","P",
            "Boolean parameter indicating if unit can be used for
            load shedding"
            ":math:`cost_{t}^{dsm, up}` ", ":attr:`~SinkDSM.cost_dsm_up[t]`",
            "P", "Variable costs for an upwards shift"
            ":math:`cost_{t}^{dsm, do, shift}` ",
            ":attr:`~SinkDSM.cost_dsm_down_shift[t]`","P",
            "Variable costs for a downwards shift (load shifting)"
            ":math:`cost_{t}^{dsm, do, shed}` ",
            ":attr:`~SinkDSM.cost_dsm_down_shed[t]`","P",
            "Variable costs for shedding load"
            ":math:`\R`",":attr:`~SinkDSM.recovery_time_shift`","P",
            "Minimum time between the end of one load shifting process
            and the start of another"
            ":math:`\Delta t`",":attr:`~models.Model.timeincrement`","P",
            "The time increment of the model"
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all DSM components get inflow from bus_elec
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        # Set of DSM Components
        self.multiperioddsm = Set(initialize=[g for g in group])

        #  ************* VARIABLES *****************************

        # Variable load shift down
        self.dsm_do_shift = Var(self.multiperioddsm, m.TIMESTEPS, m.TIMESTEPS,
                                initialize=0, within=NonNegativeReals)

        # Variable load shedding
        self.dsm_do_shed = Var(self.multiperioddsm, m.TIMESTEPS, initialize=0,
                               within=NonNegativeReals)

        # Variable load shift up
        self.dsm_up = Var(self.multiperioddsm, m.TIMESTEPS, initialize=0,
                          within=NonNegativeReals)

        #  ************* CONSTRAINTS *****************************

        def _shift_shed_vars_rule(block):
            """
            Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if not g.shift_eligibility:
                        lhs = self.dsm_up[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

                    if not g.shed_eligibility:
                        lhs = self.dsm_do_shed[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Demand Production Relation
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DSM.
            Generator Production == Demand +- DSM
            """
            for p, t in m.TIMEINDEX:
                for g in group:

                    # first time steps: 0 + delay time
                    if t <= g.delay_time:

                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, p, t]
                        # Demand +- DSM
                        rhs = (
                            g.demand[t] * g.max_demand
                            + self.dsm_up[g, t]
                            - sum(
                                self.dsm_do_shift[g, tt, t]
                                for tt in range(t + g.delay_time + 1))
                            - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add(
                            (g, p, t), (lhs == rhs))

                    # main use case
                    elif (g.delay_time < t
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, p, t]
                        # Demand +- DSM
                        rhs = (
                            g.demand[t] * g.max_demand
                            + self.dsm_up[g, t]
                            - sum(
                                self.dsm_do_shift[g, tt, t]
                                for tt in range(t - g.delay_time,
                                                t + g.delay_time + 1))
                            - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add(
                            (g, p, t), (lhs == rhs))

                    # last time steps: end - delay time
                    else:
                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, p, t]
                        # Demand +- DSM
                        rhs = (
                            g.demand[t] * g.max_demand
                            + self.dsm_up[g, t]
                            - sum(
                                self.dsm_do_shift[g, tt, t]
                                for tt in range(t - g.delay_time,
                                                m.TIMESTEPS[-1] + 1))
                            - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add(
                            (g, p, t), (lhs == rhs))

        self.input_output_relation = Constraint(group, m.TIMEINDEX,
                                                noruleinit=True)
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule)

        # Equation 7 (resp. 7')
        def dsm_up_down_constraint_rule(block):
            """Equation 7 (resp. 7') by Zerrahn & Schill:
            Every upward load shift has to be compensated by downward load
            shifts in a defined time frame. Slightly modified equations for
            the first and last time steps due to variable initialization.
            Efficiency value depicts possible energy losses through
            load shifting (Equation 7').
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # first time steps: 0 + delay time
                    if t <= g.delay_time:

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t + g.delay_time + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

                    # main use case
                    elif (g.delay_time < t
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t - g.delay_time,
                                                  t + g.delay_time + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

                    # last time steps: end - delay time
                    else:

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t - g.delay_time,
                                                  m.TIMESTEPS[-1] + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

        self.dsm_updo_constraint = Constraint(group, m.TIMESTEPS,
                                              noruleinit=True)
        self.dsm_updo_constraint_build = BuildAction(
            rule=dsm_up_down_constraint_rule)

        # Equation 8
        def dsm_up_constraint_rule(block):
            """Equation 8 by Zerrahn & Schill:
            Realised upward load shift at time t has to be smaller than
            upward DSM capacity at time t.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # DSM up
                    lhs = self.dsm_up[g, t]
                    # Capacity dsm_up
                    rhs = g.capacity_up[t] * g.max_capacity_up

                    # add constraint
                    block.dsm_up_constraint.add((g, t), (lhs <= rhs))

        self.dsm_up_constraint = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.dsm_up_constraint_build = BuildAction(
            rule=dsm_up_constraint_rule
        )

        # Equation 9 (modified)
        def dsm_do_constraint_rule(block):
            """Equation 9 by Zerrahn & Schill:
            Realised downward load shift at time t has to be smaller than
            downward DSM capacity at time t.
            """
            for tt in m.TIMESTEPS:
                for g in group:

                    # first times steps: 0 + delay
                    if tt <= g.delay_time:

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = g.capacity_down[tt] * g.max_capacity_down

                        # add constraint
                        block.dsm_do_constraint.add((g, tt), (lhs <= rhs))

                    # main use case
                    elif (g.delay_time < tt
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt - g.delay_time,
                                                  tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = g.capacity_down[tt] * g.max_capacity_down

                        # add constraint
                        block.dsm_do_constraint.add((g, tt), (lhs <= rhs))

                    # last time steps: end - delay time
                    else:

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt - g.delay_time,
                                                  m.TIMESTEPS[-1] + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = g.capacity_down[tt] * g.max_capacity_down

                        # add constraint
                        block.dsm_do_constraint.add((g, tt), (lhs <= rhs))

        self.dsm_do_constraint = Constraint(group, m.TIMESTEPS,
                                            noruleinit=True)
        self.dsm_do_constraint_build = BuildAction(
            rule=dsm_do_constraint_rule)

        # Equation 10
        def c2_constraint_rule(block):
            """Equation 10 by Zerrahn & Schill:
            The realised DSM up or down at time T has to be smaller than
            the maximum downward or upward capacity at time T. Therefore, in
            total each individual DSM unit within the modeled portfolio
            can only be shifted up OR down at a given time.
            """
            for tt in m.TIMESTEPS:
                for g in group:

                    # first times steps: 0 + delay time
                    if tt <= g.delay_time:

                        # DSM up/down
                        lhs = (self.dsm_up[g, tt]
                               + sum(self.dsm_do_shift[g, t, tt]
                                     for t in range(tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = max(g.capacity_up[tt] * g.max_capacity_up,
                                  g.capacity_down[tt] * g.max_capacity_down)

                        # add constraint
                        block.C2_constraint.add((g, tt), (lhs <= rhs))

                    elif (g.delay_time < tt
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM up/down
                        lhs = (
                            self.dsm_up[g, tt]
                            + sum(self.dsm_do_shift[g, t, tt]
                                  for t in range(tt - g.delay_time,
                                                 tt + g.delay_time + 1))
                            + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = max(g.capacity_up[tt] * g.max_capacity_up,
                                  g.capacity_down[tt] * g.max_capacity_down)

                        # add constraint
                        block.C2_constraint.add((g, tt), (lhs <= rhs))

                    else:

                        # DSM up/down
                        lhs = (self.dsm_up[g, tt] + sum(
                            self.dsm_do_shift[g, t, tt]
                            for t in range(tt - g.delay_time,
                                           m.TIMESTEPS[-1] + 1))
                               + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = max(g.capacity_up[tt] * g.max_capacity_up,
                                  g.capacity_down[tt] * g.max_capacity_down)

                        # add constraint
                        block.C2_constraint.add((g, tt), (lhs <= rhs))

        self.C2_constraint = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.C2_constraint_build = BuildAction(rule=c2_constraint_rule)

        def recovery_constraint_rule(block):
            """Equation 11 by Zerrahn & Schill:
            A recovery time is introduced to account for the fact that
            there may be some restrictions before the next load shift
            may take place. Rule is only applicable if a recovery time
            is defined.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # No need to build constraint if no recovery
                    # time is defined.
                    if g.recovery_time_shift not in [None, 0]:

                        # main use case
                        if t <= m.TIMESTEPS[-1] - g.recovery_time_shift:

                            # DSM up
                            lhs = sum(self.dsm_up[g, tt] for tt in
                                      range(t, t + g.recovery_time_shift))
                            # max energy shift for shifting process
                            rhs = (g.capacity_up[t] * g.max_capacity_up
                                   * g.delay_time * m.timeincrement[t])
                            # add constraint
                            block.recovery_constraint.add((g, t), (lhs <= rhs))

                        # last time steps: end - recovery time
                        else:

                            # DSM up
                            lhs = sum(self.dsm_up[g, tt] for tt in
                                      range(t, m.TIMESTEPS[-1] + 1))
                            # max energy shift for shifting process
                            rhs = (g.capacity_up[t] * g.max_capacity_up
                                   * g.delay_time * m.timeincrement[t])
                            # add constraint
                            block.recovery_constraint.add((g, t), (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.recovery_constraint = Constraint(group, m.TIMESTEPS,
                                              noruleinit=True)
        self.recovery_constraint_build = BuildAction(
            rule=recovery_constraint_rule)

        # Equation 9a from Zerrahn and Schill (2015b)
        def shed_limit_constraint_rule(block):
            """The following constraint is highly similar to equation 9a
            from Zerrahn and Schill (2015b): A recovery time for load
            shedding is introduced in order to limit the overall amount
            of shedded energy.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # Only applicable for load shedding
                    if g.shed_eligibility:

                        # main use case
                        if t <= m.TIMESTEPS[-1] - g.recovery_time_shed:

                            # DSM up
                            lhs = sum(self.dsm_do_shed[g, tt] for tt in
                                      range(t, t + g.recovery_time_shed))
                            # max energy shift for shifting process
                            rhs = (g.capacity_down[t] * g.max_capacity_down
                                   * g.shed_time * m.timeincrement[t])
                            # add constraint
                            block.shed_limit_constraint.add((g, t),
                                                            (lhs <= rhs))

                        # last time steps: end - recovery time
                        else:

                            # DSM up
                            lhs = sum(self.dsm_do_shed[g, tt] for tt in
                                      range(t, m.TIMESTEPS[-1] + 1))
                            # max energy shift for shifting process
                            rhs = (g.capacity_down[t] * g.max_capacity_down
                                   * g.shed_time * m.timeincrement[t])
                            # add constraint
                            block.shed_limit_constraint.add((g, t),
                                                            (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.shed_limit_constraint = Constraint(group, m.TIMESTEPS,
                                                noruleinit=True)
        self.shed_limit_constraint_build = BuildAction(
            rule=shed_limit_constraint_rule)

    def _objective_expression(self):
        r"""Objective expression with variable costs for DSM activity
        """

        m = self.parent_block()

        variable_costs = 0
        fixed_costs = 0

        for g in self.multiperioddsm:
            for p, t in m.TIMEINDEX:
                variable_costs += (self.dsm_up[g, t]
                                   * m.objective_weighting[t]
                                   * g.cost_dsm_up[p]
                                   * ((1 + m.discount_rate) ** -p))
                variable_costs += ((sum(self.dsm_do_shift[g, t, tt]
                                        for tt in m.TIMESTEPS)
                                    * g.cost_dsm_down_shift[p]
                                    + self.dsm_do_shed[g, t]
                                    * g.cost_dsm_down_shed[p])
                                   * m.objective_weighting[t]
                                   * ((1 + m.discount_rate) ** -p))

            if g.fixed_costs[0] is not None:
                for p in m.PERIODS:
                    fixed_costs += (
                        g.max_demand
                        * g.fixed_costs[p]
                        * ((1 + m.discount_rate) ** (-p))
                    )

        self.cost = Expression(expr=variable_costs + fixed_costs)

        return self.cost


class SinkDSMDIWInvestmentBlock(SimpleBlock):
    r"""Constraints for SinkDSM with "DIW" approach and :attr:`investment`

    **The following constraints are created for approach = 'DIW' with an
    investment object defined:**

    .. _SinkDSMDIW equations:

    .. math::
        &
        (1) \quad invest_{min} \leq invest \leq invest_{max} \\
        &
        (2) \quad DSM_{t}^{up} = 0 \quad \forall t
        \quad if \space eligibility_{shift} = False \\
        &
        (3) \quad DSM_{t}^{do, shed} = 0 \quad \forall t
        \quad if \space eligibility_{shed} = False \\
        &
        (4) \quad \dot{E}_{t} = demand_{t} \cdot (invest + E_{exist})
        + DSM_{t}^{up} -
        \sum_{tt=t-L}^{t+L} DSM_{tt,t}^{do, shift} - DSM_{t}^{do, shed} \quad
        \forall t \in \mathbb{T} \\
        &
        (5) \quad DSM_{t}^{up} \cdot \eta =
        \sum_{tt=t-L}^{t+L} DSM_{t,tt}^{do, shift}
        \quad \forall t \in \mathbb{T} \\
        &
        (6) \quad DSM_{t}^{up} \leq E_{t}^{up} \cdot (invest + E_{exist})
        \ s_{flex, up}
        \quad \forall t \in \mathbb{T} \\
        &
        (7) \quad \sum_{t=tt-L}^{tt+L} DSM_{t,tt}^{do, shift}
        + DSM_{tt}^{do, shed} \leq E_{tt}^{do} \cdot (invest + E_{exist})
        \cdot s_{flex, do}
        \quad \forall tt \in \mathbb{T} \\
        &
        (8) \quad DSM_{tt}^{up} + \sum_{t=tt-L}^{tt+L} DSM_{t,tt}^{do, shift}
        + DSM_{tt}^{do, shed} \leq
        max \{ E_{tt}^{up} \cdot s_{flex, up},
        E_{tt}^{do} \cdot s_{flex, do} \} \cdot (invest + E_{exist})
        \quad \forall tt \in \mathbb{T} \\
        &
        (9) \quad \sum_{tt=t}^{t+R-1} DSM_{tt}^{up}
        \leq E_{t}^{up} \cdot (invest + E_{exist})
        \cdot s_{flex, up} \cdot L \cdot \Delta t
        \quad \forall t \in \mathbb{T} \\
        &
        (10) \quad \sum_{tt=t}^{t+R-1} DSM_{tt}^{do, shed}
        \leq E_{t}^{do} \cdot (invest + E_{exist})
        \cdot s_{flex, do} \cdot t_{shed}
        \cdot \Delta t \quad \forall t \in \mathbb{T} \\

    *Note*: For the sake of readability, the handling of indices is not
    displayed here. E.g. evaluating a variable for t-L may lead to a negative
    and therefore infeasible index.
    This is addressed by limiting the sums to non-negative indices within the
    model index bounds. Please refer to the constraints implementation
    themselves.

    **The following parts of the objective function are created:**

    * Investment annuity:

    .. math::
        invest \cdot costs_{invest} \\

    * Variable costs:

    .. math::
        DSM_{t}^{up} \cdot cost_{t}^{dsm, up}
        + \sum_{tt=0}^{T} DSM_{t, tt}^{do, shift} \cdot
        cost_{t}^{dsm, do, shift}
        + DSM_{t}^{do, shed} \cdot cost_{t}^{dsm, do, shed}
        \quad \forall t \in \mathbb{T}

    **Table: Symbols and attribute names of variables and parameters**

    Please refer to :class:`oemof.solph.custom.SinkDSMDIWBlock`.

    The following variables and parameters are exclusively used for
    investment modeling:

        .. csv-table:: Variables (V) and Parameters (P)
            :header: "symbol", "attribute", "type", "explanation"
            :widths: 1, 1, 1, 1

            ":math:`invest` ",":attr:`~SinkDSM.invest` ","V", "DSM capacity
            invested in. Equals to the additionally installed capacity.
            The capacity share eligible for a shift is determined
            by flex share(s)."
            ":math:`invest_{min}` ", ":attr:`~SinkDSM.investment.minimum` ",
            "P", "minimum investment"
            ":math:`invest_{max}` ", ":attr:`~SinkDSM.investment.maximum` ",
            "P", "maximum investment"
            ":math:`E_{exist}` ",":attr:`~SinkDSM.investment.existing` ",
            "P", "existing DSM capacity"
            ":math:`s_{flex, up}` ",":attr:`~SinkDSM.flex_share_up` ",
            "P","Share of invested capacity that may be shift upwards
            at maximum"
            ":math:`s_{flex, do}` ",":attr:`~SinkDSM.flex_share_do` ",
            "P", "Share of invested capacity that may be shift downwards
            at maximum"
            ":math:`costs_{invest}` ",":attr:`~SinkDSM.investment.ep_costs` ",
            "P", "specific investment annuity"
            ":math:`T` "," ","P", "Overall amount of time steps (cardinality)"
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all DSM components get inflow from a bus
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        # Set of DSM Components
        self.investdsm = Set(initialize=[g for g in group])

        #  ************* VARIABLES *****************************

        # Define bounds for investments in demand response
        def _dsm_investvar_bound_rule(block, g):
            """Rule definition to bound the
            demand response capacity invested in (`invest`).
            """
            return g.investment.minimum, g.investment.maximum

        # Investment in DR capacity
        self.invest = Var(self.investdsm,
                          within=NonNegativeReals,
                          bounds=_dsm_investvar_bound_rule)

        # Variable load shift down
        self.dsm_do_shift = Var(self.investdsm, m.TIMESTEPS, m.TIMESTEPS,
                                initialize=0, within=NonNegativeReals)

        # Variable load shedding
        self.dsm_do_shed = Var(self.investdsm, m.TIMESTEPS, initialize=0,
                               within=NonNegativeReals)

        # Variable load shift up
        self.dsm_up = Var(self.investdsm, m.TIMESTEPS, initialize=0,
                          within=NonNegativeReals)

        #  ************* CONSTRAINTS *****************************

        def _shift_shed_vars_rule(block):
            """Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if not g.shift_eligibility:
                        lhs = self.dsm_up[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

                    if not g.shed_eligibility:
                        lhs = self.dsm_do_shed[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Demand Production Relation
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DSM.
            Sink Inflow == Demand +- DSM
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # first time steps: 0 + delay time
                    if t <= g.delay_time:

                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, t]
                        # Demand +- DSM
                        rhs = (g.demand[t]
                               * (self.invest[g] + g.investment.existing)
                               + self.dsm_up[g, t]
                               - sum(self.dsm_do_shift[g, tt, t]
                                     for tt in range(t + g.delay_time + 1))
                               - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add((g, t), (lhs == rhs))

                    # main use case
                    elif (g.delay_time < t
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, t]
                        # Demand +- DSM
                        rhs = (g.demand[t]
                               * (self.invest[g] + g.investment.existing)
                               + self.dsm_up[g, t]
                               - sum(self.dsm_do_shift[g, tt, t]
                                     for tt in range(t - g.delay_time,
                                                     t + g.delay_time + 1))
                               - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add((g, t), (lhs == rhs))

                    # last time steps: end - delay time
                    else:
                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, t]
                        # Demand +- DSM
                        rhs = (g.demand[t]
                               * (self.invest[g] + g.investment.existing)
                               + self.dsm_up[g, t]
                               - sum(self.dsm_do_shift[g, tt, t]
                                     for tt in range(t - g.delay_time,
                                                     m.TIMESTEPS[-1] + 1))
                               - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation = Constraint(group, m.TIMESTEPS,
                                                noruleinit=True)
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule)

        # Equation 7 (resp. 7')
        def dsm_up_down_constraint_rule(block):
            """Equation 7 (resp. 7') by Zerrahn & Schill:
            Every upward load shift has to be compensated by downward load
            shifts in a defined time frame. Slightly modified equations for
            the first and last time steps due to variable initialization.
            Efficiency value depicts possible energy losses through
            load shifting (Equation 7').
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # first time steps: 0 + delay time
                    if t <= g.delay_time:

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t + g.delay_time + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

                    # main use case
                    elif (g.delay_time < t
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t - g.delay_time,
                                                  t + g.delay_time + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

                    # last time steps: end - delay time
                    else:

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t - g.delay_time,
                                                  m.TIMESTEPS[-1] + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

        self.dsm_updo_constraint = Constraint(group, m.TIMESTEPS,
                                              noruleinit=True)
        self.dsm_updo_constraint_build = BuildAction(
            rule=dsm_up_down_constraint_rule)

        # Equation 8
        def dsm_up_constraint_rule(block):
            """Equation 8 by Zerrahn & Schill:
            Realised upward load shift at time t has to be smaller than
            upward DSM capacity at time t.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # DSM up
                    lhs = self.dsm_up[g, t]
                    # Capacity dsm_up
                    rhs = (g.capacity_up[t]
                           * (self.invest[g] + g.investment.existing)
                           * g.flex_share_up)

                    # add constraint
                    block.dsm_up_constraint.add((g, t), (lhs <= rhs))

        self.dsm_up_constraint = Constraint(group, m.TIMESTEPS,
                                            noruleinit=True)
        self.dsm_up_constraint_build = BuildAction(rule=dsm_up_constraint_rule)

        # Equation 9 (modified)
        def dsm_do_constraint_rule(block):
            """Equation 9 by Zerrahn & Schill:
            Realised downward load shift at time t has to be smaller than
            downward DSM capacity at time t.
            """
            for tt in m.TIMESTEPS:
                for g in group:

                    # first times steps: 0 + delay
                    if tt <= g.delay_time:

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = (g.capacity_down[tt]
                               * (self.invest[g] + g.investment.existing)
                               * g.flex_share_down)

                        # add constraint
                        block.dsm_do_constraint.add((g, tt), (lhs <= rhs))

                    # main use case
                    elif (g.delay_time < tt
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt - g.delay_time,
                                                  tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = (g.capacity_down[tt]
                               * (self.invest[g] + g.investment.existing)
                               * g.flex_share_down)

                        # add constraint
                        block.dsm_do_constraint.add((g, tt), (lhs <= rhs))

                    # last time steps: end - delay time
                    else:

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt - g.delay_time,
                                                  m.TIMESTEPS[-1] + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = (g.capacity_down[tt]
                               * (self.invest[g] + g.investment.existing)
                               * g.flex_share_down)

                        # add constraint
                        block.dsm_do_constraint.add((g, tt), (lhs <= rhs))

        self.dsm_do_constraint = Constraint(group, m.TIMESTEPS,
                                            noruleinit=True)
        self.dsm_do_constraint_build = BuildAction(
            rule=dsm_do_constraint_rule)

        # Equation 10
        def c2_constraint_rule(block):
            """Equation 10 by Zerrahn & Schill:
            The realised DSM up or down at time T has to be smaller than
            the maximum downward or upward capacity at time T. Therefore, in
            total each individual DSM unit within the modeled portfolio
            can only be shifted up OR down at a given time.
            """
            for tt in m.TIMESTEPS:
                for g in group:

                    # first times steps: 0 + delay time
                    if tt <= g.delay_time:

                        # DSM up/down
                        lhs = (self.dsm_up[g, tt]
                               + sum(self.dsm_do_shift[g, t, tt]
                                     for t in range(tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = (max(g.capacity_up[tt] * g.flex_share_up,
                                   g.capacity_down[tt] * g.flex_share_down)
                               * (self.invest[g] + g.investment.existing))

                        # add constraint
                        block.C2_constraint.add((g, tt), (lhs <= rhs))

                    elif (g.delay_time < tt
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM up/down
                        lhs = (self.dsm_up[g, tt] + sum(
                            self.dsm_do_shift[g, t, tt]
                            for t in range(tt - g.delay_time,
                                           tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = (max(g.capacity_up[tt] * g.flex_share_up,
                                   g.capacity_down[tt] * g.flex_share_down)
                               * (self.invest[g] + g.investment.existing))

                        # add constraint
                        block.C2_constraint.add((g, tt), (lhs <= rhs))

                    else:

                        # DSM up/down
                        lhs = (self.dsm_up[g, tt] + sum(
                            self.dsm_do_shift[g, t, tt]
                            for t in range(tt - g.delay_time,
                                           m.TIMESTEPS[-1] + 1))
                               + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = (max(g.capacity_up[tt] * g.flex_share_up,
                                   g.capacity_down[tt] * g.flex_share_down)
                               * (self.invest[g] + g.investment.existing))

                        # add constraint
                        block.C2_constraint.add((g, tt), (lhs <= rhs))

        self.C2_constraint = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.C2_constraint_build = BuildAction(rule=c2_constraint_rule)

        def recovery_constraint_rule(block):
            """Equation 11 by Zerrahn & Schill:
            A recovery time is introduced to account for the fact that
            there may be some restrictions before the next load shift
            may take place. Rule is only applicable if a recovery time
            is defined.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # No need to build constraint if no recovery
                    # time is defined.
                    if g.recovery_time_shift not in [None, 0]:

                        # main use case
                        if t <= m.TIMESTEPS[-1] - g.recovery_time_shift:

                            # DSM up
                            lhs = sum(self.dsm_up[g, tt] for tt in
                                      range(t, t + g.recovery_time_shift))
                            # max energy shift for shifting process
                            rhs = (g.capacity_up[t]
                                   * (self.invest[g] + g.investment.existing)
                                   * g.flex_share_up * g.delay_time
                                   * m.timeincrement[t])
                            # add constraint
                            block.recovery_constraint.add((g, t), (lhs <= rhs))

                        # last time steps: end - recovery time
                        else:

                            # DSM up
                            lhs = sum(self.dsm_up[g, tt] for tt in
                                      range(t, m.TIMESTEPS[-1] + 1))
                            # max energy shift for shifting process
                            rhs = (g.capacity_up[t]
                                   * (self.invest[g] + g.investment.existing)
                                   * g.flex_share_up * g.delay_time
                                   * m.timeincrement[t])
                            # add constraint
                            block.recovery_constraint.add((g, t), (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.recovery_constraint = Constraint(group, m.TIMESTEPS,
                                              noruleinit=True)
        self.recovery_constraint_build = BuildAction(
            rule=recovery_constraint_rule)

        # Equation 9a from Zerrahn and Schill (2015b)
        def shed_limit_constraint_rule(block):
            """The following constraint is highly similar to equation 9a
            from Zerrahn and Schill (2015b): A recovery time for load
            shedding is introduced in order to limit the overall amount
            of shedded energy.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # Only applicable for load shedding
                    if g.shed_eligibility:

                        # main use case
                        if t <= m.TIMESTEPS[-1] - g.recovery_time_shed:

                            # DSM up
                            lhs = sum(self.dsm_do_shed[g, tt] for tt in
                                      range(t, t + g.recovery_time_shed))
                            # max energy shift for shifting process
                            rhs = (g.capacity_down[t]
                                   * (self.invest[g] + g.investment.existing)
                                   * g.flex_share_down * g.shed_time
                                   * m.timeincrement[t])
                            # add constraint
                            block.shed_limit_constraint.add((g, t),
                                                            (lhs <= rhs))

                        # last time steps: end - recovery time
                        else:

                            # DSM up
                            lhs = sum(self.dsm_do_shed[g, tt] for tt in
                                      range(t, m.TIMESTEPS[-1] + 1))
                            # max energy shift for shifting process
                            rhs = (g.capacity_down[t]
                                   * (self.invest[g] + g.investment.existing)
                                   * g.flex_share_down * g.shed_time
                                   * m.timeincrement[t])
                            # add constraint
                            block.shed_limit_constraint.add((g, t),
                                                            (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.shed_limit_constraint = Constraint(group, m.TIMESTEPS,
                                                noruleinit=True)
        self.shed_limit_constraint_build = BuildAction(
            rule=shed_limit_constraint_rule)

    def _objective_expression(self):
        r"""Objective expression with variable and investment costs for DSM
        """

        m = self.parent_block()

        investment_costs = 0
        variable_costs = 0

        for g in self.investdsm:
            if g.investment.ep_costs is not None:
                investment_costs += self.invest[g] * g.investment.ep_costs
            else:
                raise ValueError("Missing value for investment costs!")

            for t in m.TIMESTEPS:
                variable_costs += (self.dsm_up[g, t] * g.cost_dsm_up[t]
                                   * m.objective_weighting[t])
                variable_costs += ((sum(self.dsm_do_shift[g, t, tt]
                                        for tt in m.TIMESTEPS)
                                    * g.cost_dsm_down_shift[t]
                                    + self.dsm_do_shed[g, t]
                                    * g.cost_dsm_down_shed[t])
                                   * m.objective_weighting)

        self.cost = Expression(expr=investment_costs + variable_costs)

        return self.cost


class SinkDSMDIWMultiPeriodInvestmentBlock(SinkDSMDIWBlock):
    r"""Constraints for SinkDSM with "DIW" approach and
    :attr:`multiperiodinvestment`

    **The following constraints are created for approach = 'DIW' with an
    multiperiodinvestment object defined:**

    .. _SinkDSMDIW equations:

    .. math::
        &
        (1) \quad invest_{min} \leq invest \leq invest_{max} \\
        &
        (2) \quad DSM_{t}^{up} = 0 \quad \forall t
        \quad if \space eligibility_{shift} = False \\
        &
        (3) \quad DSM_{t}^{do, shed} = 0 \quad \forall t
        \quad if \space eligibility_{shed} = False \\
        &
        (4) \quad \dot{E}_{t} = demand_{t} \cdot (invest + E_{exist})
        + DSM_{t}^{up} -
        \sum_{tt=t-L}^{t+L} DSM_{tt,t}^{do, shift} - DSM_{t}^{do, shed} \quad
        \forall t \in \mathbb{T} \\
        &
        (5) \quad DSM_{t}^{up} \cdot \eta =
        \sum_{tt=t-L}^{t+L} DSM_{t,tt}^{do, shift}
        \quad \forall t \in \mathbb{T} \\
        &
        (6) \quad DSM_{t}^{up} \leq E_{t}^{up} \cdot (invest + E_{exist})
        \ s_{flex, up}
        \quad \forall t \in \mathbb{T} \\
        &
        (7) \quad \sum_{t=tt-L}^{tt+L} DSM_{t,tt}^{do, shift}
        + DSM_{tt}^{do, shed} \leq E_{tt}^{do} \cdot (invest + E_{exist})
        \cdot s_{flex, do}
        \quad \forall tt \in \mathbb{T} \\
        &
        (8) \quad DSM_{tt}^{up} + \sum_{t=tt-L}^{tt+L} DSM_{t,tt}^{do, shift}
        + DSM_{tt}^{do, shed} \leq
        max \{ E_{tt}^{up} \cdot s_{flex, up},
        E_{tt}^{do} \cdot s_{flex, do} \} \cdot (invest + E_{exist})
        \quad \forall tt \in \mathbb{T} \\
        &
        (9) \quad \sum_{tt=t}^{t+R-1} DSM_{tt}^{up}
        \leq E_{t}^{up} \cdot (invest + E_{exist})
        \cdot s_{flex, up} \cdot L \cdot \Delta t
        \quad \forall t \in \mathbb{T} \\
        &
        (10) \quad \sum_{tt=t}^{t+R-1} DSM_{tt}^{do, shed}
        \leq E_{t}^{do} \cdot (invest + E_{exist})
        \cdot s_{flex, do} \cdot t_{shed}
        \cdot \Delta t \quad \forall t \in \mathbb{T} \\

    *Note*: For the sake of readability, the handling of indices is not
    displayed here. E.g. evaluating a variable for t-L may lead to a negative
    and therefore infeasible index.
    This is addressed by limiting the sums to non-negative indices within the
    model index bounds. Please refer to the constraints implementation
    themselves.

    **The following parts of the objective function are created:**

    * Investment annuity:

    .. math::
        invest \cdot costs_{invest} \\

    * Variable costs:

    .. math::
        DSM_{t}^{up} \cdot cost_{t}^{dsm, up}
        + \sum_{tt=0}^{T} DSM_{t, tt}^{do, shift} \cdot
        cost_{t}^{dsm, do, shift}
        + DSM_{t}^{do, shed} \cdot cost_{t}^{dsm, do, shed}
        \quad \forall t \in \mathbb{T}

    **Table: Symbols and attribute names of variables and parameters**

    Please refer to :class:`oemof.solph.custom.SinkDSMDIWBlock`.

    The following variables and parameters are exclusively used for
    investment modeling:

        .. csv-table:: Variables (V) and Parameters (P)
            :header: "symbol", "attribute", "type", "explanation"
            :widths: 1, 1, 1, 1

            ":math:`invest` ",":attr:`~SinkDSM.invest` ","V", "DSM capacity
            invested in. Equals to the additionally installed capacity.
            The capacity share eligible for a shift is determined
            by flex share(s)."
            ":math:`invest_{min}` ", ":attr:`~SinkDSM.investment.minimum` ",
            "P", "minimum investment"
            ":math:`invest_{max}` ", ":attr:`~SinkDSM.investment.maximum` ",
            "P", "maximum investment"
            ":math:`E_{exist}` ",":attr:`~SinkDSM.investment.existing` ",
            "P", "existing DSM capacity"
            ":math:`s_{flex, up}` ",":attr:`~SinkDSM.flex_share_up` ",
            "P","Share of invested capacity that may be shift upwards
            at maximum"
            ":math:`s_{flex, do}` ",":attr:`~SinkDSM.flex_share_do` ",
            "P", "Share of invested capacity that may be shift downwards
            at maximum"
            ":math:`costs_{invest}` ",":attr:`~SinkDSM.investment.ep_costs` ",
            "P", "specific investment annuity"
            ":math:`T` "," ","P", "Overall amount of time steps (cardinality)"
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all DSM components get inflow from bus_elec
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        # Set of DSM Components
        self.multiperiodinvestdsm = Set(initialize=[g for g in group])

        #  ************* VARIABLES *****************************

        # Define bounds for investments in demand response
        def _dsm_investvar_bound_rule(block, g, p):
            """
            Rule definition to bound the
            invested demand response capacity `invest`.
            """
            return (g.multiperiodinvestment.minimum[p],
                    g.multiperiodinvestment.maximum[p])

        # Investment in DR capacity
        self.invest = Var(self.multiperiodinvestdsm,
                          m.PERIODS,
                          within=NonNegativeReals,
                          bounds=_dsm_investvar_bound_rule)

        # Total capacity
        self.total = Var(self.multiperiodinvestdsm,
                         m.PERIODS,
                         within=NonNegativeReals)

        # Old capacity to be decommissioned (due to lifetime)
        # Old capacity is built out of old exogenous and endogenous capacities
        self.old = Var(self.multiperiodinvestdsm,
                       m.PERIODS,
                       within=NonNegativeReals)

        # Old endogenous capacity to be decommissioned (due to lifetime)
        self.old_end = Var(self.multiperiodinvestdsm,
                           m.PERIODS,
                           within=NonNegativeReals)

        # Old exogenous capacity to be decommissioned (due to lifetime)
        self.old_exo = Var(self.multiperiodinvestdsm,
                           m.PERIODS,
                           within=NonNegativeReals)

        # Variable load shift down
        self.dsm_do_shift = Var(self.multiperiodinvestdsm,
                                m.TIMESTEPS, m.TIMESTEPS,
                                initialize=0, within=NonNegativeReals)

        # Variable load shedding
        self.dsm_do_shed = Var(self.multiperiodinvestdsm, m.TIMESTEPS,
                               initialize=0,
                               within=NonNegativeReals)

        # Variable load shift up
        self.dsm_up = Var(self.multiperiodinvestdsm, m.TIMESTEPS,
                          initialize=0,
                          within=NonNegativeReals)

        #  ************* CONSTRAINTS *****************************

        # Handle unit lifetimes
        def _total_dsm_capacity_rule(block):
            """Rule definition for determining total installed
            capacity (taking decommissioning into account)
            """
            for g in group:
                for p in m.PERIODS:
                    if p == 0:
                        expr = (self.total[g, p]
                                == self.invest[g, p]
                                + g.multiperiodinvestment.existing)
                        self.total_dsm_rule.add((g, p), expr)
                    else:
                        expr = (self.total[g, p]
                                == self.invest[g, p]
                                + self.total[g, p - 1]
                                - self.old[g, p])
                        self.total_dsm_rule.add((g, p), expr)

        self.total_dsm_rule = Constraint(group, m.PERIODS,
                                         noruleinit=True)
        self.total_dsm_rule_build = BuildAction(
            rule=_total_dsm_capacity_rule)

        def _old_dsm_capacity_rule_end(block):
            """Rule definition for determining old endogenously installed
            capacity to be decommissioned due to reaching its lifetime
            """
            for g in group:
                lifetime = g.multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    if lifetime <= p:
                        expr = (self.old_end[g, p]
                                == self.invest[g, p - lifetime])
                        self.old_dsm_rule_end.add((g, p), expr)
                    else:
                        expr = (self.old_end[g, p]
                                == 0)
                        self.old_dsm_rule_end.add((g, p), expr)

        self.old_dsm_rule_end = Constraint(group,
                                           m.PERIODS,
                                           noruleinit=True)
        self.old_dsm_rule_end_build = BuildAction(
            rule=_old_dsm_capacity_rule_end)

        def _old_dsm_capacity_rule_exo(block):
            """Rule definition for determining old exogenously given capacity
            to be decommissioned due to reaching its lifetime
            """
            for g in group:
                age = g.multiperiodinvestment.age
                lifetime = g.multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    if lifetime - age == p:
                        expr = (
                            self.old_exo[g, p]
                            == g.multiperiodinvestment.existing)
                        self.old_dsm_rule_exo.add((g, p), expr)
                    else:
                        expr = (self.old_exo[g, p]
                                == 0)
                        self.old_dsm_rule_exo.add((g, p), expr)

        self.old_dsm_rule_exo = Constraint(group,
                                           m.PERIODS,
                                           noruleinit=True)
        self.old_dsm_rule_exo_build = BuildAction(
            rule=_old_dsm_capacity_rule_exo)

        def _old_dsm_capacity_rule(block):
            """Rule definition for determining (overall) old capacity
            to be decommissioned due to reaching its lifetime
            """
            for g in group:
                for p in m.PERIODS:
                    expr = (
                        self.old[g, p]
                        == self.old_end[g, p] + self.old_exo[g, p])
                    self.old_dsm_rule.add((g, p), expr)

        self.old_dsm_rule = Constraint(group,
                                       m.PERIODS,
                                       noruleinit=True)
        self.old_dsm_rule_build = BuildAction(
            rule=_old_dsm_capacity_rule)

        def _shift_shed_vars_rule(block):
            """
            Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if not g.shift_eligibility:
                        lhs = self.dsm_up[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

                    if not g.shed_eligibility:
                        lhs = self.dsm_do_shed[g, t]
                        rhs = 0

                        block.shift_shed_vars.add((g, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Demand Production Relation
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DSM.
            Generator Production == Demand +- DSM
            """
            for p, t in m.TIMEINDEX:
                for g in group:

                    # first time steps: 0 + delay time
                    if t <= g.delay_time:

                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, p, t]
                        # Demand +- DSM
                        rhs = (
                            g.demand[t] * self.total[g, p]
                            + self.dsm_up[g, t]
                            - sum(
                                self.dsm_do_shift[g, tt, t]
                                for tt in range(t + g.delay_time + 1))
                            - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add(
                            (g, p, t), (lhs == rhs))

                    # main use case
                    elif (g.delay_time < t
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, p, t]
                        # Demand +- DSM
                        rhs = (
                            g.demand[t] * self.total[g, p]
                            + self.dsm_up[g, t]
                            - sum(
                                self.dsm_do_shift[g, tt, t]
                                for tt in range(t - g.delay_time,
                                                t + g.delay_time + 1))
                            - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add(
                            (g, p, t), (lhs == rhs))

                    # last time steps: end - delay time
                    else:
                        # Inflow from bus
                        lhs = m.flow[g.inflow, g, p, t]
                        # Demand +- DSM
                        rhs = (
                            g.demand[t] * self.total[g, p]
                            + self.dsm_up[g, t]
                            - sum(
                                self.dsm_do_shift[g, tt, t]
                                for tt in range(t - g.delay_time,
                                                m.TIMESTEPS[-1] + 1))
                            - self.dsm_do_shed[g, t])

                        # add constraint
                        block.input_output_relation.add(
                            (g, p, t), (lhs == rhs))

        self.input_output_relation = Constraint(group, m.TIMEINDEX,
                                                noruleinit=True)
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule)

        # Equation 7 (resp. 7')
        def dsm_up_down_constraint_rule(block):
            """Equation 7 (resp. 7') by Zerrahn & Schill:
            Every upward load shift has to be compensated by downward load
            shifts in a defined time frame. Slightly modified equations for
            the first and last time steps due to variable initialization.
            Efficiency value depicts possible energy losses through
            load shifting (Equation 7').
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # first time steps: 0 + delay time
                    if t <= g.delay_time:

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t + g.delay_time + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

                    # main use case
                    elif (g.delay_time < t
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t - g.delay_time,
                                                  t + g.delay_time + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

                    # last time steps: end - delay time
                    else:

                        # DSM up
                        lhs = self.dsm_up[g, t] * g.efficiency
                        # DSM down
                        rhs = sum(self.dsm_do_shift[g, t, tt]
                                  for tt in range(t - g.delay_time,
                                                  m.TIMESTEPS[-1] + 1))

                        # add constraint
                        block.dsm_updo_constraint.add((g, t), (lhs == rhs))

        self.dsm_updo_constraint = Constraint(group, m.TIMESTEPS,
                                              noruleinit=True)
        self.dsm_updo_constraint_build = BuildAction(
            rule=dsm_up_down_constraint_rule)

        # Equation 8
        def dsm_up_constraint_rule(block):
            """Equation 8 by Zerrahn & Schill:
            Realised upward load shift at time t has to be smaller than
            upward DSM capacity at time t.
            """
            for p, t in m.TIMEINDEX:
                for g in group:
                    # DSM up
                    lhs = self.dsm_up[g, t]
                    # Capacity dsm_up
                    rhs = (g.capacity_up[t] * self.total[g, p]
                           * g.flex_share_up)

                    # add constraint
                    block.dsm_up_constraint.add((g, p, t), (lhs <= rhs))

        self.dsm_up_constraint = Constraint(group, m.TIMEINDEX,
                                            noruleinit=True)
        self.dsm_up_constraint_build = BuildAction(rule=dsm_up_constraint_rule)

        # Equation 9 (modified)
        def dsm_do_constraint_rule(block):
            """Equation 9 by Zerrahn & Schill:
            Realised downward load shift at time t has to be smaller than
            downward DSM capacity at time t.
            """
            for p, tt in m.TIMEINDEX:
                for g in group:

                    # first times steps: 0 + delay
                    if tt <= g.delay_time:

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = (g.capacity_down[tt] * self.total[g, p]
                               * g.flex_share_down)

                        # add constraint
                        block.dsm_do_constraint.add(
                            (g, p, tt), (lhs <= rhs))

                    # main use case
                    elif (g.delay_time < tt
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt - g.delay_time,
                                                  tt + g.delay_time + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = (g.capacity_down[tt] * self.total[g, p]
                               * g.flex_share_down)

                        # add constraint
                        block.dsm_do_constraint.add(
                            (g, p, tt), (lhs <= rhs))

                    # last time steps: end - delay time
                    else:

                        # DSM down
                        lhs = (sum(self.dsm_do_shift[g, t, tt]
                                   for t in range(tt - g.delay_time,
                                                  m.TIMESTEPS[-1] + 1))
                               + self.dsm_do_shed[g, tt])
                        # Capacity DSM down
                        rhs = (g.capacity_down[tt] * self.total[g, p]
                               * g.flex_share_down)

                        # add constraint
                        block.dsm_do_constraint.add(
                            (g, p, tt), (lhs <= rhs))

        self.dsm_do_constraint = Constraint(group, m.TIMEINDEX,
                                            noruleinit=True)
        self.dsm_do_constraint_build = BuildAction(
            rule=dsm_do_constraint_rule)

        # Equation 10
        def c2_constraint_rule(block):
            """Equation 10 by Zerrahn & Schill:
            The realised DSM up or down at time T has to be smaller than
            the maximum downward or upward capacity at time T. Therefore, in
            total each individual DSM unit within the modeled portfolio
            can only be shifted up OR down at a given time.
            """
            for p, tt in m.TIMEINDEX:
                for g in group:

                    # first times steps: 0 + delay time
                    if tt <= g.delay_time:

                        # DSM up/down
                        lhs = (
                            self.dsm_up[g, tt]
                            + sum(
                                self.dsm_do_shift[g, t, tt]
                                for t in range(tt + g.delay_time + 1))
                            + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = (max(g.capacity_up[tt] * g.flex_share_up,
                                   g.capacity_down[tt] * g.flex_share_down)
                               * self.total[g, p])

                        # add constraint
                        block.C2_constraint.add((g, p, tt), (lhs <= rhs))

                    elif (g.delay_time < tt
                          <= m.TIMESTEPS[-1] - g.delay_time):

                        # DSM up/down
                        lhs = (
                            self.dsm_up[g, tt]
                            + sum(
                                self.dsm_do_shift[g, t, tt]
                                for t in range(tt - g.delay_time,
                                               tt + g.delay_time + 1))
                            + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = (max(g.capacity_up[tt] * g.flex_share_up,
                                   g.capacity_down[tt] * g.flex_share_down)
                               * self.total[g, p])

                        # add constraint
                        block.C2_constraint.add((g, p, tt), (lhs <= rhs))

                    else:

                        # DSM up/down
                        lhs = (
                            self.dsm_up[g, tt]
                            + sum(
                                self.dsm_do_shift[g, t, tt]
                                for t in range(tt - g.delay_time,
                                               m.TIMESTEPS[-1] + 1))
                            + self.dsm_do_shed[g, tt])
                        # max capacity at tt
                        rhs = (max(g.capacity_up[tt] * g.flex_share_up,
                                   g.capacity_down[tt] * g.flex_share_down)
                               * self.total[g, p])

                        # add constraint
                        block.C2_constraint.add((g, p, tt), (lhs <= rhs))

        self.C2_constraint = Constraint(group, m.TIMEINDEX, noruleinit=True)
        self.C2_constraint_build = BuildAction(rule=c2_constraint_rule)

        def recovery_constraint_rule(block):
            """Equation 11 by Zerrahn & Schill:
            A recovery time is introduced to account for the fact that
            there may be some restrictions before the next load shift
            may take place. Rule is only applicable if a recovery time
            is defined.
            """
            for p, t in m.TIMEINDEX:
                for g in group:

                    # No need to build constraint if no recovery
                    # time is defined.
                    if g.recovery_time_shift not in [None, 0]:

                        # main use case
                        if t <= m.TIMESTEPS[-1] - g.recovery_time_shift:

                            # DSM up
                            lhs = sum(self.dsm_up[g, tt] for tt in
                                      range(t, t + g.recovery_time_shift))
                            # max energy shift for shifting process
                            rhs = (g.capacity_up[t] * self.total[g, p]
                                   * g.flex_share_up * g.delay_time
                                   * m.timeincrement[t])
                            # add constraint
                            block.recovery_constraint.add(
                                (g, p, t), (lhs <= rhs))

                        # last time steps: end - recovery time
                        else:

                            # DSM up
                            lhs = sum(self.dsm_up[g, tt] for tt in
                                      range(t, m.TIMESTEPS[-1] + 1))
                            # max energy shift for shifting process
                            rhs = (g.capacity_up[t] * self.total[g, p]
                                   * g.flex_share_up * g.delay_time
                                   * m.timeincrement[t])
                            # add constraint
                            block.recovery_constraint.add(
                                (g, p, t), (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.recovery_constraint = Constraint(group, m.TIMEINDEX,
                                              noruleinit=True)
        self.recovery_constraint_build = BuildAction(
            rule=recovery_constraint_rule)

        # Equation 9a from Zerrahn and Schill (2015b)
        def shed_limit_constraint_rule(block):
            """The following constraint is highly similar to equation 9a
            from Zerrahn and Schill (2015b): A recovery time for load
            shedding is introduced in order to limit the overall amount
            of shedded energy.
            """
            for p, t in m.TIMEINDEX:
                for g in group:

                    if g.shed_eligibility:

                        # main use case
                        if t <= m.TIMESTEPS[-1] - g.recovery_time_shed:

                            # DSM up
                            lhs = sum(self.dsm_do_shed[g, tt] for tt in
                                      range(t, t + g.recovery_time_shed))
                            # max energy shift for shifting process
                            rhs = (g.capacity_down[t] * self.total[g, p]
                                   * g.flex_share_down * g.shed_time
                                   * m.timeincrement[t])
                            # add constraint
                            block.shed_limit_constraint.add((g, p, t),
                                                            (lhs <= rhs))

                        # last time steps: end - recovery time
                        else:

                            # DSM up
                            lhs = sum(self.dsm_do_shed[g, tt] for tt in
                                      range(t, m.TIMESTEPS[-1] + 1))
                            # max energy shift for shifting process
                            rhs = (g.capacity_down[t] * self.total[g, p]
                                   * g.flex_share_down * g.shed_time
                                   * m.timeincrement[t])
                            # add constraint
                            block.shed_limit_constraint.add((g, p, t),
                                                            (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.shed_limit_constraint = Constraint(group, m.TIMEINDEX,
                                                noruleinit=True)
        self.shed_limit_constraint_build = BuildAction(
            rule=shed_limit_constraint_rule)

    def _objective_expression(self):
        r"""Objective expression with variable, investment and fixed costs
        for DSM """

        m = self.parent_block()

        investment_costs = 0
        variable_costs = 0
        fixed_costs = 0

        for g in self.multiperiodinvestdsm:
            if g.multiperiodinvestment.ep_costs is not None:
                lifetime = g.multiperiodinvestment.lifetime
                interest = g.multiperiodinvestment.interest_rate
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
                        capex=g.multiperiodinvestment.ep_costs[p],
                        n=lifetime,
                        wacc=interest)
                    investment_costs += (
                        self.invest[g, p] * annuity * lifetime
                        * ((1 + m.discount_rate) ** (-p))
                    )
            else:
                raise ValueError("Missing value for investment costs!")

            for p, t in m.TIMEINDEX:
                variable_costs += (self.dsm_up[g, t]
                                   * m.objective_weighting[t]
                                   * g.cost_dsm_up[p]
                                   * ((1 + m.discount_rate) ** -p))
                variable_costs += ((sum(self.dsm_do_shift[g, t, tt]
                                        for tt in m.TIMESTEPS)
                                    * g.cost_dsm_down_shift[p]
                                    + self.dsm_do_shed[g, t]
                                    * g.cost_dsm_down_shed[p])
                                   * m.objective_weighting[t]
                                   * ((1 + m.discount_rate) ** -p))

            if g.multiperiodinvestment.fixed_costs[0] is not None:
                lifetime = g.multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    fixed_costs += (
                        sum(self.invest[g, p]
                            * g.multiperiodinvestment.fixed_costs[pp]
                            * ((1 + m.discount_rate) ** (-pp))
                            for pp in range(p, p + lifetime)
                            )
                        * ((1 + m.discount_rate) ** (-p))
                    )

        self.cost = Expression(
            expr=investment_costs + fixed_costs + variable_costs
        )

        return self.cost


class SinkDSMDLRBlock(SimpleBlock):
    r"""Constraints for SinkDSM with "DLR" approach

    **The following constraints are created for approach = 'DLR':**

    .. _SinkDSMDLR equations:

    .. math::
        &
        (1) \quad DSM_{h, t}^{up} = 0 \quad \forall h \in H_{DR}
        \forall t \in \mathbb{T}
        \quad if \space eligibility_{shift} = False \\
        &
        (2) \quad DSM_{t}^{do, shed} = 0 \quad \forall t \in \mathbb{T}
        \quad if \space eligibility_{shed} = False \\
        &
        (3) \quad \dot{E}_{t} = demand_{t} \cdot demand_{max} +
        \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDo} - DSM_{h, t}^{do, shift}
        - DSM_{h, t}^{balanceUp}) - DSM_{t}^{do, shed}
        \quad \forall t \in \mathbb{T} \\
        &
        (4) \quad DSM_{h, t}^{balanceDo} =
        \frac{DSM_{h, t - h}^{do, shift}}{\eta}
        \quad \forall h \in H_{DR} \forall t \in [h..T] \\
        &
        (5) \quad DSM_{h, t}^{balanceUp} =
        DSM_{h, t-h}^{up} \cdot \eta
        \quad \forall h \in H_{DR} \forall t \in [h..T] \\
        &
        (6) \quad DSM_{h, t}^{do, shift} = 0
        \quad \forall h \in H_{DR}
        \forall t \in [T - h..T] \\
        &
        (7) \quad DSM_{h, t}^{up} = 0
        \quad \forall h \in H_{DR}
        \forall t \in [T - h..T] \\
        &
        (8) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{do, shift}
        + DSM_{h, t}^{balanceUp}) + DSM_{t}^{do, shed}
        \leq E_{t}^{do} \cdot E_{max, do}
        \quad \forall t \in \mathbb{T} \\
        &
        (9) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDo})
        \leq E_{t}^{up} \cdot E_{max, up}
        \quad \forall t \in \mathbb{T} \\
        &
        (10) \quad \Delta t \cdot \displaystyle\sum_{h=1}^{H_{DR}}
        (DSM_{h, t}^{do, shift} - DSM_{h, t}^{balanceDo} \cdot \eta)
        = W_{t}^{levelDo} - W_{t-1}^{levelDo}
        \quad \forall t \in [1..T] \\
        &
        (11) \quad \Delta t \cdot \displaystyle\sum_{h=1}^{H_{DR}}
        (DSM_{h, t}^{up} \cdot \eta - DSM_{h, t}^{balanceUp})
        = W_{t}^{levelUp} - W_{t-1}^{levelUp}
        \quad \forall t \in [1..T] \\
        &
        (12) \quad W_{t}^{levelDo} \leq \overline{E}_{t}^{do}
        \cdot E_{max, do} \cdot t_{shift}
        \quad \forall t \in \mathbb{T} \\
        &
        (13) \quad W_{t}^{levelUp} \leq \overline{E}_{t}^{up}
        \cdot E_{max, up} \cdot t_{shift}
        \quad \forall t \in \mathbb{T} \\
        &
        (14) \quad \displaystyle\sum_{t=0}^{T} DSM_{t}^{do, shed}
        \leq E_{max, do} \cdot \overline{E}_{t}^{do} \cdot t_{shed}
        \cdot n^{yearLimitShed} \\
        &
        (15) \quad \displaystyle\sum_{t=0}^{T} \sum_{h=1}^{H_{DR}}
        DSM_{h, t}^{do, shift}
        \leq E_{max, do} \cdot \overline{E}_{t}^{do} \cdot t_{shift}
        \cdot n^{yearLimitShift} \\
        (optional \space constraint) \\
        &
        (16) \quad \displaystyle\sum_{t=0}^{T} \sum_{h=1}^{H_{DR}}
        DSM_{h, t}^{up}
        \leq E_{max, up} \cdot \overline{E}_{t}^{up} \cdot t_{shift}
        \cdot n^{yearLimitShift} \\
        (optional \space constraint) \\
        &
        (17) \quad \displaystyle\sum_{h=1}^{H_{DR}} DSM_{h, t}^{do, shift}
        \leq E_{max, do} \cdot \overline{E}_{t}^{do}
        \cdot t_{shift} -
        \displaystyle\sum_{t'=1}^{t_{dayLimit}} \sum_{h=1}^{H_{DR}}
        DSM_{h, t - t'}^{do, shift}
        \quad \forall t \in [t-t_{dayLimit}..T] \\
        (optional \space constraint) \\
        &
        (18) \quad \displaystyle\sum_{h=1}^{H_{DR}} DSM_{h, t}^{up}
        \leq E_{max, up} \cdot \overline{E}_{t}^{up}
        \cdot t_{shift} -
        \displaystyle\sum_{t'=1}^{t_{dayLimit}} \sum_{h=1}^{H_{DR}}
        DSM_{h, t - t'}^{up}
        \quad \forall t \in [t-t_{dayLimit}..T] \\
        (optional \space constraint) \\
        &
        (19) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDo}
        + DSM_{h, t}^{do, shift} + DSM_{h, t}^{balanceUp})
        + DSM_{t}^{do, shed}
        \leq \max \{E_{t}^{up} \cdot E_{max, up},
        E_{t}^{do} \cdot E_{max, do} \}
        \quad \forall t \in \mathbb{T} \\
        (optional \space constraint) \\
        &

    *Note*: For the sake of readability, the handling of indices is not
    displayed here. E.g. evaluating a variable for t-L may lead to a negative
    and therefore infeasible index.
    This is addressed by limiting the sums to non-negative indices within the
    model index bounds. Please refer to the constraints implementation
    themselves.

    **The following parts of the objective function are created:**

    .. math::
        \sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up} + DSM_{h, t}^{balanceDo})
        \cdot cost_{t}^{dsm, up}
        + \sum_{h=1}^{H_{DR}} (DSM_{h, t}^{do, shift} + DSM_{h, t}^{balanceUp})
        \cdot cost_{t}^{dsm, do, shift}
        + DSM_{t}^{do, shed} \cdot cost_{t}^{dsm, do, shed}
        \quad \forall t \in \mathbb{T} \\

    **Table: Symbols and attribute names of variables and parameters**

        .. csv-table:: Variables (V) and Parameters (P)
            :header: "symbol", "attribute", "type", "explanation"
            :widths: 1, 1, 1, 1

            ":math:`DSM_{h, t}^{up}` ",":attr:`~SinkDSM.dsm_up[g,h,t]`",
            "V", "DSM up shift (additional load) in hour t with delay time h"
            ":math:`DSM_{h, t}^{do, shift}` ",
            ":attr:`~SinkDSM.dsm_do_shift[g,h, t]`",
            "V", "DSM down shift (less load) in hour t with delay time h"
            ":math:`DSM_{h, t}^{balanceUp}` ",
            ":attr:`~SinkDSM.balance_dsm_up[g,h,t]`",
            "V", "DSM down shift (less load) in hour t with delay time h
            to balance previous upshift"
            ":math:`DSM_{h, t}^{balanceDo}` ",
            ":attr:`~SinkDSM.balance_dsm_do[g,h,t]`",
            "V", "DSM up shift (additional load) in hour t with delay time h
            to balance previous downshift"
            ":math:`DSM_{t}^{do, shed}` ",
            ":attr:`~SinkDSM.dsm_do_shed[g, t]` ",
            "V","DSM shedded (capacity shedded, i.e. not compensated for)"
            ":math:`\dot{E}_{t}` ",":attr:`flow[g,t]`","V","Energy
            flowing in from (electrical) inflow bus"
            ":math:`h`","element of :attr:`~SinkDSM.delay_time`","P",
            "delay time for load shift (integer value from set of feasible
            delay times per DSM portfolio)
            (time until the energy balance has to be levelled out again;
            roundtrip time of one load shifting cycle, i.e. time window
            for upshift and compensating downshift)"
            ":math:`H_{DR}`",
            "`range(length(:attr:`~SinkDSM.delay_time`) + 1)`",
            "P", "Set of feasible delay times for load shift of a certain
            DSM portfolio
            (time until the energy balance has to be levelled out again;
            roundtrip time of one load shifting cycle, i.e. time window
            for upshift and compensating downshift)"
            ":math:`t_{shift}`",":attr:`~SinkDSM.shift_time`","P",
            "Maximum time for a shift in one direction, i. e. maximum time
            for an upshift or a downshift in a load shifting cycle"
            ":math:`t_{she}`",":attr:`~SinkDSM.shed_time`","P",
            "Maximum time for one load shedding process"
            ":math:`demand_{t}`",":attr:`~SinkDSM.demand[t]`","P",
            "(Electrical) demand series (normalized)"
            ":math:`demand_{max}`",":attr:`~SinkDSM.max_demand`","P",
            "Maximum demand value"
            ":math:`E_{t}^{do}`",":attr:`~SinkDSM.capacity_down[t]`","P",
            "Capacity  allowed for a load adjustment downwards (normalized)
            (DSM down shift + DSM shedded)"
            ":math:`E_{t}^{up}`",":attr:`~SinkDSM.capacity_up[t]`","P",
            "Capacity allowed for a shift upwards (normalized) (DSM up shift)"
            ":math:`E_{do, max}`",":attr:`~SinkDSM.max_capacity_down`","P",
            "Maximum capacity allowed for a load adjustment downwards
            (DSM down shift + DSM shedded)"
            ":math:`E_{up, max}`",":attr:`~SinkDSM.max_capacity_up`","P",
            "Capacity allowed for a shift upwards (normalized) (DSM up shift)"
            ":math:`\eta`",":attr:`~SinkDSM.efficiency`","P", "Efficiency
            loss for load shifting processes"
            ":math:`\mathbb{T}` "," ","P", "Set of time steps"
            ":math:`T` "," ","P", "Overall amount of time steps (cardinality)"
            ":math:`eligibility_{shift}` ",
            ":attr:`~SinkDSM.shift_eligibility`","P",
            "Boolean parameter indicating if unit can be used for
            load shifting"
            ":math:`eligibility_{shed}` ",
            ":attr:`~SinkDSM.shed_eligibility`","P",
            "Boolean parameter indicating if unit can be used for
            load shedding"
            ":math:`cost_{t}^{dsm, up}` ", ":attr:`~SinkDSM.cost_dsm_up[t]`",
            "P", "Variable costs for an upwards shift"
            ":math:`cost_{t}^{dsm, do, shift}` ",
            ":attr:`~SinkDSM.cost_dsm_down_shift[t]`","P",
            "Variable costs for a downwards shift (load shifting)"
            ":math:`cost_{t}^{dsm, do, shed}` ",
            ":attr:`~SinkDSM.cost_dsm_down_shed[t]`","P",
            "Variable costs for shedding load"
            ":math:`\Delta t`",":attr:`~models.Model.timeincrement`","P",
            "The time increment of the model"
            ":math:`n_{yearLimitshift}`",":attr:`~SinkDSM.n_yearLimitShift`",
            "P", "Maximum allowed number of load shifts (at full capacity)
            in the optimization timeframe"
            ":math:`n_{yearLimitshed}`",":attr:`~SinkDSM.n_yearLimitShed`",
            "P", "Maximum allowed number of load sheds (at full capacity)
            in the optimization timeframe"
            ":math:`t_{dayLimit}`",":attr:`~SinkDSM.t_dayLimit`",
            "P", "Maximum duration of load shifts at full capacity per day
            resp. in the last hours before the current"
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all DSM components get inflow from a bus
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        # Set of DR Components
        self.DR = Set(initialize=[n for n in group])

        # Depict different delay_times per unit via a mapping
        map_DR_H = {
            k: v for k, v in zip([n for n in group],
                                 [n.delay_time for n in group])
        }

        unique_H = list(
            set(itertools.chain.from_iterable(map_DR_H.values()))
        )
        self.H = Set(initialize=unique_H)

        self.DR_H = Set(within=self.DR * self.H,
                        initialize=[(dr, h)
                                    for dr in map_DR_H
                                    for h in map_DR_H[dr]])

        #  ************* VARIABLES *****************************

        # Variable load shift down (capacity)
        self.dsm_do_shift = Var(self.DR_H, m.TIMESTEPS, initialize=0,
                                within=NonNegativeReals)

        # Variable for load shedding (capacity)
        self.dsm_do_shed = Var(self.DR, m.TIMESTEPS, initialize=0,
                               within=NonNegativeReals)

        # Variable load shift up (capacity)
        self.dsm_up = Var(self.DR_H, m.TIMESTEPS, initialize=0,
                          within=NonNegativeReals)

        # Variable balance load shift down through upwards shift (capacity)
        self.balance_dsm_do = Var(self.DR_H, m.TIMESTEPS, initialize=0,
                                  within=NonNegativeReals)

        # Variable balance load shift up through downwards shift (capacity)
        self.balance_dsm_up = Var(self.DR_H, m.TIMESTEPS, initialize=0,
                                  within=NonNegativeReals)

        # Variable fictious DR storage level for downwards load shifts (energy)
        self.dsm_do_level = Var(self.DR, m.TIMESTEPS, initialize=0,
                                within=NonNegativeReals)

        # Variable fictious DR storage level for upwards load shifts (energy)
        self.dsm_up_level = Var(self.DR, m.TIMESTEPS, initialize=0,
                                within=NonNegativeReals)

        #  ************* CONSTRAINTS *****************************

        def _shift_shed_vars_rule(block):
            """Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if not g.shift_eligibility:
                            lhs = self.dsm_up[g, h, t]
                            rhs = 0

                            block.shift_shed_vars.add((g, h, t), (lhs == rhs))

                        if not g.shed_eligibility:
                            lhs = self.dsm_do_shed[g, t]
                            rhs = 0

                            block.shift_shed_vars.add((g, h, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, self.H, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Relation between inflow and effective Sink consumption
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DR.
            Bus outflow == Demand +- DR (i.e. effective Sink consumption)
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # outflow from bus
                    lhs = m.flow[g.inflow, g, t]

                    # Demand +- DR
                    rhs = (g.demand[t] * g.max_demand +
                           + sum(self.dsm_up[g, h, t]
                                 + self.balance_dsm_do[g, h, t]
                                 - self.dsm_do_shift[g, h, t]
                                 - self.balance_dsm_up[g, h, t]
                                 for h in g.delay_time)
                           - self.dsm_do_shed[g, t])

                    # add constraint
                    block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation = Constraint(group, m.TIMESTEPS,
                                                noruleinit=True)
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule)

        # Equation 4.8
        def capacity_balance_red_rule(block):
            """Load reduction must be balanced by load increase
            within delay_time
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if g.shift_eligibility:

                            # main use case
                            if t >= h:
                                # balance load reduction
                                lhs = self.balance_dsm_do[g, h, t]

                                # load reduction (efficiency considered)
                                rhs = (self.dsm_do_shift[g, h, t - h]
                                       / g.efficiency)

                                # add constraint
                                block.capacity_balance_red.add((g, h, t),
                                                               (lhs == rhs))

                            # no balancing for the first timestep
                            elif t == m.TIMESTEPS[1]:
                                lhs = self.balance_dsm_do[g, h, t]
                                rhs = 0

                                block.capacity_balance_red.add((g, h, t),
                                                               (lhs == rhs))

                            else:
                                pass  # return(Constraint.Skip)

                        # if only shedding is possible, balancing variable is 0
                        else:
                            lhs = self.balance_dsm_do[g, h, t]
                            rhs = 0

                            block.capacity_balance_red.add((g, h, t),
                                                           (lhs == rhs))

        self.capacity_balance_red = Constraint(group, self.H, m.TIMESTEPS,
                                               noruleinit=True)
        self.capacity_balance_red_build = BuildAction(
            rule=capacity_balance_red_rule)

        # Equation 4.9
        def capacity_balance_inc_rule(block):
            """Load increased must be balanced by load reduction
            within delay_time
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if g.shift_eligibility:

                            # main use case
                            if t >= h:
                                # balance load increase
                                lhs = self.balance_dsm_up[g, h, t]

                                # load increase (efficiency considered)
                                rhs = self.dsm_up[g, h, t - h] * g.efficiency

                                # add constraint
                                block.capacity_balance_inc.add((g, h, t),
                                                               (lhs == rhs))

                            # no balancing for the first timestep
                            elif t == m.TIMESTEPS[1]:
                                lhs = self.balance_dsm_up[g, h, t]
                                rhs = 0

                                block.capacity_balance_inc.add((g, h, t),
                                                               (lhs == rhs))

                            else:
                                pass  # return(Constraint.Skip)

                        # if only shedding is possible, balancing variable is 0
                        else:
                            lhs = self.balance_dsm_up[g, h, t]
                            rhs = 0

                            block.capacity_balance_inc.add((g, h, t),
                                                           (lhs == rhs))

        self.capacity_balance_inc = Constraint(group, self.H, m.TIMESTEPS,
                                               noruleinit=True)
        self.capacity_balance_inc_build = BuildAction(
            rule=capacity_balance_inc_rule)

        # Fix: prevent shifts which cannot be compensated
        def no_comp_red_rule(block):
            """Prevent downwards shifts that cannot be balanced anymore
            within the optimization timeframe
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.fixes:
                        for h in g.delay_time:

                            if t > m.TIMESTEPS[-1] - h:
                                # no load reduction anymore (dsm_do_shift = 0)
                                lhs = self.dsm_do_shift[g, h, t]
                                rhs = 0
                                block.no_comp_red.add((g, h, t), (lhs == rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.no_comp_red = Constraint(group, self.H, m.TIMESTEPS,
                                      noruleinit=True)
        self.no_comp_red_build = BuildAction(
            rule=no_comp_red_rule)

        # Fix: prevent shifts which cannot be compensated
        def no_comp_inc_rule(block):
            """Prevent upwards shifts that cannot be balanced anymore
            within the optimization timeframe
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.fixes:
                        for h in g.delay_time:

                            if t > m.TIMESTEPS[-1] - h:
                                # no load increase anymore (dsm_up = 0)
                                lhs = self.dsm_up[g, h, t]
                                rhs = 0
                                block.no_comp_inc.add((g, h, t), (lhs == rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.no_comp_inc = Constraint(group, self.H, m.TIMESTEPS,
                                      noruleinit=True)
        self.no_comp_inc_build = BuildAction(
            rule=no_comp_inc_rule)

        # Equation 4.11
        def availability_red_rule(block):
            """Load reduction must be smaller than or equal to the
            (time-dependent) capacity limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # load reduction
                    lhs = (sum(self.dsm_do_shift[g, h, t]
                               + self.balance_dsm_up[g, h, t]
                               for h in g.delay_time)
                           + self.dsm_do_shed[g, t])

                    # upper bound
                    rhs = g.capacity_down[t] * g.max_capacity_down

                    # add constraint
                    block.availability_red.add((g, t), (lhs <= rhs))

        self.availability_red = Constraint(group, m.TIMESTEPS,
                                           noruleinit=True)
        self.availability_red_build = BuildAction(
            rule=availability_red_rule)

        # Equation 4.12
        def availability_inc_rule(block):
            """Load increase must be smaller than or equal to the
            (time-dependent) capacity limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # load increase
                    lhs = sum(self.dsm_up[g, h, t]
                              + self.balance_dsm_do[g, h, t]
                              for h in g.delay_time)

                    # upper bound
                    rhs = g.capacity_up[t] * g.max_capacity_up

                    # add constraint
                    block.availability_inc.add((g, t), (lhs <= rhs))

        self.availability_inc = Constraint(group, m.TIMESTEPS,
                                           noruleinit=True)
        self.availability_inc_build = BuildAction(
            rule=availability_inc_rule)

        # Equation 4.13
        def dr_storage_red_rule(block):
            """Fictious demand response storage level for load reductions
            transition equation
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # avoid timesteps prior to t = 0
                    if t > 0:
                        # reduction minus balancing of reductions
                        lhs = (m.timeincrement[t]
                               * sum((self.dsm_do_shift[g, h, t]
                                      - self.balance_dsm_do[g, h, t]
                                      * g.efficiency)
                                     for h in g.delay_time))

                        # load reduction storage level transition
                        rhs = (self.dsm_do_level[g, t]
                               - self.dsm_do_level[g, t - 1])

                        # add constraint
                        block.dr_storage_red.add((g, t), (lhs == rhs))

                    else:
                        lhs = self.dsm_do_level[g, t]
                        rhs = (m.timeincrement[t]
                               * sum(self.dsm_do_shift[g, h, t]
                                     for h in g.delay_time))
                        block.dr_storage_red.add((g, t), (lhs == rhs))

        self.dr_storage_red = Constraint(group, m.TIMESTEPS,
                                         noruleinit=True)
        self.dr_storage_red_build = BuildAction(
            rule=dr_storage_red_rule)

        # Equation 4.14
        def dr_storage_inc_rule(block):
            """Fictious demand response storage level for load increase
            transition equation
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # avoid timesteps prior to t = 0
                    if t > 0:
                        # increases minus balancing of reductions
                        lhs = (m.timeincrement[t]
                               * sum((self.dsm_up[g, h, t]
                                      * g.efficiency
                                      - self.balance_dsm_up[g, h, t])
                                     for h in g.delay_time))

                        # load increase storage level transition
                        rhs = (self.dsm_up_level[g, t]
                               - self.dsm_up_level[g, t - 1])

                        # add constraint
                        block.dr_storage_inc.add((g, t), (lhs == rhs))

                    else:
                        # pass  # return(Constraint.Skip)
                        lhs = self.dsm_up_level[g, t]
                        rhs = (m.timeincrement[t]
                               * sum(self.dsm_up[g, h, t]
                                     for h in g.delay_time))
                        block.dr_storage_inc.add((g, t), (lhs == rhs))

        self.dr_storage_inc = Constraint(group, m.TIMESTEPS,
                                         noruleinit=True)
        self.dr_storage_inc_build = BuildAction(
            rule=dr_storage_inc_rule)

        # Equation 4.15
        def dr_storage_limit_red_rule(block):
            """Fictious demand response storage level for load reduction limit
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.shift_eligibility:
                        # fictious demand response load reduction storage level
                        lhs = self.dsm_do_level[g, t]

                        # maximum (time-dependent) available shifting capacity
                        rhs = (g.capacity_down_mean * g.max_capacity_down
                               * g.shift_time)

                        # add constraint
                        block.dr_storage_limit_red.add((g, t), (lhs <= rhs))

                    else:
                        lhs = self.dsm_do_level[g, t]
                        # Force storage level and thus dsm_do_shift to 0
                        rhs = 0

                        # add constraint
                        block.dr_storage_limit_red.add((g, t), (lhs <= rhs))

        self.dr_storage_limit_red = Constraint(group, m.TIMESTEPS,
                                               noruleinit=True)
        self.dr_storage_level_red_build = BuildAction(
            rule=dr_storage_limit_red_rule)

        # Equation 4.16
        def dr_storage_limit_inc_rule(block):
            """Fictious demand response storage level for load increase limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # fictious demand response load reduction storage level
                    lhs = self.dsm_up_level[g, t]

                    # maximum (time-dependent) available shifting capacity
                    rhs = (g.capacity_up_mean * g.max_capacity_up
                           * g.shift_time)

                    # add constraint
                    block.dr_storage_limit_inc.add((g, t), (lhs <= rhs))

        self.dr_storage_limit_inc = Constraint(group, m.TIMESTEPS,
                                               noruleinit=True)
        self.dr_storage_level_inc_build = BuildAction(
            rule=dr_storage_limit_inc_rule)

        # Equation 4.17' -> load shedding
        def dr_yearly_limit_shed_rule(block):
            """Introduce overall annual (energy) limit for load shedding resp.
            overall limit for optimization timeframe considered
            A year limit in contrast to Gils (2015) is defined a mandatory
            parameter here in order to achieve an approach comparable
            to the others.
            """
            for g in group:

                if g.shed_eligibility:
                    # sum of all load reductions
                    lhs = sum(self.dsm_do_shed[g, t]
                              for t in m.TIMESTEPS)

                    # year limit
                    rhs = (g.capacity_down_mean * g.max_capacity_down
                           * g.shed_time * g.n_yearLimit_shed)

                    # add constraint
                    block.dr_yearly_limit_shed.add(g, (lhs <= rhs))

                else:
                    pass  # return(Constraint.Skip)

        self.dr_yearly_limit_shed = Constraint(group, noruleinit=True)
        self.dr_yearly_limit_shed_build = BuildAction(
            rule=dr_yearly_limit_shed_rule)

        # ************* Optional Constraints *****************************

        # Equation 4.17
        def dr_yearly_limit_red_rule(block):
            """Introduce overall annual (energy) limit for load reductions
            resp. overall limit for optimization timeframe considered
            """
            for g in group:

                if g.ActivateYearLimit:
                    # sum of all load reductions
                    lhs = sum(sum(self.dsm_do_shift[g, h, t]
                                  for h in g.delay_time)
                              for t in m.TIMESTEPS)

                    # year limit
                    rhs = (g.capacity_down_mean * g.max_capacity_down
                           * g.shift_time * g.n_yearLimit_shift)

                    # add constraint
                    block.dr_yearly_limit_red.add(g, (lhs <= rhs))

                else:
                    pass  # return(Constraint.Skip)

        self.dr_yearly_limit_red = Constraint(group, noruleinit=True)
        self.dr_yearly_limit_red_build = BuildAction(
            rule=dr_yearly_limit_red_rule)

        # Equation 4.18
        def dr_yearly_limit_inc_rule(block):
            """Introduce overall annual (energy) limit for load increases
            resp. overall limit for optimization timeframe considered
            """
            for g in group:

                if g.ActivateYearLimit:
                    # sum of all load increases
                    lhs = sum(sum(self.dsm_up[g, h, t]
                                  for h in g.delay_time)
                              for t in m.TIMESTEPS)

                    # year limit
                    rhs = (g.capacity_up_mean * g.max_capacity_up
                           * g.shift_time * g.n_yearLimit_shift)

                    # add constraint
                    block.dr_yearly_limit_inc.add(g, (lhs <= rhs))

                else:
                    pass  # return(Constraint.Skip)

        self.dr_yearly_limit_inc = Constraint(group, noruleinit=True)
        self.dr_yearly_limit_inc_build = BuildAction(
            rule=dr_yearly_limit_inc_rule)

        # Equation 4.19
        def dr_daily_limit_red_rule(block):
            """Introduce rolling (energy) limit for load reductions
            This effectively limits DR utilization dependent on
            activations within previous hours.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.ActivateDayLimit:
                        # main use case
                        if t >= g.t_dayLimit:

                            # load reduction
                            lhs = sum(self.dsm_do_shift[g, h, t]
                                      for h in g.delay_time)

                            # daily limit
                            rhs = (
                                g.capacity_down_mean * g.max_capacity_down
                                * g.shift_time
                                - sum(sum(self.dsm_do_shift[g, h, t - t_dash]
                                          for h in g.delay_time)
                                      for t_dash
                                      in range(1, int(g.t_dayLimit) + 1))
                            )

                            # add constraint
                            block.dr_daily_limit_red.add((g, t), (lhs <= rhs))

                        else:
                            pass  # return(Constraint.Skip)

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_daily_limit_red = Constraint(group, m.TIMESTEPS,
                                             noruleinit=True)
        self.dr_daily_limit_red_build = BuildAction(
            rule=dr_daily_limit_red_rule)

        # Equation 4.20
        def dr_daily_limit_inc_rule(block):
            """Introduce rolling (energy) limit for load increases
            This effectively limits DR utilization dependent on
            activations within previous hours.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.ActivateDayLimit:
                        # main use case
                        if t >= g.t_dayLimit:

                            # load increase
                            lhs = sum(self.dsm_up[g, h, t]
                                      for h in g.delay_time)

                            # daily limit
                            rhs = (
                                g.capacity_up_mean * g.max_capacity_up
                                * g.shift_time
                                - sum(sum(self.dsm_up[g, h, t - t_dash]
                                          for h in g.delay_time)
                                      for t_dash
                                      in range(1, int(g.t_dayLimit) + 1))
                            )

                            # add constraint
                            block.dr_daily_limit_inc.add((g, t), (lhs <= rhs))

                        else:
                            pass  # return(Constraint.Skip)

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_daily_limit_inc = Constraint(group, m.TIMESTEPS,
                                             noruleinit=True)
        self.dr_daily_limit_inc_build = BuildAction(
            rule=dr_daily_limit_inc_rule)

        # Addition: avoid simultaneous activations
        def dr_logical_constraint_rule(block):
            """Similar to equation 10 from Zerrahn and Schill (2015):
            The sum of upwards and downwards shifts may not be greater
            than the (bigger) capacity limit.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.addition:
                        # sum of load increases and reductions
                        lhs = (sum(self.dsm_up[g, h, t]
                                   + self.balance_dsm_do[g, h, t]
                                   + self.dsm_do_shift[g, h, t]
                                   + self.balance_dsm_up[g, h, t]
                                   for h in g.delay_time)
                               + self.dsm_do_shed[g, t])

                        # maximum capacity eligibly for load shifting
                        rhs = max(g.capacity_down[t] * g.max_capacity_down,
                                  g.capacity_up[t] * g.max_capacity_up)

                        # add constraint
                        block.dr_logical_constraint.add((g, t), (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_logical_constraint = Constraint(group, m.TIMESTEPS,
                                                noruleinit=True)
        self.dr_logical_constraint_build = BuildAction(
            rule=dr_logical_constraint_rule)

    # Equation 4.23
    def _objective_expression(self):
        r"""Objective expression with variable costs for DSM activity;
        Equation 4.23 from Gils (2015)
        """
        m = self.parent_block()

        dr_cost = 0

        for t in m.TIMESTEPS:
            for g in self.DR:
                dr_cost += (sum(self.dsm_up[g, h, t]
                                + self.balance_dsm_do[g, h, t]
                                for h in g.delay_time)
                            * g.cost_dsm_up[t] * m.objective_weighting[t])
                dr_cost += ((sum(self.dsm_do_shift[g, h, t]
                                 + self.balance_dsm_up[g, h, t]
                                 for h in g.delay_time)
                             * g.cost_dsm_down_shift[t]
                             + self.dsm_do_shed[g, t]
                             * g.cost_dsm_down_shed[t])
                            * m.objective_weighting[t])

        self.cost = Expression(expr=dr_cost)

        return self.cost


class SinkDSMDLRMultiPeriodBlock(SimpleBlock):
    r"""Constraints for SinkDSMDLRBlock

    **The following constraints are created:**

    .. _SinkDSM-equations:

    .. math::
        &
        (1) \quad \dot{E}_{t} = demand_{t} \cdot demand_{max} +
        \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDown} - DSM_{h, t}^{down} - DSM_{h, t}^{balanceUp}
        - DSM_{t}^{shed})
        \quad \forall t \in \mathbb{T} \\
        &
        (2) \quad DSM_{h, t}^{balanceDown} =
        \frac{DSM_{t-t_{shift}^h}^{down}}{\eta}
        \quad \forall t \in [t_{shift}^h..\mathbb{T}], h \in H_{DR} \\
        &
        (3) \quad DSM_{h, t}^{balanceUp} = DSM_{t-t_{shift}^h}^{up} \cdot \eta
        \quad \forall t \in [t_{shift}^{h}..\mathbb{T}], h \in H_{DR} \\
        &
        (4) \quad DSM_{h, t}^{down} = 0
        \quad \forall t \in [\mathbb{T} - t_{shift}^h..\mathbb{T}],
        h \in H_{DR}
        &
        (5) \quad DSM_{h, t}^{up} = 0
        \quad \forall t \in [\mathbb{T} - t_{shift}^h..\mathbb{T}],
        h \in H_{DR}
        &
        (6) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{down}
        + DSM_{h, t}^{balanceUp}) + DSM_{t}^{shed} \leq capacity_{t}^{down}
        \cdot capacity_{max}^{down}
        \quad \forall t \in \mathbb{T} \\
        &
        (7) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDown}) \leq capacity_{t}^{up}
        \cdot capacity_{max}^{up}
        \quad \forall t \in \mathbb{T} \\
        &
        (8) \quad \Delta t \cdot \displaystyle\sum_{h=1}^{H_{DR}}
        DSM_{h, t}^{down} - DSM_{h, t}^{balanceDown} \cdot \eta =
        W_{t}^{levelDown} - W_{t-1}^{levelDown} \quad
        \forall t \in [1..\mathbb{T}] \\
        &
        (9) \quad \Delta t \cdot \displaystyle\sum_{h=1}^{H_{DR}}
        DSM_{h, t}^{up} \cdot \eta - DSM_{h, t}^{balanceUp}  = W_{t}^{levelUp}
        - W_{t-1}^{levelUp} \quad \forall t \in [1..\mathbb{T}] \\
        &
        (10) \quad W_{t}^{levelDown} \leq \overline{capacity}_{t}^{down}
        \cdot capacity_{max}^{down}
        \cdot t_{interfere} \quad \forall t \in \mathbb{T} \\
        &
        (11) \quad W_{t}^{levelUp} \leq \overline{capacity}_{t}^{up}
        \cdot capacity_{max}^{up}
        \cdot t_{interfere} \quad \forall t \in \mathbb{T} \\
        &
        (12) \quad \displaystyle\sum_{t=0}^{T} \sum_{h=1}^{H_{DR}}
         DSM_{h, t}^{down} \leq capacity_{max}^{down}
        \cdot \overline{capacity}_{t}^{down} \cdot t_{interfere}
        \cdot n^{yearLimit} \\
        (optional \space constraint)
        &
        (13) \quad \displaystyle\sum_{t=0}^{T} \sum_{h=1}^{H_{DR}}
        DSM_{h, t}^{up} \leq capacity_{max}^{up}
        \cdot \overline{capacity}_{t}^{up} \cdot t_{interfere}
        \cdot n^{yearLimit} \\
        (optional \space constraint
        &
        (14) \quad \displaystyle\sum_{h=1}^{H_{DR}} DSM_{h, t}^{down}
        \leq capacity_{max}^{down} \cdot \overline{capacity}_{t}^{down}
        \cdot t_{interfere} -
        \displaystyle\sum_{t'=1}^{t_{dayLimit}}\sum_{h=1}^{H_{DR}}
        DSM_{h, t-t'}^{down}
        \quad \forall t \in [t-t_{dayLimit}..\mathbb{T}] \\
        (optional \space constraint)
        &
        (15) \quad \displaystyle\sum_{h=1}^{H_{DR}} DSM_{h, t}^{up}
        \leq capacity_{max}^{up} \cdot \overline{capacity}_{t}^{up}
        \cdot t_{interfere} -
        \displaystyle\sum_{t'=1}^{t_{dayLimit}}\sum_{h=1}^{H_{DR}}
        DSM_{h, t-t'}^{up}
        \quad \forall t \in [t-t_{dayLimit}..\mathbb{T}] \\
        (optional \space constraint)
        &
        (16) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDown}
        + DSM_{h, t}^{down} + DSM_{h, t}^{balanceUp})
        + DSM_{t}^{shed}
        \leq \max \{capacity_{t}^{up} \cdot capacity_{max}^{up},
        capacity_{t}^{down} \cdot capacity_{max}^{down} \}
        \quad \forall t \in \mathbb{T} \\ (optional \space constraint)
        &
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all DR components get inflow from bus_elec
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        # Set of DR Components
        self.MULTIPERIODDR = Set(initialize=[n for n in group])

        # Depict different delay_times per unit via a mapping
        map_MULTIPERIODDR_H = {
            k: v
            for k, v in zip([n for n in group],
                            [n.delay_time for n in group])
        }

        unique_H = list(set(itertools.chain.from_iterable(
            map_MULTIPERIODDR_H.values())))
        self.H = Set(initialize=unique_H)

        self.MULTIPERIODDR_H = Set(
            within=self.MULTIPERIODDR * self.H,
            initialize=[(dr, h)
                        for dr in map_MULTIPERIODDR_H
                        for h in map_MULTIPERIODDR_H[dr]])

        #  ************* VARIABLES *****************************

        # Variable load shift down (capacity)
        self.dsm_do_shift = Var(self.MULTIPERIODDR_H, m.TIMESTEPS,
                                initialize=0,
                                within=NonNegativeReals)

        # Variable for load shedding (capacity)
        self.dsm_do_shed = Var(self.MULTIPERIODDR, m.TIMESTEPS,
                               initialize=0,
                               within=NonNegativeReals)

        # Variable load shift up (capacity)
        self.dsm_up = Var(self.MULTIPERIODDR_H, m.TIMESTEPS,
                          initialize=0,
                          within=NonNegativeReals)

        # Variable balance load shift down through upwards shift (capacity)
        self.balance_dsm_do = Var(self.MULTIPERIODDR_H, m.TIMESTEPS,
                                  initialize=0,
                                  within=NonNegativeReals)

        # Variable balance load shift up through downwards shift (capacity)
        self.balance_dsm_up = Var(self.MULTIPERIODDR_H, m.TIMESTEPS,
                                  initialize=0,
                                  within=NonNegativeReals)

        # Variable fictious DR storage level for downwards load shifts (energy)
        self.dsm_do_level = Var(self.MULTIPERIODDR, m.TIMESTEPS,
                                initialize=0,
                                within=NonNegativeReals)

        # Variable fictious DR storage level for upwards load shifts (energy)
        self.dsm_up_level = Var(self.MULTIPERIODDR, m.TIMESTEPS,
                                initialize=0,
                                within=NonNegativeReals)

        #  ************* CONSTRAINTS *****************************

        def _shift_shed_vars_rule(block):
            """Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if not g.shift_eligibility:
                            lhs = self.dsm_up[g, h, t]
                            rhs = 0

                            block.shift_shed_vars.add((g, h, t), (lhs == rhs))

                        if not g.shed_eligibility:
                            lhs = self.dsm_do_shed[g, t]
                            rhs = 0

                            block.shift_shed_vars.add((g, h, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, self.H, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Relation between inflow and effective Sink consumption
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DR.
            Bus outflow == Demand +- DR (i.e. effective Sink consumption)
            """
            for p, t in m.TIMEINDEX:

                for g in group:
                    # outflow from bus
                    lhs = m.flow[g.inflow, g, p, t]

                    # Demand +- DR
                    rhs = (g.demand[t] * g.max_demand +
                           + sum(self.dsm_up[g, h, t]
                                 + self.balance_dsm_do[g, h, t]
                                 - self.dsm_do_shift[g, h, t]
                                 - self.balance_dsm_up[g, h, t]
                                 for h in g.delay_time)
                           - self.dsm_do_shed[g, t])

                    # add constraint
                    block.input_output_relation.add((g, p, t), (lhs == rhs))

        self.input_output_relation = Constraint(group, m.TIMEINDEX,
                                                noruleinit=True)
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule)

        # Equation 4.8
        def capacity_balance_red_rule(block):
            """Load reduction must be balanced by load increase
            within delay_time
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if g.shift_eligibility:

                            # main use case
                            if t >= h:
                                # balance load reduction
                                lhs = self.balance_dsm_do[g, h, t]

                                # load reduction (efficiency considered)
                                rhs = (self.dsm_do_shift[g, h, t - h]
                                       / g.efficiency)

                                # add constraint
                                block.capacity_balance_red.add((g, h, t),
                                                               (lhs == rhs))

                            # no balancing for the first timestep
                            elif t == m.TIMESTEPS[1]:
                                lhs = self.balance_dsm_do[g, h, t]
                                rhs = 0

                                block.capacity_balance_red.add((g, h, t),
                                                               (lhs == rhs))

                            else:
                                pass  # return(Constraint.Skip)

                        # if only shedding is possible, balancing variable is 0
                        else:
                            lhs = self.balance_dsm_do[g, h, t]
                            rhs = 0

                            block.capacity_balance_red.add((g, h, t),
                                                           (lhs == rhs))

        self.capacity_balance_red = Constraint(group, self.H, m.TIMESTEPS,
                                               noruleinit=True)
        self.capacity_balance_red_build = BuildAction(
            rule=capacity_balance_red_rule)

        # Equation 4.9
        def capacity_balance_inc_rule(block):
            """Load increased must be balanced by load reduction
            within delay_time
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if g.shift_eligibility:

                            # main use case
                            if t >= h:
                                # balance load increase
                                lhs = self.balance_dsm_up[g, h, t]

                                # load increase (efficiency considered)
                                rhs = self.dsm_up[g, h, t - h] * g.efficiency

                                # add constraint
                                block.capacity_balance_inc.add((g, h, t),
                                                               (lhs == rhs))

                            # no balancing for the first timestep
                            elif t == m.TIMESTEPS[1]:
                                lhs = self.balance_dsm_up[g, h, t]
                                rhs = 0

                                block.capacity_balance_inc.add((g, h, t),
                                                               (lhs == rhs))

                            else:
                                pass  # return(Constraint.Skip)

                        # if only shedding is possible, balancing variable is 0
                        else:
                            lhs = self.balance_dsm_up[g, h, t]
                            rhs = 0

                            block.capacity_balance_inc.add((g, h, t),
                                                           (lhs == rhs))

        self.capacity_balance_inc = Constraint(group, self.H, m.TIMESTEPS,
                                               noruleinit=True)
        self.capacity_balance_inc_build = BuildAction(
            rule=capacity_balance_inc_rule)

        # Fix: prevent shifts which cannot be compensated
        def no_comp_red_rule(block):
            """Prevent downwards shifts that cannot be balanced anymore
            within the optimization timeframe
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.fixes:
                        for h in g.delay_time:

                            if t > m.TIMESTEPS[-1] - h:
                                # no load reduction anymore (dsm_do_shift = 0)
                                lhs = self.dsm_do_shift[g, h, t]
                                rhs = 0
                                block.no_comp_red.add((g, h, t), (lhs == rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.no_comp_red = Constraint(group, self.H, m.TIMESTEPS,
                                      noruleinit=True)
        self.no_comp_red_build = BuildAction(
            rule=no_comp_red_rule)

        # Fix: prevent shifts which cannot be compensated
        def no_comp_inc_rule(block):
            """Prevent upwards shifts that cannot be balanced anymore
            within the optimization timeframe
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.fixes:
                        for h in g.delay_time:

                            if t > m.TIMESTEPS[-1] - h:
                                # no load increase anymore (dsm_up = 0)
                                lhs = self.dsm_up[g, h, t]
                                rhs = 0
                                block.no_comp_inc.add((g, h, t), (lhs == rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.no_comp_inc = Constraint(group, self.H, m.TIMESTEPS,
                                      noruleinit=True)
        self.no_comp_inc_build = BuildAction(
            rule=no_comp_inc_rule)

        # Equation 4.11
        def availability_red_rule(block):
            """Load reduction must be smaller than or equal to the
            (time-dependent) capacity limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # load reduction
                    lhs = (sum(self.dsm_do_shift[g, h, t]
                               + self.balance_dsm_up[g, h, t]
                               for h in g.delay_time)
                           + self.dsm_do_shed[g, t])

                    # upper bound
                    rhs = g.capacity_down[t] * g.max_capacity_down

                    # add constraint
                    block.availability_red.add((g, t), (lhs <= rhs))

        self.availability_red = Constraint(group, m.TIMESTEPS,
                                           noruleinit=True)
        self.availability_red_build = BuildAction(
            rule=availability_red_rule)

        # Equation 4.12
        def availability_inc_rule(block):
            """Load increase must be smaller than or equal to the
            (time-dependent) capacity limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # load increase
                    lhs = sum(self.dsm_up[g, h, t]
                              + self.balance_dsm_do[g, h, t]
                              for h in g.delay_time)

                    # upper bound
                    rhs = g.capacity_up[t] * g.max_capacity_up

                    # add constraint
                    block.availability_inc.add((g, t), (lhs <= rhs))

        self.availability_inc = Constraint(group, m.TIMESTEPS,
                                           noruleinit=True)
        self.availability_inc_build = BuildAction(
            rule=availability_inc_rule)

        # Equation 4.13
        def dr_storage_red_rule(block):
            """Fictious demand response storage level for load reductions
            transition equation
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # avoid timesteps prior to t = 0
                    if t > 0:
                        # reduction minus balancing of reductions
                        lhs = (m.timeincrement[t]
                               * sum((self.dsm_do_shift[g, h, t]
                                      - self.balance_dsm_do[g, h, t]
                                      * g.efficiency)
                                     for h in g.delay_time))

                        # load reduction storage level transition
                        rhs = (self.dsm_do_level[g, t]
                               - self.dsm_do_level[g, t - 1])

                        # add constraint
                        block.dr_storage_red.add((g, t), (lhs == rhs))

                    else:
                        lhs = self.dsm_do_level[g, t]
                        rhs = (m.timeincrement[t]
                               * sum(self.dsm_do_shift[g, h, t]
                                     for h in g.delay_time))
                        block.dr_storage_red.add((g, t), (lhs == rhs))

        self.dr_storage_red = Constraint(group, m.TIMESTEPS,
                                         noruleinit=True)
        self.dr_storage_red_build = BuildAction(
            rule=dr_storage_red_rule)

        # Equation 4.14
        def dr_storage_inc_rule(block):
            """Fictious demand response storage level for load increase
            transition equation
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # avoid timesteps prior to t = 0
                    if t > 0:
                        # increases minus balancing of reductions
                        lhs = (m.timeincrement[t]
                               * sum((self.dsm_up[g, h, t]
                                      * g.efficiency
                                      - self.balance_dsm_up[g, h, t])
                                     for h in g.delay_time))

                        # load increase storage level transition
                        rhs = (self.dsm_up_level[g, t]
                               - self.dsm_up_level[g, t - 1])

                        # add constraint
                        block.dr_storage_inc.add((g, t), (lhs == rhs))

                    else:
                        # pass  # return(Constraint.Skip)
                        lhs = self.dsm_up_level[g, t]
                        rhs = (m.timeincrement[t]
                               * sum(self.dsm_up[g, h, t]
                                     for h in g.delay_time))
                        block.dr_storage_inc.add((g, t), (lhs == rhs))

        self.dr_storage_inc = Constraint(group, m.TIMESTEPS,
                                         noruleinit=True)
        self.dr_storage_inc_build = BuildAction(
            rule=dr_storage_inc_rule)

        # Equation 4.15
        def dr_storage_limit_red_rule(block):
            """Fictious demand response storage level for load reduction limit
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.shift_eligibility:
                        # fictious demand response load reduction storage level
                        lhs = self.dsm_do_level[g, t]

                        # maximum (time-dependent) available shifting capacity
                        rhs = (g.capacity_down_mean * g.max_capacity_down
                               * g.shift_time)

                        # add constraint
                        block.dr_storage_limit_red.add((g, t), (lhs <= rhs))

                    else:
                        lhs = self.dsm_do_level[g, t]
                        # Force storage level and thus dsm_do_shift to 0
                        rhs = 0

                        # add constraint
                        block.dr_storage_limit_red.add((g, t), (lhs <= rhs))

        self.dr_storage_limit_red = Constraint(group, m.TIMESTEPS,
                                               noruleinit=True)
        self.dr_storage_level_red_build = BuildAction(
            rule=dr_storage_limit_red_rule)

        # Equation 4.16
        def dr_storage_limit_inc_rule(block):
            """Fictious demand response storage level for load increase limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # fictious demand response load reduction storage level
                    lhs = self.dsm_up_level[g, t]

                    # maximum (time-dependent) available shifting capacity
                    rhs = (g.capacity_up_mean * g.max_capacity_up
                           * g.shift_time)

                    # add constraint
                    block.dr_storage_limit_inc.add((g, t), (lhs <= rhs))

        self.dr_storage_limit_inc = Constraint(group, m.TIMESTEPS,
                                               noruleinit=True)
        self.dr_storage_level_inc_build = BuildAction(
            rule=dr_storage_limit_inc_rule)

        # Equation 4.17' -> load shedding
        def dr_yearly_limit_shed_rule(block):
            """Introduce overall annual (energy) limit for load shedding resp.
            overall limit for optimization timeframe considered
            A year limit in contrast to Gils (2015) is defined a mandatory
            parameter here in order to achieve an approach comparable
            to the others.
            """
            for g in group:

                if g.shed_eligibility:
                    # sum of all load reductions
                    lhs = sum(self.dsm_do_shed[g, t]
                              for t in m.TIMESTEPS)

                    # year limit
                    rhs = (g.capacity_down_mean * g.max_capacity_down
                           * g.shed_time * g.n_yearLimit_shed)

                    # add constraint
                    block.dr_yearly_limit_shed.add(g, (lhs <= rhs))

                else:
                    pass  # return(Constraint.Skip)

        self.dr_yearly_limit_shed = Constraint(group, noruleinit=True)
        self.dr_yearly_limit_shed_build = BuildAction(
            rule=dr_yearly_limit_shed_rule)

        # ************* Optional Constraints *****************************

        # Equation 4.17
        def dr_yearly_limit_red_rule(block):
            """Introduce overall annual (energy) limit for load reductions
            resp. overall limit for optimization timeframe considered
            """
            for g in group:

                if g.ActivateYearLimit:
                    # sum of all load reductions
                    lhs = sum(sum(self.dsm_do_shift[g, h, t]
                                  for h in g.delay_time)
                              for t in m.TIMESTEPS)

                    # year limit
                    rhs = (g.capacity_down_mean * g.max_capacity_down
                           * g.shift_time * g.n_yearLimit_shift)

                    # add constraint
                    block.dr_yearly_limit_red.add(g, (lhs <= rhs))

                else:
                    pass  # return(Constraint.Skip)

        self.dr_yearly_limit_red = Constraint(group, noruleinit=True)
        self.dr_yearly_limit_red_build = BuildAction(
            rule=dr_yearly_limit_red_rule)

        # Equation 4.18
        def dr_yearly_limit_inc_rule(block):
            """Introduce overall annual (energy) limit for load increases
            resp. overall limit for optimization timeframe considered
            """
            for g in group:

                if g.ActivateYearLimit:
                    # sum of all load increases
                    lhs = sum(sum(self.dsm_up[g, h, t]
                                  for h in g.delay_time)
                              for t in m.TIMESTEPS)

                    # year limit
                    rhs = (g.capacity_up_mean * g.max_capacity_up
                           * g.shift_time * g.n_yearLimit_shift)

                    # add constraint
                    block.dr_yearly_limit_inc.add(g, (lhs <= rhs))

                else:
                    pass  # return(Constraint.Skip)

        self.dr_yearly_limit_inc = Constraint(group, noruleinit=True)
        self.dr_yearly_limit_inc_build = BuildAction(
            rule=dr_yearly_limit_inc_rule)

        # Equation 4.19
        def dr_daily_limit_red_rule(block):
            """Introduce rolling (energy) limit for load reductions
            This effectively limits DR utilization dependent on
            activations within previous hours.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.ActivateDayLimit:
                        # main use case
                        if t >= g.t_dayLimit:

                            # load reduction
                            lhs = sum(self.dsm_do_shift[g, h, t]
                                      for h in g.delay_time)

                            # daily limit
                            rhs = (
                                g.capacity_down_mean * g.max_capacity_down
                                * g.shift_time
                                - sum(sum(self.dsm_do_shift[g, h, t - t_dash]
                                          for h in g.delay_time)
                                      for t_dash
                                      in range(1, int(g.t_dayLimit) + 1))
                            )

                            # add constraint
                            block.dr_daily_limit_red.add((g, t), (lhs <= rhs))

                        else:
                            pass  # return(Constraint.Skip)

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_daily_limit_red = Constraint(group, m.TIMESTEPS,
                                             noruleinit=True)
        self.dr_daily_limit_red_build = BuildAction(
            rule=dr_daily_limit_red_rule)

        # Equation 4.20
        def dr_daily_limit_inc_rule(block):
            """Introduce rolling (energy) limit for load increases
            This effectively limits DR utilization dependent on
            activations within previous hours.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.ActivateDayLimit:
                        # main use case
                        if t >= g.t_dayLimit:

                            # load increase
                            lhs = sum(self.dsm_up[g, h, t]
                                      for h in g.delay_time)

                            # daily limit
                            rhs = (
                                g.capacity_up_mean * g.max_capacity_up
                                * g.shift_time
                                - sum(sum(self.dsm_up[g, h, t - t_dash]
                                          for h in g.delay_time)
                                      for t_dash
                                      in range(1, int(g.t_dayLimit) + 1))
                            )

                            # add constraint
                            block.dr_daily_limit_inc.add((g, t), (lhs <= rhs))

                        else:
                            pass  # return(Constraint.Skip)

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_daily_limit_inc = Constraint(group, m.TIMESTEPS,
                                             noruleinit=True)
        self.dr_daily_limit_inc_build = BuildAction(
            rule=dr_daily_limit_inc_rule)

        # Own addition (optional)
        def dr_logical_constraint_rule(block):
            """Similar to equation 10 from Zerrahn and Schill (2015):
            The sum of upwards and downwards shifts may not be greater
            than the (bigger) capacity limit.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.addition:
                        # sum of load increases and reductions
                        lhs = (sum(self.dsm_up[g, h, t]
                                   + self.balance_dsm_do[g, h, t]
                                   + self.dsm_do_shift[g, h, t]
                                   + self.balance_dsm_up[g, h, t]
                                   for h in g.delay_time)
                               + self.dsm_do_shed[g, t])

                        # maximum capacity eligibly for load shifting
                        rhs = max(g.capacity_down[t] * g.max_capacity_down,
                                  g.capacity_up[t] * g.max_capacity_up)

                        # add constraint
                        block.dr_logical_constraint.add((g, t), (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_logical_constraint = Constraint(group, m.TIMESTEPS,
                                                noruleinit=True)
        self.dr_logical_constraint_build = BuildAction(
            rule=dr_logical_constraint_rule)

    # Equation 4.23
    def _objective_expression(self):
        r""" Objective expression for all DR shift units with fixed costs
        and variable costs; Equation 4.23 from Gils (2015)
        """
        m = self.parent_block()

        variable_costs = 0
        fixed_costs = 0

        for g in self.MULTIPERIODDR:
            for p, t in m.TIMEINDEX:
                variable_costs += ((sum(self.dsm_up[g, h, t]
                                        + self.balance_dsm_do[g, h, t]
                                        for h in g.delay_time)
                                    * g.cost_dsm_up[p])
                                   * m.objective_weighting[t]
                                   * ((1 + m.discount_rate) ** -p))
                variable_costs += ((sum(self.dsm_do_shift[g, h, t]
                                        + self.balance_dsm_up[g, h, t]
                                        for h in g.delay_time)
                                    * g.cost_dsm_down_shift[p]
                                    + self.dsm_do_shed[g, t]
                                    * g.cost_dsm_down_shed[p])
                                   * m.objective_weighting[t]
                                   * ((1 + m.discount_rate) ** -p))

            if g.fixed_costs[0] is not None:
                for p in m.PERIODS:
                    fixed_costs += (
                        g.max_demand
                        * g.fixed_costs[p]
                        * ((1 + m.discount_rate) ** (-p))
                    )

        self.cost = Expression(expr=variable_costs + fixed_costs)

        return self.cost


class SinkDSMDLRInvestmentBlock(SinkDSMDLRBlock):
    r"""Constraints for SinkDSM with "DLR" approach and :attr:`investment`

    **The following constraints are created for approach = 'DLR' with an
    investment object defined:**

    .. _SinkDSMDLR equations:

    .. math::
        &
        (1) \quad invest_{min} \leq invest \leq invest_{max} \\
        &
        (2) \quad DSM_{h, t}^{up} = 0 \quad \forall h \in H_{DR}
        \forall t \in \mathbb{T}
        \quad if \space eligibility_{shift} = False \\
        &
        (3) \quad DSM_{t}^{do, shed} = 0 \quad \forall t \in \mathbb{T}
        \quad if \space eligibility_{shed} = False \\
        &
        (4) \quad \dot{E}_{t} = demand_{t} \cdot (invest + E_{exist})
        + \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDo} - DSM_{h, t}^{do, shift}
        - DSM_{h, t}^{balanceUp}) - DSM_{t}^{do, shed}
        \quad \forall t \in \mathbb{T} \\
        &
        (5) \quad DSM_{h, t}^{balanceDo} =
        \frac{DSM_{h, t - h}^{do, shift}}{\eta}
        \quad \forall h \in H_{DR} \forall t \in [h..T] \\
        &
        (6) \quad DSM_{h, t}^{balanceUp} =
        DSM_{h, t-h}^{up} \cdot \eta
        \quad \forall h \in H_{DR} \forall t \in [h..T] \\
        &
        (7) \quad DSM_{h, t}^{do, shift} = 0
        \quad \forall h \in H_{DR}
        \forall t \in [T - h..T] \\
        &
        (8) \quad DSM_{h, t}^{up} = 0
        \quad \forall h \in H_{DR}
        \forall t \in [T - h..T] \\
        &
        (9) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{do, shift}
        + DSM_{h, t}^{balanceUp}) + DSM_{t}^{do, shed}
        \leq E_{t}^{do} \cdot (invest + E_{exist})
        \cdot s_{flex, do}
        \quad \forall t \in \mathbb{T} \\
        &
        (10) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDo})
        \leq E_{t}^{up} \cdot (invest + E_{exist})
        \cdot s_{flex, up}
        \quad \forall t \in \mathbb{T} \\
        &
        (11) \quad \Delta t \cdot \displaystyle\sum_{h=1}^{H_{DR}}
        (DSM_{h, t}^{do, shift} - DSM_{h, t}^{balanceDo} \cdot \eta)
        = W_{t}^{levelDo} - W_{t-1}^{levelDo}
        \quad \forall t \in [1..T] \\
        &
        (12) \quad \Delta t \cdot \displaystyle\sum_{h=1}^{H_{DR}}
        (DSM_{h, t}^{up} \cdot \eta - DSM_{h, t}^{balanceUp})
        = W_{t}^{levelUp} - W_{t-1}^{levelUp}
        \quad \forall t \in [1..T] \\
        &
        (13) \quad W_{t}^{levelDo} \leq \overline{E}_{t}^{do}
        \cdot (invest + E_{exist})
        \cdot s_{flex, do} \cdot t_{shift}
        \quad \forall t \in \mathbb{T} \\
        &
        (14) \quad W_{t}^{levelUp} \leq \overline{E}_{t}^{up}
        \cdot (invest + E_{exist})
        \cdot s_{flex, up} \cdot t_{shift}
        \quad \forall t \in \mathbb{T} \\
        &
        (15) \quad \displaystyle\sum_{t=0}^{T} DSM_{t}^{do, shed}
        \leq (invest + E_{exist})
        \cdot s_{flex, do} \cdot \overline{E}_{t}^{do}
        \cdot t_{shed}
        \cdot n^{yearLimitShed} \\
        &
        (16) \quad \displaystyle\sum_{t=0}^{T} \sum_{h=1}^{H_{DR}}
        DSM_{h, t}^{do, shift}
        \leq (invest + E_{exist})
        \cdot s_{flex, do} \cdot \overline{E}_{t}^{do}
        \cdot t_{shift}
        \cdot n^{yearLimitShift} \\
        (optional \space constraint) \\
        &
        (17) \quad \displaystyle\sum_{t=0}^{T} \sum_{h=1}^{H_{DR}}
        DSM_{h, t}^{up}
        \leq (invest + E_{exist})
        \cdot s_{flex, up} \cdot \overline{E}_{t}^{up}
        \cdot t_{shift}
        \cdot n^{yearLimitShift} \\
        (optional \space constraint) \\
        &
        (18) \quad \displaystyle\sum_{h=1}^{H_{DR}} DSM_{h, t}^{do, shift}
        \leq (invest + E_{exist})
        \cdot s_{flex, do} \cdot \overline{E}_{t}^{do}
        \cdot t_{shift} -
        \displaystyle\sum_{t'=1}^{t_{dayLimit}} \sum_{h=1}^{H_{DR}}
        DSM_{h, t - t'}^{do, shift}
        \quad \forall t \in [t-t_{dayLimit}..T] \\
        (optional \space constraint) \\
        &
        (19) \quad \displaystyle\sum_{h=1}^{H_{DR}} DSM_{h, t}^{up}
        \leq (invest + E_{exist})
        \cdot s_{flex, up} \cdot \overline{E}_{t}^{up}
        \cdot t_{shift} -
        \displaystyle\sum_{t'=1}^{t_{dayLimit}} \sum_{h=1}^{H_{DR}}
        DSM_{h, t - t'}^{up}
        \quad \forall t \in [t-t_{dayLimit}..T] \\
        (optional \space constraint) \\
        &
        (20) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDo}
        + DSM_{h, t}^{do, shift} + DSM_{h, t}^{balanceUp})
        + DSM_{t}^{shed}
        \leq \max \{E_{t}^{up} \cdot s_{flex, up},
        E_{t}^{do} \cdot s_{flex, do} \} \cdot (invest + E_{exist})
        \quad \forall t \in \mathbb{T} \\
        (optional \space constraint) \\
        &

    *Note*: For the sake of readability, the handling of indices is not
    displayed here. E.g. evaluating a variable for t-L may lead to a negative
    and therefore infeasible index.
    This is addressed by limiting the sums to non-negative indices within the
    model index bounds. Please refer to the constraints implementation
    themselves.

    **The following parts of the objective function are created:**

    * Investment annuity:

    .. math::
        invest \cdot costs_{invest} \\

    * Variable costs:

    .. math::
        \sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up} + DSM_{h, t}^{balanceDo})
        \cdot cost_{t}^{dsm, up}
        + \sum_{h=1}^{H_{DR}} (DSM_{h, t}^{do, shift} + DSM_{h, t}^{balanceUp})
        \cdot cost_{t}^{dsm, do, shift}
        + DSM_{t}^{do, shed} \cdot cost_{t}^{dsm, do, shed}
        \quad \forall t \in \mathbb{T} \\

    **Table: Symbols and attribute names of variables and parameters**

    Please refer to :class:`oemof.solph.custom.SinkDSMDLRBlock`.

    The following variables and parameters are exclusively used for
    investment modeling:

        .. csv-table:: Variables (V) and Parameters (P)
            :header: "symbol", "attribute", "type", "explanation"
            :widths: 1, 1, 1, 1

            ":math:`invest` ",":attr:`~SinkDSM.invest` ","V", "DSM capacity
            invested in. Equals to the additionally installed capacity.
            The capacity share eligible for a shift is determined
            by flex share(s)."
            ":math:`invest_{min}` ", ":attr:`~SinkDSM.investment.minimum` ",
            "P", "minimum investment"
            ":math:`invest_{max}` ", ":attr:`~SinkDSM.investment.maximum` ",
            "P", "maximum investment"
            ":math:`E_{exist}` ",":attr:`~SinkDSM.investment.existing` ",
            "P", "existing DSM capacity"
            ":math:`s_{flex, up}` ",":attr:`~SinkDSM.flex_share_up` ",
            "P","Share of invested capacity that may be shift upwards
            at maximum"
            ":math:`s_{flex, do}` ",":attr:`~SinkDSM.flex_share_do` ",
            "P", "Share of invested capacity that may be shift downwards
            at maximum"
            ":math:`costs_{invest}` ",":attr:`~SinkDSM.investment.ep_costs` ",
            "P", "specific investment annuity"
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):

        if group is None:
            return None

        m = self.parent_block()

        # for all DSM components get inflow from a bus
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        self.INVESTDR = Set(initialize=[n for n in group])

        # Depict different delay_times per unit via a mapping
        map_INVESTDR_H = {
            k: v for k, v in zip([n for n in group],
                                 [n.delay_time for n in group])
        }

        unique_H = list(
            set(itertools.chain.from_iterable(
                map_INVESTDR_H.values()))
        )
        self.H = Set(initialize=unique_H)

        self.INVESTDR_H = Set(within=self.INVESTDR * self.H,
                              initialize=[(dr, h)
                                          for dr in map_INVESTDR_H
                                          for h in map_INVESTDR_H[dr]])

        #  ************* VARIABLES *****************************

        # Define bounds for investments in demand response
        def _dr_investvar_bound_rule(block, g):
            """Rule definition to bound the
            invested demand response capacity `invest`.
            """
            return g.investment.minimum, g.investment.maximum

        # Investment in DR capacity
        self.invest = Var(self.INVESTDR,
                          within=NonNegativeReals,
                          bounds=_dr_investvar_bound_rule)

        # Variable load shift down (capacity)
        self.dsm_do_shift = Var(self.INVESTDR_H, m.TIMESTEPS, initialize=0,
                                within=NonNegativeReals)

        # Variable for load shedding (capacity)
        self.dsm_do_shed = Var(self.INVESTDR, m.TIMESTEPS, initialize=0,
                               within=NonNegativeReals)

        # Variable load shift up (capacity)
        self.dsm_up = Var(self.INVESTDR_H, m.TIMESTEPS, initialize=0,
                          within=NonNegativeReals)

        # Variable balance load shift down through upwards shift (capacity)
        self.balance_dsm_do = Var(self.INVESTDR_H, m.TIMESTEPS, initialize=0,
                                  within=NonNegativeReals)

        # Variable balance load shift up through downwards shift (capacity)
        self.balance_dsm_up = Var(self.INVESTDR_H, m.TIMESTEPS, initialize=0,
                                  within=NonNegativeReals)

        # Variable fictious DR storage level for downwards load shifts (energy)
        self.dsm_do_level = Var(self.INVESTDR, m.TIMESTEPS, initialize=0,
                                within=NonNegativeReals)

        # Variable fictious DR storage level for upwards load shifts (energy)
        self.dsm_up_level = Var(self.INVESTDR, m.TIMESTEPS, initialize=0,
                                within=NonNegativeReals)

        #  ************* CONSTRAINTS *****************************

        def _shift_shed_vars_rule(block):
            """Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if not g.shift_eligibility:
                            lhs = self.dsm_up[g, h, t]
                            rhs = 0

                            block.shift_shed_vars.add((g, h, t), (lhs == rhs))

                        if not g.shed_eligibility:
                            lhs = self.dsm_do_shed[g, t]
                            rhs = 0

                            block.shift_shed_vars.add((g, h, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, self.H, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Relation between inflow and effective Sink consumption
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DR.
            Bus outflow == Demand +- DR (i.e. effective Sink consumption)
            """
            for t in m.TIMESTEPS:

                for g in group:
                    # outflow from bus
                    lhs = m.flow[g.inflow, g, t]

                    # Demand +- DR
                    rhs = (g.demand[t]
                           * (self.invest[g] + g.investment.existing)
                           + sum(self.dsm_up[g, h, t]
                                 + self.balance_dsm_do[g, h, t]
                                 - self.dsm_do_shift[g, h, t]
                                 - self.balance_dsm_up[g, h, t]
                                 for h in g.delay_time)
                           - self.dsm_do_shed[g, t])

                    # add constraint
                    block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation = Constraint(group, m.TIMESTEPS,
                                                noruleinit=True)
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule)

        # Equation 4.8
        def capacity_balance_red_rule(block):
            """Load reduction must be balanced by load increase
            within delay_time
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if g.shift_eligibility:

                            # main use case
                            if t >= h:
                                # balance load reduction
                                lhs = self.balance_dsm_do[g, h, t]

                                # load reduction (efficiency considered)
                                rhs = (self.dsm_do_shift[g, h, t - h]
                                       / g.efficiency)

                                # add constraint
                                block.capacity_balance_red.add((g, h, t),
                                                               (lhs == rhs))

                            # no balancing for the first timestep
                            elif t == m.TIMESTEPS[1]:
                                lhs = self.balance_dsm_do[g, h, t]
                                rhs = 0

                                block.capacity_balance_red.add((g, h, t),
                                                               (lhs == rhs))

                            else:
                                pass  # return(Constraint.Skip)

                        # if only shedding is possible, balancing variable is 0
                        else:
                            lhs = self.balance_dsm_do[g, h, t]
                            rhs = 0

                            block.capacity_balance_red.add((g, h, t),
                                                           (lhs == rhs))

        self.capacity_balance_red = Constraint(group, self.H, m.TIMESTEPS,
                                               noruleinit=True)
        self.capacity_balance_red_build = BuildAction(
            rule=capacity_balance_red_rule)

        # Equation 4.9
        def capacity_balance_inc_rule(block):
            """Load increased must be balanced by load reduction
            within delay_time
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if g.shift_eligibility:

                            # main use case
                            if t >= h:
                                # balance load increase
                                lhs = self.balance_dsm_up[g, h, t]

                                # load increase (efficiency considered)
                                rhs = self.dsm_up[g, h, t - h] * g.efficiency

                                # add constraint
                                block.capacity_balance_inc.add((g, h, t),
                                                               (lhs == rhs))

                            # no balancing for the first timestep
                            elif t == m.TIMESTEPS[1]:
                                lhs = self.balance_dsm_up[g, h, t]
                                rhs = 0

                                block.capacity_balance_inc.add((g, h, t),
                                                               (lhs == rhs))

                            else:
                                pass  # return(Constraint.Skip)

                        # if only shedding is possible, balancing variable is 0
                        else:
                            lhs = self.balance_dsm_up[g, h, t]
                            rhs = 0

                            block.capacity_balance_inc.add((g, h, t),
                                                           (lhs == rhs))

        self.capacity_balance_inc = Constraint(group, self.H, m.TIMESTEPS,
                                               noruleinit=True)
        self.capacity_balance_inc_build = BuildAction(
            rule=capacity_balance_inc_rule)

        # Own addition: prevent shifts which cannot be compensated
        def no_comp_red_rule(block):
            """Prevent downwards shifts that cannot be balanced anymore
            within the optimization timeframe
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.fixes:
                        for h in g.delay_time:

                            if t > m.TIMESTEPS[-1] - h:
                                # no load reduction anymore (dsm_do_shift = 0)
                                lhs = self.dsm_do_shift[g, h, t]
                                rhs = 0
                                block.no_comp_red.add((g, h, t), (lhs == rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.no_comp_red = Constraint(group, self.H, m.TIMESTEPS,
                                      noruleinit=True)
        self.no_comp_red_build = BuildAction(
            rule=no_comp_red_rule)

        # Own addition: prevent shifts which cannot be compensated
        def no_comp_inc_rule(block):
            """Prevent upwards shifts that cannot be balanced anymore
            within the optimization timeframe
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.fixes:
                        for h in g.delay_time:

                            if t > m.TIMESTEPS[-1] - h:
                                # no load increase anymore (dsm_up = 0)
                                lhs = self.dsm_up[g, h, t]
                                rhs = 0
                                block.no_comp_inc.add((g, h, t), (lhs == rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.no_comp_inc = Constraint(group, self.H, m.TIMESTEPS,
                                      noruleinit=True)
        self.no_comp_inc_build = BuildAction(
            rule=no_comp_inc_rule)

        # Equation 4.11
        def availability_red_rule(block):
            """Load reduction must be smaller than or equal to the
            (time-dependent) capacity limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # load reduction
                    lhs = (sum(self.dsm_do_shift[g, h, t]
                               + self.balance_dsm_up[g, h, t]
                               for h in g.delay_time)
                           + self.dsm_do_shed[g, t])

                    # upper bound
                    rhs = (g.capacity_down[t]
                           * (self.invest[g] + g.investment.existing)
                           * g.flex_share_down)

                    # add constraint
                    block.availability_red.add((g, t), (lhs <= rhs))

        self.availability_red = Constraint(group, m.TIMESTEPS,
                                           noruleinit=True)
        self.availability_red_build = BuildAction(
            rule=availability_red_rule)

        # Equation 4.12
        def availability_inc_rule(block):
            """Load increase must be smaller than or equal to the
            (time-dependent) capacity limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # load increase
                    lhs = sum(self.dsm_up[g, h, t]
                              + self.balance_dsm_do[g, h, t]
                              for h in g.delay_time)

                    # upper bound
                    rhs = (g.capacity_up[t]
                           * (self.invest[g] + g.investment.existing)
                           * g.flex_share_up)

                    # add constraint
                    block.availability_inc.add((g, t), (lhs <= rhs))

        self.availability_inc = Constraint(group, m.TIMESTEPS,
                                           noruleinit=True)
        self.availability_inc_build = BuildAction(
            rule=availability_inc_rule)

        # Equation 4.13
        def dr_storage_red_rule(block):
            """Fictious demand response storage level for load reductions
            transition equation
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # avoid timesteps prior to t = 0
                    if t > 0:
                        # reduction minus balancing of reductions
                        lhs = (m.timeincrement[t]
                               * sum((self.dsm_do_shift[g, h, t]
                                      - self.balance_dsm_do[g, h, t]
                                      * g.efficiency)
                                     for h in g.delay_time))

                        # load reduction storage level transition
                        rhs = (self.dsm_do_level[g, t]
                               - self.dsm_do_level[g, t - 1])

                        # add constraint
                        block.dr_storage_red.add((g, t), (lhs == rhs))

                    else:
                        # pass  # return(Constraint.Skip)
                        lhs = self.dsm_do_level[g, t]
                        rhs = (m.timeincrement[t]
                               * sum(self.dsm_do_shift[g, h, t]
                                     for h in g.delay_time))
                        block.dr_storage_red.add((g, t), (lhs == rhs))

        self.dr_storage_red = Constraint(group, m.TIMESTEPS,
                                         noruleinit=True)
        self.dr_storage_red_build = BuildAction(
            rule=dr_storage_red_rule)

        # Equation 4.14
        def dr_storage_inc_rule(block):
            """Fictious demand response storage level for load increase
            transition equation
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # avoid timesteps prior to t = 0
                    if t > 0:
                        # increases minus balancing of reductions
                        lhs = (m.timeincrement[t]
                               * sum((self.dsm_up[g, h, t]
                                      * g.efficiency
                                      - self.balance_dsm_up[g, h, t])
                                     for h in g.delay_time))

                        # load increase storage level transition
                        rhs = (self.dsm_up_level[g, t]
                               - self.dsm_up_level[g, t - 1])

                        # add constraint
                        block.dr_storage_inc.add((g, t), (lhs == rhs))

                    else:
                        # pass  # return(Constraint.Skip)
                        lhs = self.dsm_up_level[g, t]
                        rhs = m.timeincrement[t] * sum(self.dsm_up[g, h, t]
                                                       for h in g.delay_time)
                        block.dr_storage_inc.add((g, t), (lhs == rhs))

        self.dr_storage_inc = Constraint(group, m.TIMESTEPS,
                                         noruleinit=True)
        self.dr_storage_inc_build = BuildAction(
            rule=dr_storage_inc_rule)

        # Equation 4.15
        def dr_storage_limit_red_rule(block):
            """Fictious demand response storage level for load reduction limit
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.shift_eligibility:
                        # fictious demand response load reduction storage level
                        lhs = self.dsm_do_level[g, t]

                        # maximum (time-dependent) available shifting capacity
                        rhs = (g.capacity_down_mean
                               * (self.invest[g] + g.investment.existing)
                               * g.flex_share_down * g.shift_time)

                        # add constraint
                        block.dr_storage_limit_red.add((g, t), (lhs <= rhs))

                    else:
                        lhs = self.dsm_do_level[g, t]
                        # Force storage level and thus dsm_do_shift to 0
                        rhs = 0

                        # add constraint
                        block.dr_storage_limit_red.add((g, t), (lhs <= rhs))

        self.dr_storage_limit_red = Constraint(group, m.TIMESTEPS,
                                               noruleinit=True)
        self.dr_storage_level_red_build = BuildAction(
            rule=dr_storage_limit_red_rule)

        # Equation 4.16
        def dr_storage_limit_inc_rule(block):
            """Fictious demand response storage level for load increase limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    # fictious demand response load reduction storage level
                    lhs = self.dsm_up_level[g, t]

                    # maximum (time-dependent) available shifting capacity
                    rhs = (g.capacity_up_mean
                           * (self.invest[g] + g.investment.existing)
                           * g.flex_share_up * g.shift_time)

                    # add constraint
                    block.dr_storage_limit_inc.add((g, t), (lhs <= rhs))

        self.dr_storage_limit_inc = Constraint(group, m.TIMESTEPS,
                                               noruleinit=True)
        self.dr_storage_level_inc_build = BuildAction(
            rule=dr_storage_limit_inc_rule)

        # Equation 4.17' -> load shedding
        def dr_yearly_limit_shed_rule(block):
            """Introduce overall annual (energy) limit for load shedding
            resp. overall limit for optimization timeframe considered
            A year limit in contrast to Gils (2015) is defined a mandatory
            parameter here in order to achieve an approach comparable
            to the others.
            """
            for g in group:
                # sum of all load reductions
                lhs = sum(self.dsm_do_shed[g, t]
                          for t in m.TIMESTEPS)

                # year limit
                rhs = (g.capacity_down_mean
                       * (self.invest[g] + g.investment.existing)
                       * g.flex_share_down * g.shed_time
                       * g.n_yearLimit_shed)

                # add constraint
                block.dr_yearly_limit_shed.add(g, (lhs <= rhs))

        self.dr_yearly_limit_shed = Constraint(group, noruleinit=True)
        self.dr_yearly_limit_shed_build = BuildAction(
            rule=dr_yearly_limit_shed_rule)

        # ************* Optional Constraints *****************************

        # Equation 4.17
        def dr_yearly_limit_red_rule(block):
            """Introduce overall annual (energy) limit for load reductions
            resp. overall limit for optimization timeframe considered
            """
            for g in group:

                if g.ActivateYearLimit:
                    # sum of all load reductions
                    lhs = sum(sum(self.dsm_do_shift[g, h, t]
                                  for h in g.delay_time)
                              for t in m.TIMESTEPS)

                    # year limit
                    rhs = (g.capacity_down_mean
                           * (self.invest[g] + g.investment.existing)
                           * g.flex_share_down * g.shift_time
                           * g.n_yearLimit_shift)

                    # add constraint
                    block.dr_yearly_limit_red.add(g, (lhs <= rhs))

                else:
                    pass  # return(Constraint.Skip)

        self.dr_yearly_limit_red = Constraint(group, noruleinit=True)
        self.dr_yearly_limit_red_build = BuildAction(
            rule=dr_yearly_limit_red_rule)

        # Equation 4.18
        def dr_yearly_limit_inc_rule(block):
            """Introduce overall annual (energy) limit for load increases
            resp. overall limit for optimization timeframe considered
            """
            for g in group:

                if g.ActivateYearLimit:
                    # sum of all load increases
                    lhs = sum(sum(self.dsm_up[g, h, t]
                                  for h in g.delay_time)
                              for t in m.TIMESTEPS)

                    # year limit
                    rhs = (g.capacity_up_mean
                           * (self.invest[g] + g.investment.existing)
                           * g.flex_share_up * g.shift_time
                           * g.n_yearLimit_shift)

                    # add constraint
                    block.dr_yearly_limit_inc.add(g, (lhs <= rhs))

                else:
                    pass  # return(Constraint.Skip)

        self.dr_yearly_limit_inc = Constraint(group, noruleinit=True)
        self.dr_yearly_limit_inc_build = BuildAction(
            rule=dr_yearly_limit_inc_rule)

        # Equation 4.19
        def dr_daily_limit_red_rule(block):
            """Introduce rolling (energy) limit for load reductions
            This effectively limits DR utilization dependent on
            activations within previous hours.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.ActivateDayLimit:

                        # main use case
                        if t >= g.t_dayLimit:

                            # load reduction
                            lhs = sum(self.dsm_do_shift[g, h, t]
                                      for h in g.delay_time)

                            # daily limit
                            rhs = (
                                g.capacity_down_mean
                                * (self.invest[g] + g.investment.existing)
                                * g.flex_share_down * g.shift_time
                                - sum(sum(self.dsm_do_shift[g, h, t - t_dash]
                                          for h in g.delay_time)
                                      for t_dash
                                      in range(1, int(g.t_dayLimit) + 1)))

                            # add constraint
                            block.dr_daily_limit_red.add((g, t), (lhs <= rhs))

                        else:
                            pass  # return(Constraint.Skip)

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_daily_limit_red = Constraint(group, m.TIMESTEPS,
                                             noruleinit=True)
        self.dr_daily_limit_red_build = BuildAction(
            rule=dr_daily_limit_red_rule)

        # Equation 4.20
        def dr_daily_limit_inc_rule(block):
            """Introduce rolling (energy) limit for load increases
            This effectively limits DR utilization dependent on
            activations within previous hours.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.ActivateDayLimit:

                        # main use case
                        if t >= g.t_dayLimit:

                            # load increase
                            lhs = sum(self.dsm_up[g, h, t]
                                      for h in g.delay_time)

                            # daily limit
                            rhs = (
                                g.capacity_up_mean
                                * (self.invest[g] + g.investment.existing)
                                * g.flex_share_up * g.shift_time
                                - sum(sum(self.dsm_up[g, h, t - t_dash]
                                          for h in g.delay_time)
                                      for t_dash
                                      in range(1, int(g.t_dayLimit) + 1)))

                            # add constraint
                            block.dr_daily_limit_inc.add((g, t), (lhs <= rhs))

                        else:
                            pass  # return(Constraint.Skip)

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_daily_limit_inc = Constraint(group, m.TIMESTEPS,
                                             noruleinit=True)
        self.dr_daily_limit_inc_build = BuildAction(
            rule=dr_daily_limit_inc_rule)

        # Addition: avoid simultaneous activations
        def dr_logical_constraint_rule(block):
            """Similar to equation 10 from Zerrahn and Schill (2015):
            The sum of upwards and downwards shifts may not be greater
            than the (bigger) capacity limit.
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.addition:

                        # sum of load increases and reductions
                        lhs = (sum(self.dsm_up[g, h, t]
                                   + self.balance_dsm_do[g, h, t]
                                   + self.dsm_do_shift[g, h, t]
                                   + self.balance_dsm_up[g, h, t]
                                   for h in g.delay_time)
                               + self.dsm_do_shed[g, t])

                        # maximum capacity eligibly for load shifting
                        rhs = (max(g.capacity_down[t] * g.flex_share_down,
                                   g.capacity_up[t] * g.flex_share_up)
                               * (self.invest[g] + g.investment.existing))

                        # add constraint
                        block.dr_logical_constraint.add((g, t), (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_logical_constraint = Constraint(group, m.TIMESTEPS,
                                                noruleinit=True)
        self.dr_logical_constraint_build = BuildAction(
            rule=dr_logical_constraint_rule)

    def _objective_expression(self):
        r"""Objective expression with variable and investment costs for DSM;
        Equation 4.23 from Gils (2015)
        """
        m = self.parent_block()

        investment_costs = 0
        variable_costs = 0

        for g in self.INVESTDR:
            if g.investment.ep_costs is not None:
                investment_costs += self.invest[g] * g.investment.ep_costs
            else:
                raise ValueError("Missing value for investment costs!")
            for t in m.TIMESTEPS:
                variable_costs += (sum(self.dsm_up[g, h, t]
                                       + self.balance_dsm_do[g, h, t]
                                       for h in g.delay_time)
                                   * g.cost_dsm_up[t])
                variable_costs += (sum(self.dsm_do_shift[g, h, t]
                                       + self.balance_dsm_up[g, h, t]
                                       for h in g.delay_time)
                                   * g.cost_dsm_down_shift[t]
                                   + self.dsm_do_shed[g, t]
                                   * g.cost_dsm_down_shed[t])

        self.cost = Expression(expr=investment_costs + variable_costs)
        return self.cost


class SinkDSMDLRMultiPeriodInvestmentBlock(SinkDSMDLRBlock):
    r"""Constraints for SinkDSMDLRInvestmentBlock

    **The following constraints are created:**

    .. _SinkDSM-equations:

    .. math::
        &
        (1) invest_{min} \leq \quad invest \leq invest_{max}
        &
        (2) \quad \dot{E}_{t} = demand_{t} \cdot invest +
        \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDown} - DSM_{h, t}^{down} - DSM_{h, t}^{balanceUp}
        - DSM_{t}^{shed})
        \quad \forall t \in \mathbb{T} \\
        &
        (3) \quad DSM_{h, t}^{balanceDown}
        = \frac{DSM_{t-t_{shift}^h}^{down}}{\eta}
        \quad \forall t \in [t_{shift}^h..\mathbb{T}], h \in H_{DR} \\
        &
        (4) \quad DSM_{h, t}^{balanceUp} = DSM_{t-t_{shift}^h}^{up} \cdot \eta
        \quad \forall t \in [t_{shift}^{h}..\mathbb{T}], h \in H_{DR} \\
        &
        (5) \quad DSM_{h, t}^{down} = 0
        \quad \forall t \in [\mathbb{T} - t_{shift}^h..\mathbb{T}],
        h \in H_{DR}
        &
       (6) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{down}
        + DSM_{h, t}^{balanceUp}) + DSM_{t}^{shed} \leq capacity_{t}^{down}
        \cdot invest \cdot flexshare^{down}
        \quad \forall t \in \mathbb{T} \\
        &
        (7) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDown}) \leq capacity_{t}^{up}
        \cdot invest \cdot flexshare^{up}
        \quad \forall t \in \mathbb{T} \\
        &
        (8) \quad \Delta t \cdot \displaystyle\sum_{h=1}^{H_{DR}}
        DSM_{h, t}^{down} - DSM_{h, t}^{balanceDown}
        \cdot \eta = W_{t}^{levelDown}
        - W_{t-1}^{levelDown} \quad \forall t \in [1..\mathbb{T}] \\
        &
        (9) \quad \Delta t \cdot \displaystyle\sum_{h=1}^{H_{DR}}
        DSM_{h, t}^{up} \cdot \eta - DSM_{h, t}^{balanceUp}
        = W_{t}^{levelUp}
        - W_{t-1}^{levelUp} \quad \forall t \in [1..\mathbb{T}] \\
        &
        (10) \quad W_{t}^{levelDown} \leq \overline{capacity}_{t}^{down}
        \cdot invest \cdot flexshare^{down}
        \cdot t_{interfere} \quad \forall t \in \mathbb{T} \\
        &
        (11) \quad W_{t}^{levelUp} \leq \overline{capacity}_{t}^{up}
        \cdot invest \cdot flexshare^{up}
        \cdot t_{interfere} \quad \forall t \in \mathbb{T} \\
        &
        (12) \quad \displaystyle\sum_{t=0}^{T} \sum_{h=1}^{H_{DR}}
         DSM_{h, t}^{down} \leq invest \cdot flexshare^{down}
        \cdot \overline{capacity}_{t}^{down} \cdot t_{interfere}
        \cdot n^{yearLimit} \\
        (optional \space constraint)
        &
        (13) \quad \displaystyle\sum_{t=0}^{T} \sum_{h=1}^{H_{DR}}
        DSM_{h, t}^{up} \leq invest \cdot flexshare^{up}
        \cdot \overline{capacity}_{t}^{up} \cdot t_{interfere}
        \cdot n^{yearLimit} \\
        (optional \space constraint
        &
        (14) \quad \displaystyle\sum_{h=1}^{H_{DR}} DSM_{h, t}^{down}
        \leq invest \cdot flexshare^{down} \cdot \overline{capacity}_{t}^{down}
        \cdot t_{interfere} -
        \displaystyle\sum_{t'=1}^{t_{dayLimit}}\sum_{h=1}^{H_{DR}}
        DSM_{h, t-t'}^{down}
        \quad \forall t \in [t-t_{dayLimit}..\mathbb{T}] \\
        (optional \space constraint)
        &
        (15) \quad \displaystyle\sum_{h=1}^{H_{DR}} DSM_{h, t}^{up}
        \leq invest \cdot flexshare^{up} \cdot \overline{capacity}_{t}^{up}
        \cdot t_{interfere} -
        \displaystyle\sum_{t'=1}^{t_{dayLimit}}\sum_{h=1}^{H_{DR}}
        DSM_{h, t-t'}^{up}
        \quad \forall t \in [t-t_{dayLimit}..\mathbb{T}] \\
        (optional \space constraint)
        &
        (16) \quad \displaystyle\sum_{h=1}^{H_{DR}} (DSM_{h, t}^{up}
        + DSM_{h, t}^{balanceDown}
        + DSM_{h, t}^{down} + DSM_{h, t}^{balanceUp})
        + DSM_{t}^{shed}
        \leq \max \{capacity_{t}^{up} \cdot invest \cdot flexshare^{up},
        capacity_{t}^{down} \cdot invest \cdot flexshare^{down} \}
        \quad \forall t \in \mathbb{T} \\ (optional \space constraint)
        &
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):

        if group is None:
            return None

        m = self.parent_block()

        # for all DR components get inflow from bus_elec
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SETS *********************************

        self.MULTIPERIODINVESTDR = Set(initialize=[n for n in group])

        # Depict different delay_times per unit via a mapping
        map_MULTIPERIODINVESTDR_H = {
            k: v for k, v in zip([n for n in group],
                                 [n.delay_time for n in group])
        }

        unique_H = list(set(itertools.chain.from_iterable(
            map_MULTIPERIODINVESTDR_H.values())))
        self.H = Set(initialize=unique_H)

        self.MULTIPERIODINVESTDR_H = Set(
            within=self.MULTIPERIODINVESTDR * self.H,
            initialize=[
                (dr, h)
                for dr in map_MULTIPERIODINVESTDR_H
                for h in map_MULTIPERIODINVESTDR_H[dr]])

        #  ************* VARIABLES *****************************

        # Define bounds for investments in demand response
        def _dr_investvar_bound_rule(block, g, p):
            """
            Rule definition to bound the
            invested demand response capacity `invest`.
            """
            return (g.multiperiodinvestment.minimum[p],
                    g.multiperiodinvestment.maximum[p])

        # Investment in DR capacity
        self.invest = Var(self.MULTIPERIODINVESTDR,
                          m.PERIODS,
                          within=NonNegativeReals,
                          bounds=_dr_investvar_bound_rule)

        # Total capacity
        self.total = Var(self.MULTIPERIODINVESTDR,
                         m.PERIODS,
                         within=NonNegativeReals)

        # Old capacity to be decommissioned (due to lifetime)
        # Old capacity is built out of old exogenous and endogenous capacities
        self.old = Var(self.MULTIPERIODINVESTDR,
                       m.PERIODS,
                       within=NonNegativeReals)

        # Old endogenous capacity to be decommissioned (due to lifetime)
        self.old_end = Var(self.MULTIPERIODINVESTDR,
                           m.PERIODS,
                           within=NonNegativeReals)

        # Old exogenous capacity to be decommissioned (due to lifetime)
        self.old_exo = Var(self.MULTIPERIODINVESTDR,
                           m.PERIODS,
                           within=NonNegativeReals)

        # Variable load shift down (capacity)
        self.dsm_do_shift = Var(self.MULTIPERIODINVESTDR_H,
                                m.TIMESTEPS, initialize=0,
                                within=NonNegativeReals)

        # Variable for load shedding (capacity)
        self.dsm_do_shed = Var(self.MULTIPERIODINVESTDR,
                               m.TIMESTEPS, initialize=0,
                               within=NonNegativeReals)

        # Variable load shift up (capacity)
        self.dsm_up = Var(self.MULTIPERIODINVESTDR_H,
                          m.TIMESTEPS, initialize=0,
                          within=NonNegativeReals)

        # Variable balance load shift down through upwards shift (capacity)
        self.balance_dsm_do = Var(self.MULTIPERIODINVESTDR_H,
                                  m.TIMESTEPS, initialize=0,
                                  within=NonNegativeReals)

        # Variable balance load shift up through downwards shift (capacity)
        self.balance_dsm_up = Var(self.MULTIPERIODINVESTDR_H,
                                  m.TIMESTEPS, initialize=0,
                                  within=NonNegativeReals)

        # Variable fictious DR storage level for downwards load shifts (energy)
        self.dsm_do_level = Var(self.MULTIPERIODINVESTDR,
                                m.TIMESTEPS, initialize=0,
                                within=NonNegativeReals)

        # Variable fictious DR storage level for upwards load shifts (energy)
        self.dsm_up_level = Var(self.MULTIPERIODINVESTDR,
                                m.TIMESTEPS, initialize=0,
                                within=NonNegativeReals)

        #  ************* CONSTRAINTS *****************************

        # Handle unit lifetimes
        def _total_capacity_rule(block):
            """Rule definition for determining total installed
            capacity (taking decommissioning into account)
            """
            for g in group:
                for p in m.PERIODS:
                    if p == 0:
                        expr = (self.total[g, p]
                                == self.invest[g, p]
                                + g.multiperiodinvestment.existing)
                        self.total_dsm_rule.add((g, p), expr)
                    else:
                        expr = (self.total[g, p]
                                == self.invest[g, p]
                                + self.total[g, p - 1]
                                - self.old[g, p])
                        self.total_dsm_rule.add((g, p), expr)

        self.total_dsm_rule = Constraint(group, m.PERIODS,
                                         noruleinit=True)
        self.total_dsm_rule_build = BuildAction(
            rule=_total_capacity_rule)

        def _old_dsm_capacity_rule_end(block):
            """Rule definition for determining old endogenously installed
            capacity to be decommissioned due to reaching its lifetime
            """
            for g in group:
                lifetime = g.multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    if lifetime <= p:
                        expr = (self.old_end[g, p]
                                == self.invest[g, p - lifetime])
                        self.old_dsm_rule_end.add((g, p), expr)
                    else:
                        expr = (self.old_end[g, p]
                                == 0)
                        self.old_dsm_rule_end.add((g, p), expr)

        self.old_dsm_rule_end = Constraint(group,
                                           m.PERIODS,
                                           noruleinit=True)
        self.old_dsm_rule_end_build = BuildAction(
            rule=_old_dsm_capacity_rule_end)

        def _old_dsm_capacity_rule_exo(block):
            """Rule definition for determining old exogenously given capacity
            to be decommissioned due to reaching its lifetime
            """
            for g in group:
                age = g.multiperiodinvestment.age
                lifetime = g.multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    if lifetime - age == p:
                        expr = (
                            self.old_exo[g, p]
                            == g.multiperiodinvestment.existing)
                        self.old_dsm_rule_exo.add((g, p), expr)
                    else:
                        expr = (self.old_exo[g, p]
                                == 0)
                        self.old_dsm_rule_exo.add((g, p), expr)

        self.old_dsm_rule_exo = Constraint(group,
                                           m.PERIODS,
                                           noruleinit=True)
        self.old_dsm_rule_exo_build = BuildAction(
            rule=_old_dsm_capacity_rule_exo)

        def _old_dsm_capacity_rule(block):
            """Rule definition for determining (overall) old capacity
            to be decommissioned due to reaching its lifetime
            """
            for g in group:
                for p in m.PERIODS:
                    expr = (
                        self.old[g, p]
                        == self.old_end[g, p] + self.old_exo[g, p])
                    self.old_dsm_rule.add((g, p), expr)

        self.old_dsm_rule = Constraint(group,
                                       m.PERIODS,
                                       noruleinit=True)
        self.old_dsm_rule_build = BuildAction(
            rule=_old_dsm_capacity_rule)

        def _shift_shed_vars_rule(block):
            """Force shifting resp. shedding variables to zero dependent
            on how boolean parameters for shift resp. shed eligibility
            are set.
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if not g.shift_eligibility:
                            lhs = self.dsm_up[g, h, t]
                            rhs = 0

                            block.shift_shed_vars.add((g, h, t), (lhs == rhs))

                        if not g.shed_eligibility:
                            lhs = self.dsm_do_shed[g, t]
                            rhs = 0

                            block.shift_shed_vars.add((g, h, t), (lhs == rhs))

        self.shift_shed_vars = Constraint(group, self.H, m.TIMESTEPS,
                                          noruleinit=True)
        self.shift_shed_vars_build = BuildAction(
            rule=_shift_shed_vars_rule)

        # Relation between inflow and effective Sink consumption
        def _input_output_relation_rule(block):
            """Relation between input data and pyomo variables.
            The actual demand after DR.
            Bus outflow == Demand +- DR (i.e. effective Sink consumption)
            """
            for p, t in m.TIMEINDEX:

                for g in group:
                    # outflow from bus
                    lhs = m.flow[g.inflow, g, p, t]

                    # Demand +- DR
                    rhs = (g.demand[t] * self.total[g, p]
                           + sum(self.dsm_up[g, h, t]
                                 + self.balance_dsm_do[g, h, t]
                                 - self.dsm_do_shift[g, h, t]
                                 - self.balance_dsm_up[g, h, t]
                                 for h in g.delay_time)
                           - self.dsm_do_shed[g, t])

                    # add constraint
                    block.input_output_relation.add((g, p, t), (lhs == rhs))

        self.input_output_relation = Constraint(group, m.TIMEINDEX,
                                                noruleinit=True)
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule)

        # Equation 4.8
        def capacity_balance_red_rule(block):
            """Load reduction must be balanced by load increase
            within delay_time
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if g.shift_eligibility:

                            # main use case
                            if t >= h:
                                # balance load reduction
                                lhs = self.balance_dsm_do[g, h, t]

                                # load reduction (efficiency considered)
                                rhs = (self.dsm_do_shift[g, h, t - h]
                                       / g.efficiency)

                                # add constraint
                                block.capacity_balance_red.add((g, h, t),
                                                               (lhs == rhs))

                            # no balancing for the first timestep
                            elif t == m.TIMESTEPS[1]:
                                lhs = self.balance_dsm_do[g, h, t]
                                rhs = 0

                                block.capacity_balance_red.add((g, h, t),
                                                               (lhs == rhs))

                            else:
                                pass  # return(Constraint.Skip)

                        # if only shedding is possible, balancing variable is 0
                        else:
                            lhs = self.balance_dsm_do[g, h, t]
                            rhs = 0

                            block.capacity_balance_red.add((g, h, t),
                                                           (lhs == rhs))

        self.capacity_balance_red = Constraint(group, self.H, m.TIMESTEPS,
                                               noruleinit=True)
        self.capacity_balance_red_build = BuildAction(
            rule=capacity_balance_red_rule)

        # Equation 4.9
        def capacity_balance_inc_rule(block):
            """Load increased must be balanced by load reduction
            within delay_time
            """
            for t in m.TIMESTEPS:
                for g in group:
                    for h in g.delay_time:

                        if g.shift_eligibility:

                            # main use case
                            if t >= h:
                                # balance load increase
                                lhs = self.balance_dsm_up[g, h, t]

                                # load increase (efficiency considered)
                                rhs = self.dsm_up[g, h, t - h] * g.efficiency

                                # add constraint
                                block.capacity_balance_inc.add((g, h, t),
                                                               (lhs == rhs))

                            # no balancing for the first timestep
                            elif t == m.TIMESTEPS[1]:
                                lhs = self.balance_dsm_up[g, h, t]
                                rhs = 0

                                block.capacity_balance_inc.add((g, h, t),
                                                               (lhs == rhs))

                            else:
                                pass  # return(Constraint.Skip)

                        # if only shedding is possible, balancing variable is 0
                        else:
                            lhs = self.balance_dsm_up[g, h, t]
                            rhs = 0

                            block.capacity_balance_inc.add((g, h, t),
                                                           (lhs == rhs))

        self.capacity_balance_inc = Constraint(group, self.H, m.TIMESTEPS,
                                               noruleinit=True)
        self.capacity_balance_inc_build = BuildAction(
            rule=capacity_balance_inc_rule)

        # Own addition: prevent shifts which cannot be compensated
        def no_comp_red_rule(block):
            """Prevent downwards shifts that cannot be balanced anymore
            within the optimization timeframe
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.fixes:
                        for h in g.delay_time:

                            if t > m.TIMESTEPS[-1] - h:
                                # no load reduction anymore (dsm_do_shift = 0)
                                lhs = self.dsm_do_shift[g, h, t]
                                rhs = 0
                                block.no_comp_red.add((g, h, t), (lhs == rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.no_comp_red = Constraint(group, self.H, m.TIMESTEPS,
                                      noruleinit=True)
        self.no_comp_red_build = BuildAction(
            rule=no_comp_red_rule)

        # Own addition: prevent shifts which cannot be compensated
        def no_comp_inc_rule(block):
            """Prevent upwards shifts that cannot be balanced anymore
            within the optimization timeframe
            """
            for t in m.TIMESTEPS:
                for g in group:

                    if g.fixes:
                        for h in g.delay_time:

                            if t > m.TIMESTEPS[-1] - h:
                                # no load increase anymore (dsm_up = 0)
                                lhs = self.dsm_up[g, h, t]
                                rhs = 0
                                block.no_comp_inc.add((g, h, t), (lhs == rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.no_comp_inc = Constraint(group, self.H, m.TIMESTEPS,
                                      noruleinit=True)
        self.no_comp_inc_build = BuildAction(
            rule=no_comp_inc_rule)

        # Equation 4.11
        def availability_red_rule(block):
            """Load reduction must be smaller than or equal to the
             (time-dependent) capacity limit
             """
            for p, t in m.TIMEINDEX:
                for g in group:
                    # load reduction
                    lhs = (sum(self.dsm_do_shift[g, h, t]
                               + self.balance_dsm_up[g, h, t]
                               for h in g.delay_time)
                           + self.dsm_do_shed[g, t])

                    # upper bound
                    rhs = (g.capacity_down[t] * self.total[g, p]
                           * g.flex_share_down)

                    # add constraint
                    block.availability_red.add((g, p, t), (lhs <= rhs))

        self.availability_red = Constraint(group, m.TIMEINDEX,
                                           noruleinit=True)
        self.availability_red_build = BuildAction(
            rule=availability_red_rule)

        # Equation 4.12
        def availability_inc_rule(block):
            """Load increase must be smaller than or equal to the
            (time-dependent) capacity limit
            """
            for p, t in m.TIMEINDEX:
                for g in group:
                    # load increase
                    lhs = sum(self.dsm_up[g, h, t]
                              + self.balance_dsm_do[g, h, t]
                              for h in g.delay_time)

                    # upper bound
                    rhs = (g.capacity_up[t] * self.total[g, p]
                           * g.flex_share_up)

                    # add constraint
                    block.availability_inc.add((g, p, t), (lhs <= rhs))

        self.availability_inc = Constraint(group, m.TIMEINDEX,
                                           noruleinit=True)
        self.availability_inc_build = BuildAction(
            rule=availability_inc_rule)

        # Equation 4.13
        def dr_storage_red_rule(block):
            """Fictious demand response storage level for load reductions
            transition equation
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # avoid timesteps prior to t = 0
                    if t > 0:
                        # reduction minus balancing of reductions
                        lhs = (m.timeincrement[t]
                               * sum((self.dsm_do_shift[g, h, t]
                                      - self.balance_dsm_do[g, h, t]
                                      * g.efficiency)
                                     for h in g.delay_time))

                        # load reduction storage level transition
                        rhs = (self.dsm_do_level[g, t]
                               - self.dsm_do_level[g, t - 1])

                        # add constraint
                        block.dr_storage_red.add((g, t), (lhs == rhs))

                    else:
                        # pass  # return(Constraint.Skip)
                        lhs = self.dsm_do_level[g, t]
                        rhs = (m.timeincrement[t]
                               * sum(self.dsm_do_shift[g, h, t]
                                     for h in g.delay_time))
                        block.dr_storage_red.add((g, t), (lhs == rhs))

        self.dr_storage_red = Constraint(group, m.TIMESTEPS,
                                         noruleinit=True)
        self.dr_storage_red_build = BuildAction(
            rule=dr_storage_red_rule)

        # Equation 4.14
        def dr_storage_inc_rule(block):
            """Fictious demand response storage level for load increase
            transition equation
            """
            for t in m.TIMESTEPS:
                for g in group:

                    # avoid timesteps prior to t = 0
                    if t > 0:
                        # increases minus balancing of reductions
                        lhs = (m.timeincrement[t]
                               * sum((self.dsm_up[g, h, t]
                                      * g.efficiency
                                      - self.balance_dsm_up[g, h, t])
                                     for h in g.delay_time))

                        # load increase storage level transition
                        rhs = (self.dsm_up_level[g, t]
                               - self.dsm_up_level[g, t - 1])

                        # add constraint
                        block.dr_storage_inc.add((g, t), (lhs == rhs))

                    else:
                        # pass  # return(Constraint.Skip)
                        lhs = self.dsm_up_level[g, t]
                        rhs = m.timeincrement[t] * sum(self.dsm_up[g, h, t]
                                                       for h in g.delay_time)
                        block.dr_storage_inc.add((g, t), (lhs == rhs))

        self.dr_storage_inc = Constraint(group, m.TIMESTEPS,
                                         noruleinit=True)
        self.dr_storage_inc_build = BuildAction(
            rule=dr_storage_inc_rule)

        # Equation 4.15
        def dr_storage_limit_red_rule(block):
            """
            Fictious demand response storage level for load reduction limit
            """
            for p, t in m.TIMEINDEX:
                for g in group:

                    if g.shift_eligibility:
                        # fictious demand response load reduction storage level
                        lhs = self.dsm_do_level[g, t]

                        # maximum (time-dependent) available shifting capacity
                        rhs = (g.capacity_down_mean * self.total[g, p]
                               * g.flex_share_down * g.shift_time)

                        # add constraint
                        block.dr_storage_limit_red.add((g, p, t), (lhs <= rhs))

                    else:
                        lhs = self.dsm_do_level[g, t]
                        # Force storage level and thus dsm_do_shift to 0
                        rhs = 0

                        # add constraint
                        block.dr_storage_limit_red.add((g, p, t), (lhs <= rhs))

        self.dr_storage_limit_red = Constraint(group, m.TIMEINDEX,
                                               noruleinit=True)
        self.dr_storage_level_red_build = BuildAction(
            rule=dr_storage_limit_red_rule)

        # Equation 4.16
        def dr_storage_limit_inc_rule(block):
            """Fictious demand response storage level for load increase limit
            """
            for p, t in m.TIMEINDEX:
                for g in group:
                    # fictious demand response load reduction storage level
                    lhs = self.dsm_up_level[g, t]

                    # maximum (time-dependent) available shifting capacity
                    rhs = (g.capacity_up_mean * self.total[g, p]
                           * g.flex_share_up * g.shift_time)

                    # add constraint
                    block.dr_storage_limit_inc.add((g, p, t), (lhs <= rhs))

        self.dr_storage_limit_inc = Constraint(group, m.TIMEINDEX,
                                               noruleinit=True)
        self.dr_storage_level_inc_build = BuildAction(
            rule=dr_storage_limit_inc_rule)

        # Equation 4.17' -> load shedding
        def dr_yearly_limit_shed_rule(block):
            """Introduce overall annual (energy) limit for load shedding
            resp. overall limit for optimization timeframe considered
            A year limit in contrast to Gils (2015) is defined a mandatory
            parameter here in order to achieve an approach comparable
            to the others.
            """
            for g in group:
                for p in m.PERIODS:
                    # sum of all load reductions
                    lhs = sum(self.dsm_do_shed[g, t]
                              for t in m.TIMESTEPS)

                    # year limit
                    rhs = (g.capacity_down_mean * self.total[g, p]
                           * g.flex_share_down * g.shed_time
                           * g.n_yearLimit_shed)

                    # add constraint
                    block.dr_yearly_limit_shed.add((g, p), (lhs <= rhs))

        self.dr_yearly_limit_shed = Constraint(group, m.PERIODS,
                                               noruleinit=True)
        self.dr_yearly_limit_shed_build = BuildAction(
            rule=dr_yearly_limit_shed_rule)

        # ************* Optional Constraints *****************************

        # Equation 4.17
        def dr_yearly_limit_red_rule(block):
            """Introduce overall annual (energy) limit for load reductions
            resp. overall limit for optimization timeframe considered
            """
            for g in group:

                if g.ActivateYearLimit:
                    for p in m.PERIODS:
                        # sum of all load reductions
                        lhs = sum(sum(self.dsm_do_shift[g, h, t]
                                      for h in g.delay_time)
                                  for t in m.TIMESTEPS)

                        # year limit
                        rhs = (g.capacity_down_mean * self.total[g, p]
                               * g.flex_share_down * g.shift_time
                               * g.n_yearLimit_shift)

                        # add constraint
                        block.dr_yearly_limit_red.add((g, p), (lhs <= rhs))

                else:
                    pass  # return(Constraint.Skip)

        self.dr_yearly_limit_red = Constraint(group, m.PERIODS,
                                              noruleinit=True)
        self.dr_yearly_limit_red_build = BuildAction(
            rule=dr_yearly_limit_red_rule)

        # Equation 4.18
        def dr_yearly_limit_inc_rule(block):
            """Introduce overall annual (energy) limit for load increases
            resp. overall limit for optimization timeframe considered
            """
            for g in group:

                if g.ActivateYearLimit:
                    for p in m.PERIODS:
                        # sum of all load increases
                        lhs = sum(sum(self.dsm_up[g, h, t]
                                      for h in g.delay_time)
                                  for t in m.TIMESTEPS)

                        # year limit
                        rhs = (g.capacity_up_mean * self.total[g, p]
                               * g.flex_share_up * g.shift_time
                               * g.n_yearLimit_shift)

                        # add constraint
                        block.dr_yearly_limit_inc.add((g, p), (lhs <= rhs))

                else:
                    pass  # return(Constraint.Skip)

        self.dr_yearly_limit_inc = Constraint(group, m.PERIODS,
                                              noruleinit=True)
        self.dr_yearly_limit_inc_build = BuildAction(
            rule=dr_yearly_limit_inc_rule)

        # Equation 4.19
        def dr_daily_limit_red_rule(block):
            """Introduce rolling (energy) limit for load reductions
            This effectively limits DR utilization dependent on
            activations within previous hours.
            """
            for p, t in m.TIMEINDEX:
                for g in group:

                    if g.ActivateDayLimit:

                        # main use case
                        if t >= g.t_dayLimit:

                            # load reduction
                            lhs = sum(self.dsm_do_shift[g, h, t]
                                      for h in g.delay_time)

                            # daily limit
                            rhs = (
                                g.capacity_down_mean * self.total[g, p]
                                * g.flex_share_down * g.shift_time
                                - sum(sum(self.dsm_do_shift[g, h,
                                                            t - t_dash]
                                          for h in g.delay_time)
                                      for t_dash
                                      in range(1, int(g.t_dayLimit) + 1)))

                            # add constraint
                            block.dr_daily_limit_red.add(
                                (g, p, t), (lhs <= rhs))

                        else:
                            pass  # return(Constraint.Skip)

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_daily_limit_red = Constraint(group, m.TIMEINDEX,
                                             noruleinit=True)
        self.dr_daily_limit_red_build = BuildAction(
            rule=dr_daily_limit_red_rule)

        # Equation 4.20
        def dr_daily_limit_inc_rule(block):
            """Introduce rolling (energy) limit for load increases
            This effectively limits DR utilization dependent on
            activations within previous hours.
            """
            for p, t in m.TIMEINDEX:
                for g in group:

                    if g.ActivateDayLimit:

                        # main use case
                        if t >= g.t_dayLimit:

                            # load increase
                            lhs = sum(self.dsm_up[g, h, t]
                                      for h in g.delay_time)

                            # daily limit
                            rhs = (
                                g.capacity_up_mean * self.total[g, p]
                                * g.flex_share_up * g.shift_time
                                - sum(sum(self.dsm_up[g, h, t - t_dash]
                                          for h in g.delay_time)
                                      for t_dash
                                      in range(1, int(g.t_dayLimit) + 1)))

                            # add constraint
                            block.dr_daily_limit_inc.add((g, t), (lhs <= rhs))

                        else:
                            pass  # return(Constraint.Skip)

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_daily_limit_inc = Constraint(group, m.TIMEINDEX,
                                             noruleinit=True)
        self.dr_daily_limit_inc_build = BuildAction(
            rule=dr_daily_limit_inc_rule)

        # Addition: avoid simultaneous activations
        def dr_logical_constraint_rule(block):
            """Similar to equation 10 from Zerrahn and Schill (2015):
            The sum of upwards and downwards shifts may not be greater
            than the (bigger) capacity limit.
            """
            for p, t in m.TIMEINDEX:
                for g in group:

                    if g.addition:

                        # sum of load increases and reductions
                        lhs = (sum(self.dsm_up[g, h, t]
                                   + self.balance_dsm_do[g, h, t]
                                   + self.dsm_do_shift[g, h, t]
                                   + self.balance_dsm_up[g, h, t]
                                   for h in g.delay_time)
                               + self.dsm_do_shed[g, t])

                        # maximum capacity eligibly for load shifting
                        rhs = (max(g.capacity_down[t] * g.flex_share_down,
                                   g.capacity_up[t] * g.flex_share_up)
                               * self.total[g, p])

                        # add constraint
                        block.dr_logical_constraint.add(
                            (g, p, t), (lhs <= rhs))

                    else:
                        pass  # return(Constraint.Skip)

        self.dr_logical_constraint = Constraint(group, m.TIMEINDEX,
                                                noruleinit=True)
        self.dr_logical_constraint_build = BuildAction(
            rule=dr_logical_constraint_rule)

    def _objective_expression(self):
        r"""Objective expression with variable, investment and fixed costs.
        """
        m = self.parent_block()

        investment_costs = 0
        variable_costs = 0
        fixed_costs = 0

        for g in self.MULTIPERIODINVESTDR:
            if g.multiperiodinvestment.ep_costs is not None:
                lifetime = g.multiperiodinvestment.lifetime
                interest = g.multiperiodinvestment.interest_rate
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
                        capex=g.multiperiodinvestment.ep_costs[p],
                        n=lifetime,
                        wacc=interest)
                    investment_costs += (
                        self.invest[g, p] * annuity * lifetime
                        * ((1 + m.discount_rate) ** (-p))
                    )
            else:
                raise ValueError("Missing value for investment costs!")
            for p, t in m.TIMEINDEX:
                variable_costs += ((sum(self.dsm_up[g, h, t]
                                        + self.balance_dsm_do[g, h, t]
                                        for h in g.delay_time)
                                    * g.cost_dsm_up[p])
                                   * m.objective_weighting[t]
                                   * ((1 + m.discount_rate) ** -p))
                variable_costs += ((sum(self.dsm_do_shift[g, h, t]
                                        + self.balance_dsm_up[g, h, t]
                                        for h in g.delay_time)
                                    * g.cost_dsm_down_shift[p]
                                    + self.dsm_do_shed[g, t]
                                    * g.cost_dsm_down_shed[p])
                                   * m.objective_weighting[t]
                                   * ((1 + m.discount_rate) ** -p))

            if g.multiperiodinvestment.fixed_costs[0] is not None:
                lifetime = g.multiperiodinvestment.lifetime
                for p in m.PERIODS:
                    fixed_costs += (
                        sum(self.invest[g, p]
                            * g.multiperiodinvestment.fixed_costs[pp]
                            * ((1 + m.discount_rate) ** (-pp))
                            for pp in range(p, p + lifetime)
                            )
                        * ((1 + m.discount_rate) ** (-p))
                    )

        self.cost = Expression(
            expr=investment_costs + fixed_costs + variable_costs)
        return self.cost
