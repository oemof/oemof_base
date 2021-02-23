# -*- coding: utf-8 -

"""This module is designed to hold components with their classes and
associated individual constraints (blocks) and groupings. Therefore this
module holds the class definition and the block directly located by each other.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: FranziPl
SPDX-FileCopyrightText: jnnr
SPDX-FileCopyrightText: Stephan Günther
SPDX-FileCopyrightText: FabianTU
SPDX-FileCopyrightText: Johannes Röder

SPDX-License-Identifier: MIT

"""

import numpy as np
from oemof.network import network
from pyomo.core.base.block import SimpleBlock
from pyomo.environ import Binary
from pyomo.environ import BuildAction
from pyomo.environ import Constraint
from pyomo.environ import Expression
from pyomo.environ import NonNegativeReals
from pyomo.environ import Set
from pyomo.environ import Var

from oemof.solph import network as solph_network
from oemof.solph.options import Investment
from oemof.solph.plumbing import sequence as solph_sequence


class GenericStorage(network.Node):
    r"""
    Component `GenericStorage` to model with basic characteristics of storages.

    The GenericStorage is designed for one input and one output.

    Parameters
    ----------
    nominal_storage_capacity : numeric, :math:`E_{nom}`
        Absolute nominal capacity of the storage

    invest_relation_input_capacity : numeric or None, :math:`r_{cap,in}`
        Ratio between the investment variable of the input Flow and the
        investment variable of the storage:
        :math:`\dot{E}_{in,invest} = E_{invest} \cdot r_{cap,in}`

    invest_relation_output_capacity : numeric or None, :math:`r_{cap,out}`
        Ratio between the investment variable of the output Flow and the
        investment variable of the storage:
        :math:`\dot{E}_{out,invest} = E_{invest} \cdot r_{cap,out}`

    invest_relation_input_output : numeric or None, :math:`r_{in,out}`
        Ratio between the investment variable of the output Flow and the
        investment variable of the input flow. This ratio used to fix the
        flow investments to each other.
        Values < 1 set the input flow lower than the output and > 1 will
        set the input flow higher than the output flow. If None no relation
        will be set:
        :math:`\dot{E}_{in,invest} = \dot{E}_{out,invest} \cdot r_{in,out}`

    initial_storage_level : numeric, :math:`c(-1)`
        The relative storage content in the timestep before the first
        time step of optimization (between 0 and 1).
    balanced : boolean
        Couple storage level of first and last time step.
        (Total inflow and total outflow are balanced.)
    loss_rate : numeric (iterable or scalar)
        The relative loss of the storage content per time unit.
    fixed_losses_relative : numeric (iterable or scalar), :math:`\gamma(t)`
        Losses independent of state of charge between two consecutive
        timesteps relative to nominal storage capacity.
    fixed_losses_absolute : numeric (iterable or scalar), :math:`\delta(t)`
        Losses independent of state of charge and independent of
        nominal storage capacity between two consecutive timesteps.
    inflow_conversion_factor : numeric (iterable or scalar), :math:`\eta_i(t)`
        The relative conversion factor, i.e. efficiency associated with the
        inflow of the storage.
    outflow_conversion_factor : numeric (iterable or scalar), :math:`\eta_o(t)`
        see: inflow_conversion_factor
    min_storage_level : numeric (iterable or scalar), :math:`c_{min}(t)`
        The normed minimum storage content as fraction of the
        nominal storage capacity (between 0 and 1).
        To set different values in every time step use a sequence.
    max_storage_level : numeric (iterable or scalar), :math:`c_{max}(t)`
        see: min_storage_level
    investment : :class:`oemof.solph.options.Investment` object
        Object indicating if a nominal_value of the flow is determined by
        the optimization problem. Note: This will refer all attributes to an
        investment variable instead of to the nominal_storage_capacity. The
        nominal_storage_capacity should not be set (or set to None) if an
        investment object is used.

    Note
    ----
    The following sets, variables, constraints and objective parts are created
     * :py:class:`~oemof.solph.components.GenericStorageBlock` (if no
       Investment object present)
     * :py:class:`~oemof.solph.components.GenericInvestmentStorageBlock` (if
       Investment object present)

    Examples
    --------
    Basic usage examples of the GenericStorage with a random selection of
    attributes. See the Flow class for all Flow attributes.

    >>> from oemof import solph

    >>> my_bus = solph.Bus('my_bus')

    >>> my_storage = solph.components.GenericStorage(
    ...     label='storage',
    ...     nominal_storage_capacity=1000,
    ...     inputs={my_bus: solph.Flow(nominal_value=200, variable_costs=10)},
    ...     outputs={my_bus: solph.Flow(nominal_value=200)},
    ...     loss_rate=0.01,
    ...     initial_storage_level=0,
    ...     max_storage_level = 0.9,
    ...     inflow_conversion_factor=0.9,
    ...     outflow_conversion_factor=0.93)

    >>> my_investment_storage = solph.components.GenericStorage(
    ...     label='storage',
    ...     investment=solph.Investment(ep_costs=50),
    ...     inputs={my_bus: solph.Flow()},
    ...     outputs={my_bus: solph.Flow()},
    ...     loss_rate=0.02,
    ...     initial_storage_level=None,
    ...     invest_relation_input_capacity=1/6,
    ...     invest_relation_output_capacity=1/6,
    ...     inflow_conversion_factor=1,
    ...     outflow_conversion_factor=0.8)
    """

    def __init__(
        self, *args, max_storage_level=1, min_storage_level=0, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.nominal_storage_capacity = kwargs.get("nominal_storage_capacity")
        self.initial_storage_level = kwargs.get("initial_storage_level")
        self.balanced = kwargs.get("balanced", True)
        self.loss_rate = solph_sequence(kwargs.get("loss_rate", 0))
        self.fixed_losses_relative = solph_sequence(
            kwargs.get("fixed_losses_relative", 0)
        )
        self.fixed_losses_absolute = solph_sequence(
            kwargs.get("fixed_losses_absolute", 0)
        )
        self.inflow_conversion_factor = solph_sequence(
            kwargs.get("inflow_conversion_factor", 1)
        )
        self.outflow_conversion_factor = solph_sequence(
            kwargs.get("outflow_conversion_factor", 1)
        )
        self.max_storage_level = solph_sequence(max_storage_level)
        self.min_storage_level = solph_sequence(min_storage_level)
        self.investment = kwargs.get("investment")
        self.invest_relation_input_output = kwargs.get(
            "invest_relation_input_output"
        )
        self.invest_relation_input_capacity = kwargs.get(
            "invest_relation_input_capacity"
        )
        self.invest_relation_output_capacity = kwargs.get(
            "invest_relation_output_capacity"
        )
        self._invest_group = isinstance(self.investment, Investment)

        # Check number of flows.
        self._check_number_of_flows()

        # Check attributes for the investment mode.
        if self._invest_group is True:
            self._check_invest_attributes()

        # Check for old parameter names. This is a temporary fix and should
        # be removed once a general solution is found.
        # TODO: https://github.com/oemof/oemof-solph/issues/560
        renamed_parameters = [
            ("nominal_capacity", "nominal_storage_capacity"),
            ("initial_capacity", "initial_storage_level"),
            ("capacity_loss", "loss_rate"),
            ("capacity_min", "min_storage_level"),
            ("capacity_max", "max_storage_level"),
        ]
        messages = [
            "`{0}` to `{1}`".format(old_name, new_name)
            for old_name, new_name in renamed_parameters
            if old_name in kwargs
        ]
        if messages:
            message = (
                "The following attributes have been renamed from v0.2 to v0.3:"
                "\n\n  {}\n\n"
                "You are using the old names as parameters, thus setting "
                "deprecated\n"
                "attributes, which is not what you might have intended.\n"
                "Use the new names, or, if you know what you're doing, set "
                "these\n"
                "attributes explicitly after construction instead."
            )
            raise AttributeError(message.format("\n  ".join(messages)))

    def _set_flows(self):
        for flow in self.inputs.values():
            if (
                self.invest_relation_input_capacity is not None
                and not isinstance(flow.investment, Investment)
            ):
                flow.investment = Investment()
        for flow in self.outputs.values():
            if (
                self.invest_relation_output_capacity is not None
                and not isinstance(flow.investment, Investment)
            ):
                flow.investment = Investment()

    def _check_invest_attributes(self):
        if self.investment and self.nominal_storage_capacity is not None:
            e1 = (
                "If an investment object is defined the invest variable "
                "replaces the nominal_storage_capacity.\n Therefore the "
                "nominal_storage_capacity should be 'None'.\n"
            )
            raise AttributeError(e1)
        if (
            self.invest_relation_input_output is not None
            and self.invest_relation_output_capacity is not None
            and self.invest_relation_input_capacity is not None
        ):
            e2 = (
                "Overdetermined. Three investment object will be coupled"
                "with three constraints. Set one invest relation to 'None'."
            )
            raise AttributeError(e2)
        if (
            self.investment
            and sum(solph_sequence(self.fixed_losses_absolute)) != 0
            and self.investment.existing == 0
            and self.investment.minimum == 0
        ):
            e3 = (
                "With fixed_losses_absolute > 0, either investment.existing "
                "or investment.minimum has to be non-zero."
            )
            raise AttributeError(e3)

        self._set_flows()

    def _check_number_of_flows(self):
        msg = "Only one {0} flow allowed in the GenericStorage {1}."
        solph_network.check_node_object_for_missing_attribute(self, "inputs")
        solph_network.check_node_object_for_missing_attribute(self, "outputs")
        if len(self.inputs) > 1:
            raise AttributeError(msg.format("input", self.label))
        if len(self.outputs) > 1:
            raise AttributeError(msg.format("output", self.label))

    def constraint_group(self):
        if self._invest_group is True:
            return GenericInvestmentStorageBlock
        else:
            return GenericStorageBlock


# Todo: accessed by


class GenericStorageBlock(SimpleBlock):
    r"""Storage without an :class:`.Investment` object.

    **The following sets are created:** (-> see basic sets at
    :class:`.Model` )

    STORAGES
        A set with all :class:`.Storage` objects, which do not have an
         attr:`investment` of type :class:`.Investment`.

    STORAGES_BALANCED
        A set of  all :class:`.Storage` objects, with 'balanced' attribute set
        to True.

    STORAGES_WITH_INVEST_FLOW_REL
        A set with all :class:`.Storage` objects with two investment flows
        coupled with the 'invest_relation_input_output' attribute.

    **The following variables are created:**

    storage_content
        Storage content for every storage and timestep. The value for the
        storage content at the beginning is set by the parameter `initial_storage_level`
        or not set if `initial_storage_level` is None.
        The variable of storage s and timestep t can be accessed by:
        `om.Storage.storage_content[s, t]`

    **The following constraints are created:**

    Set storage_content of last time step to one at t=0 if :attr:`balanced == True`
        .. math::
            E(t_{last}) = &E(-1)

    Storage balance :attr:`om.Storage.balance[n, t]`
        .. math:: E(t) = &E(t-1) \cdot
            (1 - \beta(t)) ^{\tau(t)/(t_u)} \\
            &- \gamma(t)\cdot E_{nom} \cdot {\tau(t)/(t_u)}\\
            &- \delta(t) \cdot {\tau(t)/(t_u)}\\
            &- \frac{\dot{E}_o(t)}{\eta_o(t)} \cdot \tau(t)
            + \dot{E}_i(t) \cdot \eta_i(t) \cdot \tau(t)





    =========================== ======================= =========
    symbol                      explanation             attribute
    =========================== ======================= =========
    :math:`E(t)`                energy currently stored :py:obj:`storage_content`
    :math:`E_{nom}`             nominal capacity of     :py:obj:`nominal_storage_capacity`
                                the energy storage
    :math:`c(-1)`               state before            :py:obj:`initial_storage_level`
                                initial time step
    :math:`c_{min}(t)`          minimum allowed storage :py:obj:`min_storage_level[t]`
    :math:`c_{max}(t)`          maximum allowed storage :py:obj:`max_storage_level[t]`
    :math:`\beta(t)`            fraction of lost energy :py:obj:`loss_rate[t]`
                                as share of
                                :math:`E(t)`
                                per time unit
    :math:`\gamma(t)`           fixed loss of energy    :py:obj:`fixed_losses_relative[t]`
                                relative to
                                :math:`E_{nom}` per
                                time unit
    :math:`\delta(t)`           absolute fixed loss     :py:obj:`fixed_losses_absolute[t]`
                                of energy per
                                time unit
    :math:`\dot{E}_i(t)`        energy flowing in       :py:obj:`inputs`
    :math:`\dot{E}_o(t)`        energy flowing out      :py:obj:`outputs`
    :math:`\eta_i(t)`           conversion factor       :py:obj:`inflow_conversion_factor[t]`
                                (i.e. efficiency)
                                when storing energy
    :math:`\eta_o(t)`           conversion factor when  :py:obj:`outflow_conversion_factor[t]`
                                (i.e. efficiency)
                                taking stored energy
    :math:`\tau(t)`             duration of time step
    :math:`t_u`                 time unit of losses
                                :math:`\beta(t)`,
                                :math:`\gamma(t)`
                                :math:`\delta(t)` and
                                timeincrement
                                :math:`\tau(t)`
    =========================== ======================= =========

    **The following parts of the objective function are created:**

    Nothing added to the objective function.


    """  # noqa: E501

    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """
        Parameters
        ----------
        group : list
            List containing storage objects.
            e.g. groups=[storage1, storage2,..]
        """
        m = self.parent_block()

        if group is None:
            return None

        i = {n: [i for i in n.inputs][0] for n in group}
        o = {n: [o for o in n.outputs][0] for n in group}

        #  ************* SETS *********************************

        self.STORAGES = Set(initialize=[n for n in group])

        self.STORAGES_BALANCED = Set(
            initialize=[n for n in group if n.balanced is True]
        )

        self.STORAGES_WITH_INVEST_FLOW_REL = Set(
            initialize=[
                n for n in group if n.invest_relation_input_output is not None
            ]
        )

        #  ************* VARIABLES *****************************

        def _storage_content_bound_rule(block, n, t):
            """
            Rule definition for bounds of storage_content variable of
            storage n in timestep t.
            """
            bounds = (
                n.nominal_storage_capacity * n.min_storage_level[t],
                n.nominal_storage_capacity * n.max_storage_level[t],
            )
            return bounds

        self.storage_content = Var(
            self.STORAGES, m.TIMESTEPS, bounds=_storage_content_bound_rule
        )

        def _storage_init_content_bound_rule(block, n):
            return 0, n.nominal_storage_capacity

        self.init_content = Var(
            self.STORAGES,
            within=NonNegativeReals,
            bounds=_storage_init_content_bound_rule,
        )

        # set the initial storage content
        for n in group:
            if n.initial_storage_level is not None:
                self.init_content[n] = (
                    n.initial_storage_level * n.nominal_storage_capacity
                )
                self.init_content[n].fix()

        #  ************* Constraints ***************************

        reduced_timesteps = [x for x in m.TIMESTEPS if x > 0]

        # storage balance constraint (first time step)
        def _storage_balance_first_rule(block, n):
            """
            Rule definition for the storage balance of every storage n for
            the first timestep.
            """
            expr = 0
            expr += block.storage_content[n, 0]
            expr += (
                -block.init_content[n]
                * (1 - n.loss_rate[0]) ** m.timeincrement[0]
            )
            expr += (
                n.fixed_losses_relative[0]
                * n.nominal_storage_capacity
                * m.timeincrement[0]
            )
            expr += n.fixed_losses_absolute[0] * m.timeincrement[0]
            expr += (
                -m.flow[i[n], n, 0] * n.inflow_conversion_factor[0]
            ) * m.timeincrement[0]
            expr += (
                m.flow[n, o[n], 0] / n.outflow_conversion_factor[0]
            ) * m.timeincrement[0]
            return expr == 0

        self.balance_first = Constraint(
            self.STORAGES, rule=_storage_balance_first_rule
        )

        # storage balance constraint (every time step but the first)
        def _storage_balance_rule(block, n, t):
            """
            Rule definition for the storage balance of every storage n and
            every timestep but the first (t > 0).
            """
            expr = 0
            expr += block.storage_content[n, t]
            expr += (
                -block.storage_content[n, t - 1]
                * (1 - n.loss_rate[t]) ** m.timeincrement[t]
            )
            expr += (
                n.fixed_losses_relative[t]
                * n.nominal_storage_capacity
                * m.timeincrement[t]
            )
            expr += n.fixed_losses_absolute[t] * m.timeincrement[t]
            expr += (
                -m.flow[i[n], n, t] * n.inflow_conversion_factor[t]
            ) * m.timeincrement[t]
            expr += (
                m.flow[n, o[n], t] / n.outflow_conversion_factor[t]
            ) * m.timeincrement[t]
            return expr == 0

        self.balance = Constraint(
            self.STORAGES, reduced_timesteps, rule=_storage_balance_rule
        )

        def _balanced_storage_rule(block, n):
            """
            Storage content of last time step == initial storage content
            if balanced.
            """
            return (
                block.storage_content[n, m.TIMESTEPS[-1]]
                == block.init_content[n]
            )

        self.balanced_cstr = Constraint(
            self.STORAGES_BALANCED, rule=_balanced_storage_rule
        )

        def _power_coupled(block, n):
            """
            Rule definition for constraint to connect the input power
            and output power
            """
            expr = (
                m.InvestmentFlow.invest[n, o[n]]
                + m.flows[n, o[n]].investment.existing
            ) * n.invest_relation_input_output == (
                m.InvestmentFlow.invest[i[n], n]
                + m.flows[i[n], n].investment.existing
            )
            return expr

        self.power_coupled = Constraint(
            self.STORAGES_WITH_INVEST_FLOW_REL, rule=_power_coupled
        )

    def _objective_expression(self):
        r"""
        Objective expression for storages with no investment.
        Note: This adds nothing as variable costs are already
        added in the Block :class:`Flow`.
        """
        if not hasattr(self, "STORAGES"):
            return 0

        return 0


class GenericInvestmentStorageBlock(SimpleBlock):
    r"""
    Block for all storages with :attr:`Investment` being not None.
    See :class:`oemof.solph.options.Investment` for all parameters of the
    Investment class.

    **Variables**

    All Storages are indexed by :math:`n`, which is omitted in the following
    for the sake of convenience.
    The following variables are created as attributes of
    :attr:`om.InvestmentStorage`:

    * :math:`P_i(t)`

        Inflow of the storage
        (created in :class:`oemof.solph.models.BaseModel`).

    * :math:`P_o(t)`

        Outflow of the storage
        (created in :class:`oemof.solph.models.BaseModel`).

    * :math:`E(t)`

        Current storage content (Absolute level of stored energy).

    * :math:`E_{invest}`

        Invested (nominal) capacity of the storage.

    * :math:`E(-1)`

        Initial storage content (before timestep 0).

    * :math:`b_{invest}`

        Binary variable for the status of the investment, if
        :attr:`nonconvex` is `True`.

    **Constraints**

    The following constraints are created for all investment storages:

            Storage balance (Same as for :class:`.GenericStorageBlock`)

        .. math:: E(t) = &E(t-1) \cdot
            (1 - \beta(t)) ^{\tau(t)/(t_u)} \\
            &- \gamma(t)\cdot (E_{exist} + E_{invest}) \cdot {\tau(t)/(t_u)}\\
            &- \delta(t) \cdot {\tau(t)/(t_u)}\\
            &- \frac{P_o(t)}{\eta_o(t)} \cdot \tau(t)
            + P_i(t) \cdot \eta_i(t) \cdot \tau(t)

    Depending on the attribute :attr:`nonconvex`, the constraints for the
    bounds of the decision variable :math:`E_{invest}` are different:\

        * :attr:`nonconvex = False`

        .. math::
            E_{invest, min} \le E_{invest} \le E_{invest, max}

        * :attr:`nonconvex = True`

        .. math::
            &
            E_{invest, min} \cdot b_{invest} \le E_{invest}\\
            &
            E_{invest} \le E_{invest, max} \cdot b_{invest}\\

    The following constraints are created depending on the attributes of
    the :class:`.components.GenericStorage`:

        * :attr:`initial_storage_level is None`

            Constraint for a variable initial storage content:

        .. math::
               E(-1) \le E_{invest} + E_{exist}

        * :attr:`initial_storage_level is not None`

            An initial value for the storage content is given:

        .. math::
               E(-1) = (E_{invest} + E_{exist}) \cdot c(-1)

        * :attr:`balanced=True`

            The energy content of storage of the first and the last timestep
            are set equal:

        .. math::
            E(-1) = E(t_{last})

        * :attr:`invest_relation_input_capacity is not None`

            Connect the invest variables of the storage and the input flow:

        .. math::
            P_{i,invest} + P_{i,exist} =
            (E_{invest} + E_{exist}) \cdot r_{cap,in}

        * :attr:`invest_relation_output_capacity is not None`

            Connect the invest variables of the storage and the output flow:

        .. math::
            P_{o,invest} + P_{o,exist} =
            (E_{invest} + E_{exist}) \cdot r_{cap,out}

        * :attr:`invest_relation_input_output is not None`

            Connect the invest variables of the input and the output flow:

        .. math::
            P_{i,invest} + P_{i,exist} =
            (P_{o,invest} + P_{o,exist}) \cdot r_{in,out}

        * :attr:`max_storage_level`

            Rule for upper bound constraint for the storage content:

        .. math::
            E(t) \leq (E_{invest} +  E_{exist}) \cdot c_{max}(t)

        * :attr:`min_storage_level`

            Rule for lower bound constraint for the storage content:

        .. math:: E(t) \geq (E_{invest} +  E_{exist}) \cdot c_{min}(t)


    **Objective function**

    The part of the objective function added by the investment storages
    also depends on whether a convex or nonconvex
    investment option is selected. The following parts of the objective
    function are created:

        * :attr:`nonconvex = False`

            .. math::
                E_{invest} \cdot c_{invest,var}

        * :attr:`nonconvex = True`

            .. math::
                E_{invest} \cdot c_{invest,var}
                + c_{invest,fix} \cdot b_{invest}\\

    The total value of all investment costs of all *InvestmentStorages*
    can be retrieved calling
    :meth:`om.GenericInvestmentStorageBlock.investment_costs.expr()`.

    .. csv-table:: List of Variables
        :header: "symbol", "attribute", "explanation"
        :widths: 1, 1, 1

        ":math:`P_i(t)`", ":attr:`flow[i[n], n, t]`", "Inflow of the storage"
        ":math:`P_o(t)`", ":attr:`flow[n, o[n], t]`", "Outlfow of the storage"
        ":math:`E(t)`", ":attr:`storage_content[n, t]`", "Current storage
        content (current absolute stored energy)"
        ":math:`E_{invest}`", ":attr:`invest[n, t]`", "Invested (nominal)
        capacity of the storage"
        ":math:`E(-1)`", ":attr:`init_cap[n]`", "Initial storage capacity
        (before timestep 0)"
        ":math:`b_{invest}`", ":attr:`invest_status[i, o]`", "Binary variable
        for the status of investment"
        ":math:`P_{i,invest}`", ":attr:`InvestmentFlow.invest[i[n], n]`", "
        Invested (nominal) inflow (Investmentflow)"
        ":math:`P_{o,invest}`", ":attr:`InvestmentFlow.invest[n, o[n]]`", "
        Invested (nominal) outflow (Investmentflow)"

    .. csv-table:: List of Parameters
        :header: "symbol", "attribute", "explanation"
        :widths: 1, 1, 1

        ":math:`E_{exist}`", ":py:obj:`flows[i, o].investment.existing`", "
        Existing storage capacity"
        ":math:`E_{invest,min}`", ":py:obj:`flows[i, o].investment.minimum`", "
        Minimum investment value"
        ":math:`E_{invest,max}`", ":py:obj:`flows[i, o].investment.maximum`", "
        Maximum investment value"
        ":math:`P_{i,exist}`", ":py:obj:`flows[i[n], n].investment.existing`
        ", "Existing inflow capacity"
        ":math:`P_{o,exist}`", ":py:obj:`flows[n, o[n]].investment.existing`
        ", "Existing outlfow capacity"
        ":math:`c_{invest,var}`", ":py:obj:`flows[i, o].investment.ep_costs`
        ", "Variable investment costs"
        ":math:`c_{invest,fix}`", ":py:obj:`flows[i, o].investment.offset`", "
        Fix investment costs"
        ":math:`r_{cap,in}`", ":attr:`invest_relation_input_capacity`", "
        Relation of storage capacity and nominal inflow"
        ":math:`r_{cap,out}`", ":attr:`invest_relation_output_capacity`", "
        Relation of storage capacity and nominal outflow"
        ":math:`r_{in,out}`", ":attr:`invest_relation_input_output`", "
        Relation of nominal in- and outflow"
        ":math:`\beta(t)`", ":py:obj:`loss_rate[t]`", "Fraction of lost energy
        as share of :math:`E(t)` per time unit"
        ":math:`\gamma(t)`", ":py:obj:`fixed_losses_relative[t]`", "Fixed loss
        of energy relative to :math:`E_{invest} + E_{exist}` per time unit"
        ":math:`\delta(t)`", ":py:obj:`fixed_losses_absolute[t]`", "Absolute
        fixed loss of energy per time unit"
        ":math:`\eta_i(t)`", ":py:obj:`inflow_conversion_factor[t]`", "
        Conversion factor (i.e. efficiency) when storing energy"
        ":math:`\eta_o(t)`", ":py:obj:`outflow_conversion_factor[t]`", "
        Conversion factor when (i.e. efficiency) taking stored energy"
        ":math:`c(-1)`", ":py:obj:`initial_storage_level`", "Initial relativ
        storage content (before timestep 0)"
        ":math:`c_{max}`", ":py:obj:`flows[i, o].max[t]`", "Normed maximum
        value of storage content"
        ":math:`c_{min}`", ":py:obj:`flows[i, o].min[t]`", "Normed minimum
        value of storage content"
        ":math:`\tau(t)`", "", "Duration of time step"
        ":math:`t_u`", "", "Time unit of losses :math:`\beta(t)`,
        :math:`\gamma(t)`, :math:`\delta(t)` and timeincrement :math:`\tau(t)`"

    """

    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """"""
        m = self.parent_block()
        if group is None:
            return None

        # ########################## SETS #####################################

        self.INVESTSTORAGES = Set(initialize=[n for n in group])

        self.CONVEX_INVESTSTORAGES = Set(
            initialize=[n for n in group if n.investment.nonconvex is False]
        )

        self.NON_CONVEX_INVESTSTORAGES = Set(
            initialize=[n for n in group if n.investment.nonconvex is True]
        )

        self.INVESTSTORAGES_BALANCED = Set(
            initialize=[n for n in group if n.balanced is True]
        )

        self.INVESTSTORAGES_NO_INIT_CONTENT = Set(
            initialize=[n for n in group if n.initial_storage_level is None]
        )

        self.INVESTSTORAGES_INIT_CONTENT = Set(
            initialize=[
                n for n in group if n.initial_storage_level is not None
            ]
        )

        self.INVEST_REL_CAP_IN = Set(
            initialize=[
                n
                for n in group
                if n.invest_relation_input_capacity is not None
            ]
        )

        self.INVEST_REL_CAP_OUT = Set(
            initialize=[
                n
                for n in group
                if n.invest_relation_output_capacity is not None
            ]
        )

        self.INVEST_REL_IN_OUT = Set(
            initialize=[
                n for n in group if n.invest_relation_input_output is not None
            ]
        )

        # The storage content is a non-negative variable, therefore it makes no
        # sense to create an additional constraint if the lower bound is zero
        # for all time steps.
        self.MIN_INVESTSTORAGES = Set(
            initialize=[
                n
                for n in group
                if sum([n.min_storage_level[t] for t in m.TIMESTEPS]) > 0
            ]
        )

        # ######################### Variables  ################################
        self.storage_content = Var(
            self.INVESTSTORAGES, m.TIMESTEPS, within=NonNegativeReals
        )

        def _storage_investvar_bound_rule(block, n):
            """
            Rule definition to bound the invested storage capacity `invest`.
            """
            if n in self.CONVEX_INVESTSTORAGES:
                return n.investment.minimum, n.investment.maximum
            elif n in self.NON_CONVEX_INVESTSTORAGES:
                return 0, n.investment.maximum

        self.invest = Var(
            self.INVESTSTORAGES,
            within=NonNegativeReals,
            bounds=_storage_investvar_bound_rule,
        )

        self.init_content = Var(self.INVESTSTORAGES, within=NonNegativeReals)

        # create status variable for a non-convex investment storage
        self.invest_status = Var(self.NON_CONVEX_INVESTSTORAGES, within=Binary)

        # ######################### CONSTRAINTS ###############################
        i = {n: [i for i in n.inputs][0] for n in group}
        o = {n: [o for o in n.outputs][0] for n in group}

        reduced_timesteps = [x for x in m.TIMESTEPS if x > 0]

        def _inv_storage_init_content_max_rule(block, n):
            """Constraint for a variable initial storage capacity."""
            return (
                block.init_content[n]
                <= n.investment.existing + block.invest[n]
            )

        self.init_content_limit = Constraint(
            self.INVESTSTORAGES_NO_INIT_CONTENT,
            rule=_inv_storage_init_content_max_rule,
        )

        def _inv_storage_init_content_fix_rule(block, n):
            """Constraint for a fixed initial storage capacity."""
            return block.init_content[n] == n.initial_storage_level * (
                n.investment.existing + block.invest[n]
            )

        self.init_content_fix = Constraint(
            self.INVESTSTORAGES_INIT_CONTENT,
            rule=_inv_storage_init_content_fix_rule,
        )

        def _storage_balance_first_rule(block, n):
            """
            Rule definition for the storage balance of every storage n for the
            first time step.
            """
            expr = 0
            expr += block.storage_content[n, 0]
            expr += (
                -block.init_content[n]
                * (1 - n.loss_rate[0]) ** m.timeincrement[0]
            )
            expr += (
                n.fixed_losses_relative[0]
                * (n.investment.existing + self.invest[n])
                * m.timeincrement[0]
            )
            expr += n.fixed_losses_absolute[0] * m.timeincrement[0]
            expr += (
                -m.flow[i[n], n, 0] * n.inflow_conversion_factor[0]
            ) * m.timeincrement[0]
            expr += (
                m.flow[n, o[n], 0] / n.outflow_conversion_factor[0]
            ) * m.timeincrement[0]
            return expr == 0

        self.balance_first = Constraint(
            self.INVESTSTORAGES, rule=_storage_balance_first_rule
        )

        def _storage_balance_rule(block, n, t):
            """
            Rule definition for the storage balance of every storage n for the
            every time step but the first.
            """
            expr = 0
            expr += block.storage_content[n, t]
            expr += (
                -block.storage_content[n, t - 1]
                * (1 - n.loss_rate[t]) ** m.timeincrement[t]
            )
            expr += (
                n.fixed_losses_relative[t]
                * (n.investment.existing + self.invest[n])
                * m.timeincrement[t]
            )
            expr += n.fixed_losses_absolute[t] * m.timeincrement[t]
            expr += (
                -m.flow[i[n], n, t] * n.inflow_conversion_factor[t]
            ) * m.timeincrement[t]
            expr += (
                m.flow[n, o[n], t] / n.outflow_conversion_factor[t]
            ) * m.timeincrement[t]
            return expr == 0

        self.balance = Constraint(
            self.INVESTSTORAGES, reduced_timesteps, rule=_storage_balance_rule
        )

        def _balanced_storage_rule(block, n):
            return (
                block.storage_content[n, m.TIMESTEPS[-1]]
                == block.init_content[n]
            )

        self.balanced_cstr = Constraint(
            self.INVESTSTORAGES_BALANCED, rule=_balanced_storage_rule
        )

        def _power_coupled(block, n):
            """
            Rule definition for constraint to connect the input power
            and output power
            """
            expr = (
                m.InvestmentFlow.invest[n, o[n]]
                + m.flows[n, o[n]].investment.existing
            ) * n.invest_relation_input_output == (
                m.InvestmentFlow.invest[i[n], n]
                + m.flows[i[n], n].investment.existing
            )
            return expr

        self.power_coupled = Constraint(
            self.INVEST_REL_IN_OUT, rule=_power_coupled
        )

        def _storage_capacity_inflow_invest_rule(block, n):
            """
            Rule definition of constraint connecting the inflow
            `InvestmentFlow.invest of storage with invested capacity `invest`
            by nominal_storage_capacity__inflow_ratio
            """
            expr = (
                m.InvestmentFlow.invest[i[n], n]
                + m.flows[i[n], n].investment.existing
            ) == (
                n.investment.existing + self.invest[n]
            ) * n.invest_relation_input_capacity
            return expr

        self.storage_capacity_inflow = Constraint(
            self.INVEST_REL_CAP_IN, rule=_storage_capacity_inflow_invest_rule
        )

        def _storage_capacity_outflow_invest_rule(block, n):
            """
            Rule definition of constraint connecting outflow
            `InvestmentFlow.invest` of storage and invested capacity `invest`
            by nominal_storage_capacity__outflow_ratio
            """
            expr = (
                m.InvestmentFlow.invest[n, o[n]]
                + m.flows[n, o[n]].investment.existing
            ) == (
                n.investment.existing + self.invest[n]
            ) * n.invest_relation_output_capacity
            return expr

        self.storage_capacity_outflow = Constraint(
            self.INVEST_REL_CAP_OUT, rule=_storage_capacity_outflow_invest_rule
        )

        def _max_storage_content_invest_rule(block, n, t):
            """
            Rule definition for upper bound constraint for the
            storage content.
            """
            expr = (
                self.storage_content[n, t]
                <= (n.investment.existing + self.invest[n])
                * n.max_storage_level[t]
            )
            return expr

        self.max_storage_content = Constraint(
            self.INVESTSTORAGES,
            m.TIMESTEPS,
            rule=_max_storage_content_invest_rule,
        )

        def _min_storage_content_invest_rule(block, n, t):
            """
            Rule definition of lower bound constraint for the
            storage content.
            """
            expr = (
                self.storage_content[n, t]
                >= (n.investment.existing + self.invest[n])
                * n.min_storage_level[t]
            )
            return expr

        # Set the lower bound of the storage content if the attribute exists
        self.min_storage_content = Constraint(
            self.MIN_INVESTSTORAGES,
            m.TIMESTEPS,
            rule=_min_storage_content_invest_rule,
        )

        def maximum_invest_limit(block, n):
            """
            Constraint for the maximal investment in non convex investment
            storage.
            """
            return (
                n.investment.maximum * self.invest_status[n] - self.invest[n]
            ) >= 0

        self.limit_max = Constraint(
            self.NON_CONVEX_INVESTSTORAGES, rule=maximum_invest_limit
        )

        def smallest_invest(block, n):
            """
            Constraint for the minimal investment in non convex investment
            storage if the invest is greater than 0. So the invest variable
            can be either 0 or greater than the minimum.
            """
            return (
                self.invest[n] - (n.investment.minimum * self.invest_status[n])
                >= 0
            )

        self.limit_min = Constraint(
            self.NON_CONVEX_INVESTSTORAGES, rule=smallest_invest
        )

    def _objective_expression(self):
        """Objective expression with fixed and investement costs."""
        if not hasattr(self, "INVESTSTORAGES"):
            return 0

        investment_costs = 0

        for n in self.CONVEX_INVESTSTORAGES:
            investment_costs += self.invest[n] * n.investment.ep_costs
        for n in self.NON_CONVEX_INVESTSTORAGES:
            investment_costs += (
                self.invest[n] * n.investment.ep_costs
                + self.invest_status[n] * n.investment.offset
            )
        self.investment_costs = Expression(expr=investment_costs)

        return investment_costs


class GenericCHP(network.Transformer):
    r"""
    Component `GenericCHP` to model combined heat and power plants.

    Can be used to model (combined cycle) extraction or back-pressure turbines
    and used a mixed-integer linear formulation. Thus, it induces more
    computational effort than the `ExtractionTurbineCHP` for the
    benefit of higher accuracy.

    The full set of equations is described in:
    Mollenhauer, E., Christidis, A. & Tsatsaronis, G.
    Evaluation of an energy- and exergy-based generic modeling
    approach of combined heat and power plants
    Int J Energy Environ Eng (2016) 7: 167.
    https://doi.org/10.1007/s40095-016-0204-6

    For a general understanding of (MI)LP CHP representation, see:
    Fabricio I. Salgado, P.
    Short - Term Operation Planning on Cogeneration Systems: A Survey
    Electric Power Systems Research (2007)
    Electric Power Systems Research
    Volume 78, Issue 5, May 2008, Pages 835-848
    https://doi.org/10.1016/j.epsr.2007.06.001

    Note
    ----
    An adaption for the flow parameter `H_L_FG_share_max` has been made to
    set the flue gas losses at maximum heat extraction `H_L_FG_max` as share of
    the fuel flow `H_F` e.g. for combined cycle extraction turbines.
    The flow parameter `H_L_FG_share_min` can be used to set the flue gas
    losses at minimum heat extraction `H_L_FG_min` as share of
    the fuel flow `H_F` e.g. for motoric CHPs.
    The boolean component parameter `back_pressure` can be set to model
    back-pressure characteristics.

    Also have a look at the examples on how to use it.

    Parameters
    ----------
    fuel_input : dict
        Dictionary with key-value-pair of `oemof.Bus` and `oemof.Flow` object
        for the fuel input.
    electrical_output : dict
        Dictionary with key-value-pair of `oemof.Bus` and `oemof.Flow` object
        for the electrical output. Related parameters like `P_max_woDH` are
        passed as attributes of the `oemof.Flow` object.
    heat_output : dict
        Dictionary with key-value-pair of `oemof.Bus` and `oemof.Flow` object
        for the heat output. Related parameters like `Q_CW_min` are passed as
        attributes of the `oemof.Flow` object.
    Beta : list of numerical values
        Beta values in same dimension as all other parameters (length of
        optimization period).
    back_pressure : boolean
        Flag to use back-pressure characteristics. Set to `True` and
        `Q_CW_min` to zero for back-pressure turbines. See paper above for more
        information.

    Note
    ----
    The following sets, variables, constraints and objective parts are created
     * :py:class:`~oemof.solph.components.GenericCHPBlock`

    Examples
    --------
    >>> from oemof import solph
    >>> bel = solph.Bus(label='electricityBus')
    >>> bth = solph.Bus(label='heatBus')
    >>> bgas = solph.Bus(label='commodityBus')
    >>> ccet = solph.components.GenericCHP(
    ...    label='combined_cycle_extraction_turbine',
    ...    fuel_input={bgas: solph.Flow(
    ...        H_L_FG_share_max=[0.183])},
    ...    electrical_output={bel: solph.Flow(
    ...        P_max_woDH=[155.946],
    ...        P_min_woDH=[68.787],
    ...        Eta_el_max_woDH=[0.525],
    ...        Eta_el_min_woDH=[0.444])},
    ...    heat_output={bth: solph.Flow(
    ...        Q_CW_min=[10.552])},
    ...    Beta=[0.122], back_pressure=False)
    >>> type(ccet)
    <class 'oemof.solph.components.GenericCHP'>
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fuel_input = kwargs.get("fuel_input")
        self.electrical_output = kwargs.get("electrical_output")
        self.heat_output = kwargs.get("heat_output")
        self.Beta = solph_sequence(kwargs.get("Beta"))
        self.back_pressure = kwargs.get("back_pressure")
        self._alphas = None

        # map specific flows to standard API
        fuel_bus = list(self.fuel_input.keys())[0]
        fuel_flow = list(self.fuel_input.values())[0]
        fuel_bus.outputs.update({self: fuel_flow})

        self.outputs.update(kwargs.get("electrical_output"))
        self.outputs.update(kwargs.get("heat_output"))

    def _calculate_alphas(self):
        """
        Calculate alpha coefficients.

        A system of linear equations is created from passed capacities and
        efficiencies and solved to calculate both coefficients.
        """
        alphas = [[], []]

        eb = list(self.electrical_output.keys())[0]

        attrs = [
            self.electrical_output[eb].P_min_woDH,
            self.electrical_output[eb].Eta_el_min_woDH,
            self.electrical_output[eb].P_max_woDH,
            self.electrical_output[eb].Eta_el_max_woDH,
        ]

        length = [len(a) for a in attrs if not isinstance(a, (int, float))]
        max_length = max(length)

        if all(len(a) == max_length for a in attrs):
            if max_length == 0:
                max_length += 1  # increment dimension for scalars from 0 to 1
            for i in range(0, max_length):
                A = np.array(
                    [
                        [1, self.electrical_output[eb].P_min_woDH[i]],
                        [1, self.electrical_output[eb].P_max_woDH[i]],
                    ]
                )
                b = np.array(
                    [
                        self.electrical_output[eb].P_min_woDH[i]
                        / self.electrical_output[eb].Eta_el_min_woDH[i],
                        self.electrical_output[eb].P_max_woDH[i]
                        / self.electrical_output[eb].Eta_el_max_woDH[i],
                    ]
                )
                x = np.linalg.solve(A, b)
                alphas[0].append(x[0])
                alphas[1].append(x[1])
        else:
            error_message = (
                "Attributes to calculate alphas "
                + "must be of same dimension."
            )
            raise ValueError(error_message)

        self._alphas = alphas

    @property
    def alphas(self):
        """Compute or return the _alphas attribute."""
        if self._alphas is None:
            self._calculate_alphas()
        return self._alphas

    def constraint_group(self):
        return GenericCHPBlock


class GenericCHPBlock(SimpleBlock):
    r"""
    Block for the relation of the :math:`n` nodes with
    type class:`.GenericCHP`.

    **The following constraints are created:**

    .. _GenericCHP-equations1-10:

    .. math::
        &
        (1)\qquad \dot{H}_F(t) = fuel\ input \\
        &
        (2)\qquad \dot{Q}(t) = heat\ output \\
        &
        (3)\qquad P_{el}(t) = power\ output\\
        &
        (4)\qquad \dot{H}_F(t) = \alpha_0(t) \cdot Y(t) + \alpha_1(t) \cdot
        P_{el,woDH}(t)\\
        &
        (5)\qquad \dot{H}_F(t) = \alpha_0(t) \cdot Y(t) + \alpha_1(t) \cdot
        ( P_{el}(t) + \beta \cdot \dot{Q}(t) )\\
        &
        (6)\qquad \dot{H}_F(t) \leq Y(t) \cdot
        \frac{P_{el, max, woDH}(t)}{\eta_{el,max,woDH}(t)}\\
        &
        (7)\qquad \dot{H}_F(t) \geq Y(t) \cdot
        \frac{P_{el, min, woDH}(t)}{\eta_{el,min,woDH}(t)}\\
        &
        (8)\qquad \dot{H}_{L,FG,max}(t) = \dot{H}_F(t) \cdot
        \dot{H}_{L,FG,sharemax}(t)\\
        &
        (9)\qquad \dot{H}_{L,FG,min}(t) = \dot{H}_F(t) \cdot
        \dot{H}_{L,FG,sharemin}(t)\\
        &
        (10)\qquad P_{el}(t) + \dot{Q}(t) + \dot{H}_{L,FG,max}(t) +
        \dot{Q}_{CW, min}(t) \cdot Y(t) = / \leq \dot{H}_F(t)\\

    where :math:`= / \leq` depends on the CHP being back pressure or not.

    The coefficients :math:`\alpha_0` and :math:`\alpha_1`
    can be determined given the efficiencies maximal/minimal load:

    .. math::
        &
        \eta_{el,max,woDH}(t) = \frac{P_{el,max,woDH}(t)}{\alpha_0(t)
        \cdot Y(t) + \alpha_1(t) \cdot P_{el,max,woDH}(t)}\\
        &
        \eta_{el,min,woDH}(t) = \frac{P_{el,min,woDH}(t)}{\alpha_0(t)
        \cdot Y(t) + \alpha_1(t) \cdot P_{el,min,woDH}(t)}\\


    **For the attribute** :math:`\dot{H}_{L,FG,min}` **being not None**,
    e.g. for a motoric CHP, **the following is created:**

        **Constraint:**

    .. _GenericCHP-equations11:

    .. math::
        &
        (11)\qquad P_{el}(t) + \dot{Q}(t) + \dot{H}_{L,FG,min}(t) +
        \dot{Q}_{CW, min}(t) \cdot Y(t) \geq \dot{H}_F(t)\\[10pt]

    The symbols used are defined as follows (with Variables (V) and Parameters (P)):

    =============================== =============================== ==== =======================
    math. symbol                    attribute                       type explanation
    =============================== =============================== ==== =======================
    :math:`\dot{H}_{F}`             :py:obj:`H_F[n,t]`              V    input of enthalpy
                                                                         through fuel input
    :math:`P_{el}`                  :py:obj:`P[n,t]`                V    provided
                                                                         electric power
    :math:`P_{el,woDH}`             :py:obj:`P_woDH[n,t]`           V    electric power without
                                                                         district heating
    :math:`P_{el,min,woDH}`         :py:obj:`P_min_woDH[n,t]`       P    min. electric power
                                                                         without district heating
    :math:`P_{el,max,woDH}`         :py:obj:`P_max_woDH[n,t]`       P    max. electric power
                                                                         without district heating
    :math:`\dot{Q}`                 :py:obj:`Q[n,t]`                V    provided heat

    :math:`\dot{Q}_{CW, min}`       :py:obj:`Q_CW_min[n,t]`         P    minimal therm. condenser
                                                                         load to cooling water
    :math:`\dot{H}_{L,FG,min}`      :py:obj:`H_L_FG_min[n,t]`       V    flue gas enthalpy loss
                                                                         at min heat extraction
    :math:`\dot{H}_{L,FG,max}`      :py:obj:`H_L_FG_max[n,t]`       V    flue gas enthalpy loss
                                                                         at max heat extraction
    :math:`\dot{H}_{L,FG,sharemin}` :py:obj:`H_L_FG_share_min[n,t]` P    share of flue gas loss
                                                                         at min heat extraction
    :math:`\dot{H}_{L,FG,sharemax}` :py:obj:`H_L_FG_share_max[n,t]` P    share of flue gas loss
                                                                         at max heat extraction
    :math:`Y`                       :py:obj:`Y[n,t]`                V    status variable
                                                                         on/off
    :math:`\alpha_0`                :py:obj:`n.alphas[0][n,t]`      P    coefficient
                                                                         describing efficiency
    :math:`\alpha_1`                :py:obj:`n.alphas[1][n,t]`      P    coefficient
                                                                         describing efficiency
    :math:`\beta`                   :py:obj:`Beta[n,t]`             P    power loss index

    :math:`\eta_{el,min,woDH}`      :py:obj:`Eta_el_min_woDH[n,t]`  P    el. eff. at min. fuel
                                                                         flow w/o distr. heating
    :math:`\eta_{el,max,woDH}`      :py:obj:`Eta_el_max_woDH[n,t]`  P    el. eff. at max. fuel
                                                                         flow w/o distr. heating
    =============================== =============================== ==== =======================

    """  # noqa: E501
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """
        Create constraints for GenericCHPBlock.

        Parameters
        ----------
        group : list
            List containing `GenericCHP` objects.
            e.g. groups=[ghcp1, gchp2,..]
        """
        m = self.parent_block()

        if group is None:
            return None

        self.GENERICCHPS = Set(initialize=[n for n in group])

        # variables
        self.H_F = Var(self.GENERICCHPS, m.TIMESTEPS, within=NonNegativeReals)
        self.H_L_FG_max = Var(
            self.GENERICCHPS, m.TIMESTEPS, within=NonNegativeReals
        )
        self.H_L_FG_min = Var(
            self.GENERICCHPS, m.TIMESTEPS, within=NonNegativeReals
        )
        self.P_woDH = Var(
            self.GENERICCHPS, m.TIMESTEPS, within=NonNegativeReals
        )
        self.P = Var(self.GENERICCHPS, m.TIMESTEPS, within=NonNegativeReals)
        self.Q = Var(self.GENERICCHPS, m.TIMESTEPS, within=NonNegativeReals)
        self.Y = Var(self.GENERICCHPS, m.TIMESTEPS, within=Binary)

        # constraint rules
        def _H_flow_rule(block, n, t):
            """Link fuel consumption to component inflow."""
            expr = 0
            expr += self.H_F[n, t]
            expr += -m.flow[list(n.fuel_input.keys())[0], n, t]
            return expr == 0

        self.H_flow = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_H_flow_rule
        )

        def _Q_flow_rule(block, n, t):
            """Link heat flow to component outflow."""
            expr = 0
            expr += self.Q[n, t]
            expr += -m.flow[n, list(n.heat_output.keys())[0], t]
            return expr == 0

        self.Q_flow = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_Q_flow_rule
        )

        def _P_flow_rule(block, n, t):
            """Link power flow to component outflow."""
            expr = 0
            expr += self.P[n, t]
            expr += -m.flow[n, list(n.electrical_output.keys())[0], t]
            return expr == 0

        self.P_flow = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_P_flow_rule
        )

        def _H_F_1_rule(block, n, t):
            """Set P_woDH depending on H_F."""
            expr = 0
            expr += -self.H_F[n, t]
            expr += n.alphas[0][t] * self.Y[n, t]
            expr += n.alphas[1][t] * self.P_woDH[n, t]
            return expr == 0

        self.H_F_1 = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_H_F_1_rule
        )

        def _H_F_2_rule(block, n, t):
            """Determine relation between H_F, P and Q."""
            expr = 0
            expr += -self.H_F[n, t]
            expr += n.alphas[0][t] * self.Y[n, t]
            expr += n.alphas[1][t] * (self.P[n, t] + n.Beta[t] * self.Q[n, t])
            return expr == 0

        self.H_F_2 = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_H_F_2_rule
        )

        def _H_F_3_rule(block, n, t):
            """Set upper value of operating range via H_F."""
            expr = 0
            expr += self.H_F[n, t]
            expr += -self.Y[n, t] * (
                list(n.electrical_output.values())[0].P_max_woDH[t]
                / list(n.electrical_output.values())[0].Eta_el_max_woDH[t]
            )
            return expr <= 0

        self.H_F_3 = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_H_F_3_rule
        )

        def _H_F_4_rule(block, n, t):
            """Set lower value of operating range via H_F."""
            expr = 0
            expr += self.H_F[n, t]
            expr += -self.Y[n, t] * (
                list(n.electrical_output.values())[0].P_min_woDH[t]
                / list(n.electrical_output.values())[0].Eta_el_min_woDH[t]
            )
            return expr >= 0

        self.H_F_4 = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_H_F_4_rule
        )

        def _H_L_FG_max_rule(block, n, t):
            """Set max. flue gas loss as share fuel flow share."""
            expr = 0
            expr += -self.H_L_FG_max[n, t]
            expr += (
                self.H_F[n, t]
                * list(n.fuel_input.values())[0].H_L_FG_share_max[t]
            )
            return expr == 0

        self.H_L_FG_max_def = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_H_L_FG_max_rule
        )

        def _Q_max_res_rule(block, n, t):
            """Set maximum Q depending on fuel and electrical flow."""
            expr = 0
            expr += self.P[n, t] + self.Q[n, t] + self.H_L_FG_max[n, t]
            expr += list(n.heat_output.values())[0].Q_CW_min[t] * self.Y[n, t]
            expr += -self.H_F[n, t]
            # back-pressure characteristics or one-segment model
            if n.back_pressure is True:
                return expr == 0
            else:
                return expr <= 0

        self.Q_max_res = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_Q_max_res_rule
        )

        def _H_L_FG_min_rule(block, n, t):
            """Set min. flue gas loss as fuel flow share."""
            # minimum flue gas losses e.g. for motoric CHPs
            if getattr(
                list(n.fuel_input.values())[0], "H_L_FG_share_min", None
            ):
                expr = 0
                expr += -self.H_L_FG_min[n, t]
                expr += (
                    self.H_F[n, t]
                    * list(n.fuel_input.values())[0].H_L_FG_share_min[t]
                )
                return expr == 0
            else:
                return Constraint.Skip

        self.H_L_FG_min_def = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_H_L_FG_min_rule
        )

        def _Q_min_res_rule(block, n, t):
            """Set minimum Q depending on fuel and eletrical flow."""
            # minimum restriction for heat flows e.g. for motoric CHPs
            if getattr(
                list(n.fuel_input.values())[0], "H_L_FG_share_min", None
            ):
                expr = 0
                expr += self.P[n, t] + self.Q[n, t] + self.H_L_FG_min[n, t]
                expr += (
                    list(n.heat_output.values())[0].Q_CW_min[t] * self.Y[n, t]
                )
                expr += -self.H_F[n, t]
                return expr >= 0
            else:
                return Constraint.Skip

        self.Q_min_res = Constraint(
            self.GENERICCHPS, m.TIMESTEPS, rule=_Q_min_res_rule
        )

    def _objective_expression(self):
        r"""Objective expression for generic CHPs with no investment.

        Note: This adds nothing as variable costs are already
        added in the Block :class:`Flow`.
        """
        if not hasattr(self, "GENERICCHPS"):
            return 0

        return 0


class ExtractionTurbineCHP(solph_network.Transformer):
    r"""
    A CHP with an extraction turbine in a linear model. For more options see
    the :class:`~oemof.solph.components.GenericCHP` class.

    One main output flow has to be defined and is tapped by the remaining flow.
    The conversion factors have to be defined for the maximum tapped flow (
    full CHP mode) and for no tapped flow (full condensing mode). Even though
    it is possible to limit the variability of the tapped flow, so that the
    full condensing mode will never be reached.

    Parameters
    ----------
    conversion_factors : dict
        Dictionary containing conversion factors for conversion of inflow
        to specified outflow. Keys are output bus objects.
        The dictionary values can either be a scalar or a sequence with length
        of time horizon for simulation.
    conversion_factor_full_condensation : dict
        The efficiency of the main flow if there is no tapped flow. Only one
        key is allowed. Use one of the keys of the conversion factors. The key
        indicates the main flow. The other output flow is the tapped flow.

    Note
    ----
    The following sets, variables, constraints and objective parts are created
     * :py:class:`~oemof.solph.components.ExtractionTurbineCHPBlock`

    Examples
    --------
    >>> from oemof import solph
    >>> bel = solph.Bus(label='electricityBus')
    >>> bth = solph.Bus(label='heatBus')
    >>> bgas = solph.Bus(label='commodityBus')
    >>> et_chp = solph.components.ExtractionTurbineCHP(
    ...    label='variable_chp_gas',
    ...    inputs={bgas: solph.Flow(nominal_value=10e10)},
    ...    outputs={bel: solph.Flow(), bth: solph.Flow()},
    ...    conversion_factors={bel: 0.3, bth: 0.5},
    ...    conversion_factor_full_condensation={bel: 0.5})
    """

    def __init__(self, conversion_factor_full_condensation, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversion_factor_full_condensation = {
            k: solph_sequence(v)
            for k, v in conversion_factor_full_condensation.items()
        }

    def constraint_group(self):
        return ExtractionTurbineCHPBlock


class ExtractionTurbineCHPBlock(SimpleBlock):
    r"""Block for the linear relation of nodes with type
    :class:`~oemof.solph.components.ExtractionTurbineCHP`

    **The following two constraints are created:**

    .. _ETCHP-equations:

        .. math::
            &
            (1)\dot H_{Fuel}(t) =
               \frac{P_{el}(t) + \dot Q_{th}(t) \cdot \beta(t)}
                 {\eta_{el,woExtr}(t)} \\
            &
            (2)P_{el}(t) \geq \dot Q_{th}(t) \cdot C_b =
               \dot Q_{th}(t) \cdot
               \frac{\eta_{el,maxExtr}(t)}
                 {\eta_{th,maxExtr}(t)}

    where :math:`\beta` is defined as:

         .. math::
            \beta(t) = \frac{\eta_{el,woExtr}(t) -
            \eta_{el,maxExtr}(t)}{\eta_{th,maxExtr}(t)}

    where the first equation is the result of the relation between the input
    flow and the two output flows, the second equation stems from how the two
    output flows relate to each other, and the symbols used are defined as
    follows (with Variables (V) and Parameters (P)):

    ========================= ==================================================== ==== =========
    symbol                    attribute                                            type explanation
    ========================= ==================================================== ==== =========
    :math:`\dot H_{Fuel}`     :py:obj:`flow[i, n, t]`                              V    fuel input flow

    :math:`P_{el}`            :py:obj:`flow[n, main_output, t]`                    V    electric power

    :math:`\dot Q_{th}`       :py:obj:`flow[n, tapped_output, t]`                  V    thermal output

    :math:`\beta`             :py:obj:`main_flow_loss_index[n, t]`                 P    power loss index

    :math:`\eta_{el,woExtr}`  :py:obj:`conversion_factor_full_condensation[n, t]`  P    electric efficiency
                                                                                        without heat extraction
    :math:`\eta_{el,maxExtr}` :py:obj:`conversion_factors[main_output][n, t]`      P    electric efficiency
                                                                                        with max heat extraction
    :math:`\eta_{th,maxExtr}` :py:obj:`conversion_factors[tapped_output][n, t]`    P    thermal efficiency with
                                                                                        maximal heat extraction
    ========================= ==================================================== ==== =========

    """  # noqa: E501

    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """Creates the linear constraint for the
        :class:`oemof.solph.Transformer` block.

        Parameters
        ----------
        group : list
            List of :class:`oemof.solph.ExtractionTurbineCHP` (trsf) objects
            for which the linear relation of inputs and outputs is created
            e.g. group = [trsf1, trsf2, trsf3, ...]. Note that the relation
            is created for all existing relations of the inputs and all outputs
            of the transformer. The components inside the list need to hold
            all needed attributes.
        """
        if group is None:
            return None

        m = self.parent_block()

        for n in group:
            n.inflow = list(n.inputs)[0]
            n.main_flow = [
                k for k, v in n.conversion_factor_full_condensation.items()
            ][0]
            n.main_output = [o for o in n.outputs if n.main_flow == o][0]
            n.tapped_output = [o for o in n.outputs if n.main_flow != o][0]
            n.conversion_factor_full_condensation_sq = (
                n.conversion_factor_full_condensation[n.main_output]
            )
            n.flow_relation_index = [
                n.conversion_factors[n.main_output][t]
                / n.conversion_factors[n.tapped_output][t]
                for t in m.TIMESTEPS
            ]
            n.main_flow_loss_index = [
                (
                    n.conversion_factor_full_condensation_sq[t]
                    - n.conversion_factors[n.main_output][t]
                )
                / n.conversion_factors[n.tapped_output][t]
                for t in m.TIMESTEPS
            ]

        def _input_output_relation_rule(block):
            """Connection between input, main output and tapped output."""
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflow, g, t]
                    rhs = (
                        m.flow[g, g.main_output, t]
                        + m.flow[g, g.tapped_output, t]
                        * g.main_flow_loss_index[t]
                    ) / g.conversion_factor_full_condensation_sq[t]
                    block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule
        )

        def _out_flow_relation_rule(block):
            """Relation between main and tapped output in full chp mode."""
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g, g.main_output, t]
                    rhs = (
                        m.flow[g, g.tapped_output, t]
                        * g.flow_relation_index[t]
                    )
                    block.out_flow_relation.add((g, t), (lhs >= rhs))

        self.out_flow_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.out_flow_relation_build = BuildAction(
            rule=_out_flow_relation_rule
        )


class OffsetTransformer(network.Transformer):
    """An object with one input and one output.

    Parameters
    ----------

    coefficients : tuple
        Tuple containing the first two polynomial coefficients
        i.e. the y-intersection and slope of a linear equation.
        The tuple values can either be a scalar or a sequence with length
        of time horizon for simulation.

    Notes
    -----
    The sets, variables, constraints and objective parts are created
     * :py:class:`~oemof.solph.components.OffsetTransformerBlock`

    Examples
    --------

    >>> from oemof import solph

    >>> bel = solph.Bus(label='bel')
    >>> bth = solph.Bus(label='bth')

    >>> ostf = solph.components.OffsetTransformer(
    ...    label='ostf',
    ...    inputs={bel: solph.Flow(
    ...        nominal_value=60, min=0.5, max=1.0,
    ...        nonconvex=solph.NonConvex())},
    ...    outputs={bth: solph.Flow()},
    ...    coefficients=(20, 0.5))

    >>> type(ostf)
    <class 'oemof.solph.components.OffsetTransformer'>
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if kwargs.get("coefficients") is not None:
            self.coefficients = tuple(
                [solph_sequence(i) for i in kwargs.get("coefficients")]
            )
            if len(self.coefficients) != 2:
                raise ValueError(
                    "Two coefficients or coefficient series have to be given."
                )

        if len(self.inputs) == 1:
            for k, v in self.inputs.items():
                if not v.nonconvex:
                    raise TypeError(
                        "Input flows must be of type NonConvexFlow!"
                    )

        if len(self.inputs) > 1 or len(self.outputs) > 1:
            raise ValueError(
                "Component `OffsetTransformer` must not have "
                + "more than 1 input and 1 output!"
            )

    def constraint_group(self):
        return OffsetTransformerBlock


class OffsetTransformerBlock(SimpleBlock):
    r"""Block for the relation of nodes with type
    :class:`~oemof.solph.components.OffsetTransformer`

    **The following constraints are created:**

    .. _OffsetTransformer-equations:

    .. math::
        &
        P_{out}(t) = C_1(t) \cdot P_{in}(t) + C_0(t) \cdot Y(t) \\


    .. csv-table:: Variables (V) and Parameters (P)
        :header: "symbol", "attribute", "type", "explanation"
        :widths: 1, 1, 1, 1

        ":math:`P_{out}(t)`", ":py:obj:`flow[n, o, t]`", "V", "Power of output"
        ":math:`P_{in}(t)`", ":py:obj:`flow[i, n, t]`", "V","Power of input"
        ":math:`Y(t)`", ":py:obj:`status[i, n, t]`", "V","binary
        status variable of nonconvex input flow "
        ":math:`C_1(t)`", ":py:obj:`coefficients[1][n, t]`", "P", "linear
        coefficient 1 (slope)"
        ":math:`C_0(t)`", ":py:obj:`coefficients[0][n, t]`", "P", "linear
        coefficient 0 (y-intersection)"


    """

    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """Creates the relation for the class:`OffsetTransformer`.

        Parameters
        ----------
        group : list
            List of oemof.solph.custom.OffsetTransformer objects for which
            the relation of inputs and outputs is created
            e.g. group = [ostf1, ostf2, ostf3, ...]. The components inside
            the list need to hold an attribute `coefficients` of type dict
            containing the conversion factors for all inputs to outputs.
        """
        if group is None:
            return None

        m = self.parent_block()

        self.OFFSETTRANSFORMERS = Set(initialize=[n for n in group])

        def _relation_rule(block, n, t):
            """Link binary input and output flow to component outflow."""
            expr = 0
            expr += -m.flow[n, list(n.outputs.keys())[0], t]
            expr += (
                m.flow[list(n.inputs.keys())[0], n, t] * n.coefficients[1][t]
            )
            expr += (
                m.NonConvexFlow.status[list(n.inputs.keys())[0], n, t]
                * n.coefficients[0][t]
            )
            return expr == 0

        self.relation = Constraint(
            self.OFFSETTRANSFORMERS, m.TIMESTEPS, rule=_relation_rule
        )
