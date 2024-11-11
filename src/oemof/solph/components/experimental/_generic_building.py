# -*- coding: utf-8 -*-

"""
solph version of oemof.network.GenericBuilding including
sets, variables, constraints and parts of the objective function
for GenericBuildingBlock objects.

SPDX-FileCopyrightText: Maximilian Hillen <maximilian.hillen@dlr.de>
SPDX-FileCopyrightText: Patrik Schönfeldt

SPDX-License-Identifier: MIT

"""
from typing import List
from oemof.network import network
from oemof.solph._helpers import check_node_object_for_missing_attribute
from pyomo.core.base.block import ScalarBlock
from pyomo.environ import Constraint
from pyomo.environ import Set
from pyomo.environ import Var


class GenericBuilding(network.Node):
    r"""
    Component `GenericBuilding` to model with basic characteristics of buildings.
    A 5RC-model is chosen to abstract buildings as a one zone model and make them linear-optimizable.

    The full explanation of the 5RC building model can be found in ISO 13790:2008
    “Energy performance of buildings –Calculation of energy use for space heating and cooling“.
    Specific variables and calculation will be linked to chapters in the norm.

    In addition, the repository “RC_BuildingSimulator” from Jayathissa Prageeth
    (https://github.com/architecture-building-systems/RC_BuildingSimulator) is used.
    For further information we refer to: Jayathissa, Prageeth, et al.
    "Optimising building net energy demand with dynamic BIPV shading." Applied Energy 202 (2017): 726-735.

    The GenericBuilding is designed for one input and one output.

    Parameters
    ----------
    internal_gains : list
        List with sum of internal gains in Watts produces by residents and electrical devices in the building.
    building_config : dict
        Dictionary with mandatory building information. building_config can be generated with tabula data base.
    t_set_heating : numeric
        Value which describes the minimal permissible air temperature in Celsius in the building.
    t_set_cooling : list of numerical values
        Value which describes the maximum permissible  air temperature in Celsius in the building.
    t_e : list
        List of the ambient temperature in Celsius.
    t_inital : numeric
        Value of the initial/starting air temperature in Celsius inside the building.
    t_m : numeric
        Value of the initial/starting t_m temperature in Celsius inside the building. More information in Block.
    t_m_ts : numeric
        Value of the initial/starting air temperature in Celsius inside the building. More information in Block.
    phi_m_tot : numeric
        Value of the initial/starting air temperature in Celsius inside the building. : see formula for the calculation,
        eq C.5 in standard.

    Notes
    -----
    The following sets, variables, constraints and objective parts are created
     * :py:class:`~oemof.solph.components._generic_storage.GenericBuildingBlock`
       (if no Investment object present)

    Examples
    --------

    """  # noqa: E501

    def __init__(
        self,
        building_config,
        label: str,
        t_outside: List,
        solar_gains: List,
        internal_gains: List,
        inputs=None,
        outputs=None,
        phi_m_tot: float = 0,
        t_set_heating: float = 20,
        t_set_cooling: float = 40,
        t_inital: float = 20,
        t_m: float = 20,
        t_m_ts: float = 20,
    ):
        if inputs is None:
            inputs = {}
        if outputs is None:
            outputs = {}
        super().__init__(label=label, inputs=inputs, outputs=outputs)

        self.building_config = building_config
        self.t_e = t_outside
        self.internal_gains = internal_gains
        self.phi_m_tot = phi_m_tot
        self.solar_gains = solar_gains
        self.t_set_heating = t_set_heating
        self.t_set_cooling = t_set_cooling
        self.t_inital = t_inital
        self.t_m = t_m
        self.t_m_ts = t_m_ts

        self.floor_area = self.building_config.floor_area  # [m2] Floor Area
        self.mass_area = (
            self.building_config.mass_area
        )  # [m2] Effective Mass Area DIN 12.3.1.2
        self.A_t = (
            self.building_config.total_internal_area
        )  # [m2] the area of all surfaces facing the room DIN 7.2.2.2
        self.c_m = self.building_config.c_m  # [kWh/K] Room Capacitance
        self.ach_tot = (
            self.building_config.total_air_change_rate
        )  # [m3/s]Total Air Changes Per Hour

        self.h_tr_em = (
            self.building_config.h_tr_em
        )  # [W/K] Conductance of opaque surfaces to exterior
        self.h_tr_w = (
            self.building_config.h_tr_w
        )  # [W/K] Conductance to exterior through glazed surfaces
        self.h_ve = (
            self.building_config.h_ve
        )  # [W/K] Conductance to ventilation
        self.h_tr_ms = (
            self.building_config.h_tr_ms
        )  # [W/K] transmittance from the internal air to the thermal mass
        self.h_tr_is = (
            self.building_config.h_tr_is
        )  # [W/K] Conductance from the conditioned air to interior zone surface

        self.phi_st = (
            []
        )  # [W] Combination of internal and solar gains directly to the internal surfa
        self.phi_m = (
            []
        )  # [W] Combination of internal and solar gains directly to the medium
        self.phi_ia = (
            []
        )  # [W] Combination of internal and solar gains to the air
        for i in range(len(self.solar_gains)):
            self.h_tr_1 = (
                self.calc_h_tr_1()
            )  # [W/K] combined heat conductance, see function for definition
            self.h_tr_2 = (
                self.calc_h_tr_2()
            )  # [W/K] combined heat conductance, see function for definition
            self.h_tr_3 = (
                self.calc_h_tr_3()
            )  # [W/K] combined heat conductance, see function for definition
            self.phi_ia.append(self.calc_phi_ia(i))
            self.phi_st.append(self.calc_phi_st(i))
            self.phi_m.append(self.calc_phi_m(i))

    def calc_h_tr_1(self):
        """
        Definition to simplify calc_phi_m_tot
        (C.6) in [C.3 ISO 13790]
        """
        return 1.0 / (1.0 / self.h_ve + 1.0 / self.h_tr_is)

    def calc_h_tr_2(self):
        """
        Definition to simplify calc_phi_m_tot
        (C.7) in [C.3 ISO 13790]
        """
        return self.h_tr_1 + self.h_tr_w

    def calc_h_tr_3(self):
        """
        Definition to simplify calc_phi_m_tot
        (C.8) in [C.3 ISO 13790]
        """
        return 1.0 / (1.0 / self.h_tr_2 + 1.0 / self.h_tr_ms)

    def calc_phi_ia(self, i: float):
        """
        Heat flow in [W] to the air node
        (based on the breakdown in section C.2) formulas C.1-C.3 in [ISO 13790]
        """
        return 0.5 * self.internal_gains[i]

    def calc_phi_st(self, i: float):
        """
        Heat flow in [W] to the surface node
        (based on the breakdown in section C.2) formulas C.1-C.3 in [ISO 13790]
        """
        return (
            1 - (self.mass_area / self.A_t) - (self.h_tr_w / (9.1 * self.A_t))
        ) * (0.5 * self.internal_gains[i] + self.solar_gains[i])

    def calc_phi_m(self, i: float):
        """
        Heatflow in [W] to the thermal mass node
        (based on the breakdown in section C.2) formulas C.1-C.3 in [ISO 13790]
        """
        return (self.mass_area / self.A_t) * (
            0.5 * self.internal_gains[i] + self.solar_gains[i]
        )

    def _check_number_of_flows(self):
        """Ensure that there is only one inflow and outflow to the building"""
        msg = "Only one {0} flow allowed in the GenericBuilding {1}."
        check_node_object_for_missing_attribute(self, "inputs")
        check_node_object_for_missing_attribute(self, "outputs")
        if len(self.inputs) > 1:
            raise AttributeError(msg.format("input", self.label))
        if len(self.outputs) > 1:
            raise AttributeError(msg.format("output", self.label))

    def constraint_group(self):
        return GenericBuildingBlock


class GenericBuildingBlock(ScalarBlock):
    r"""GenericBuildingBlock without an :class:`.Investment` object.

    **The following sets are created:** (-> see basic sets at
    :class:`.Model` )

    BUILDING
        A set with all :py:class:`~.GenericBuilding` objects, which do not have an
        :attr:`investment` of type :class:`.Investment`.

    **The following variables are created:**

    t_air
        Internal building air temperature  for every storage and timestep.
        temperature at the beginning is set by the parameter `t_inital`.
        The variable of storage s and timestep t can be accessed by:
        `om.GenericBuildingBlock.t_air[s, t]`

    t_m_ts
        Temperature  of the knot, which represents the mass of
        the building zone. This temperature is calculated based on
        the value of the last timestep.
        The variable of storage s and timestep t can be accessed by:
        `om.GenericBuildingBlock.t_m_ts[s, t]`

    **The following constraints are created:**

    Building balance ts :attr:`om.Building.balance_rule_ts[n, t]`
        .. math:: \phi_{m\_tot}(t) = \phi_m(t) + h_{tr\_em} \cdot t_e(t) +
        \frac{h_{tr\_3}}{h_{tr\_2}} \cdot \left( \phi_{st}(t) +
        h_{tr\_w} \cdot t_e(t) + h_{tr\_1} \cdot
        \left( \frac{\phi_{ia}(t) +\phi_{i}(p, t) -
        \phi_{o}(p, t)}{h_{ve}} + t_e(t) \right) \right)

        .. math:: t_{m\_t} =  &t_{m\_t}(t-1) \cdot
        \left(\frac{c_m}{3600} - 0.5 \cdot
        (h_{tr\_3} + h_{tr\_em})\right) + \phi_{m\_tot}(t)}} \cdot
        {{\frac{c_m}{3600} + 0.5 \cdot (h_{tr\_3} + h_{tr\_em})}}

    Building balance t_air :attr:`om.Building.balance_rule_t_air[n, t]`
        :math::`t_s(t) = \frac{h_{tr\_ms} \cdot \frac{t_{m}(t-1) +
        t_{m}(t)}{2} + \phi_{st}(t) + h_{tr\_w} \cdot t_e(t) +
        h_{tr\_1} \cdot \left(t_e(t) + \frac{\phi_{ia}(t) +
        \phi_{hc\_nd}}{h_{ve}}\right)}{h_{tr\_ms} +
        h_{tr\_w} + h_{tr\_1}}

        :math: t_{air}(t) = \frac{h_{tr\_is} \cdot t_s(t) +
        h_{ve} \cdot t_e(t) + \phi_{ia}(t)] + \phi_{i}(p, t) -
        \phi_{o}(p, t)}{h_{tr\_is} + h_{ve}}


    =========================== ======================= =========
    symbol                      explanation             attribute
    =========================== ======================= =========
    :math:`t_{air}(t)`          internal temperature    `t_air`
    :math:`t_s(t)`              temperature knot s      `No attribute`
    :math:`t_{m}(t)`            temperature knot m      `t_m_ts`
    :math:`phi_{m\_tot}(t)`     temperature knot mtot   `No attribute`
    =========================== ======================= =========

    **The following parts of the objective function are created:**
    whereby:
    :math:`DF=(1+dr)` is the discount factor with discount rate :math:`dr`

    """  # noqa: E501
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        m = self.parent_block()
        if group is None:
            return None

        i = {n: [i for i in n.inputs][0] for n in group}

        o = {n: [o for o in n.outputs][0] for n in group}

        #  ************* SETS *********************************

        self.BUILDING = Set(initialize=[n for n in group])

        #  ************* VARIABLES *****************************

        def _internal_temperature_bound_rule(block, n, t):
            """
            Rule definition for bounds of internal_temperature/t_air variable of
            storage n in timestep t.
            """
            bounds = (
                n.t_set_heating,
                n.t_set_cooling,
            )
            return bounds

        self.t_air = Var(
            self.BUILDING,
            m.TIMEPOINTS,
            bounds=_internal_temperature_bound_rule,
        )
        self.t_m_ts = Var(self.BUILDING, m.TIMEPOINTS)

        self.phi_m_tot = Var(self.BUILDING, m.TIMEPOINTS)

        # set the initial building temperature
        # ToDo: More elegant code possible?
        for n in group:
            if n.t_inital is not None:
                self.t_air[n, 0] = n.t_inital
                self.t_air[n, 0].fix()

            if n.t_m_ts is not None:
                self.t_m_ts[n, 0] = n.t_inital
                self.t_m_ts[n, 0].fix()

            if n.phi_m_tot is not None:
                self.phi_m_tot[n, 0] = 0
                self.phi_m_tot[n, 0].fix()

        def _storage_balance_rule_tm(block, n, p, t):
            """
            Rule definition for the building temperature t_m
            of every storage n and every timestep.
            """
            t_m_last_ts = block.t_m_ts[n, t]
            phi_hc_heat = m.flow[i[n], n, p, t]
            phi_hc_cool = m.flow[n, o[n], p, t]
            phi_hc_nd = phi_hc_heat - phi_hc_cool

            phi_m_tot = (
                n.phi_m[t]
                + n.h_tr_em * n.t_e[t]
                + (n.h_tr_3 / n.h_tr_2)
                * (
                    n.phi_st[t]
                    + n.h_tr_w * n.t_e[t]
                    + n.h_tr_1
                    * (((n.phi_ia[t] + phi_hc_nd) / n.h_ve) + n.t_e[t])
                )
            )

            t_m_current_ts = (
                t_m_last_ts * ((n.c_m / 3600) - 0.5 * (n.h_tr_3 + n.h_tr_em))
                + phi_m_tot
            ) / ((n.c_m / 3600) + 0.5 * (n.h_tr_3 + n.h_tr_em))

            return block.t_m_ts[n, t + 1] == t_m_current_ts

        self.balance_t_m_current_t_s = Constraint(
            self.BUILDING, m.TIMEINDEX, rule=_storage_balance_rule_tm
        )

        def _storage_balance_rule_t_air(block, n, p, t):
            """
            Rule definition for the building temperature t_air
            of every storage n and every timestep.
            """
            phi_hc_heat = m.flow[i[n], n, p, t]
            phi_hc_cool = m.flow[n, o[n], p, t]
            phi_hc_nd = phi_hc_heat - phi_hc_cool
            t_m_last_ts = block.t_m_ts[n, t]
            t_m_current_ts = block.t_m_ts[n, t + 1]
            t_m = (t_m_last_ts + t_m_current_ts) / 2

            t_s = (
                n.h_tr_ms * t_m
                + n.phi_st[t]
                + n.h_tr_w * n.t_e[t]
                + n.h_tr_1 * (n.t_e[t] + (n.phi_ia[t] + phi_hc_nd) / n.h_ve)
            ) / (n.h_tr_ms + n.h_tr_w + n.h_tr_1)
            t_air = (
                n.h_tr_is * t_s + n.h_ve * n.t_e[t] + n.phi_ia[t] + phi_hc_nd
            ) / (n.h_tr_is + n.h_ve)
            return block.t_air[n, t + 1] == t_air

        self.balance_t_air = Constraint(
            self.BUILDING, m.TIMEINDEX, rule=_storage_balance_rule_t_air
        )

    def _objective_expression(self):
        r"""
        Objective expression for BUILDING with no investment.
        Note: This adds nothing as variable costs are already
        added in the Block :class:`SimpleFlowBlock`.
        """
        if not hasattr(self, "BUILDING"):
            return 0

        return 0
