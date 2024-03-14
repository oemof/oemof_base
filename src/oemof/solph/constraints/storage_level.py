"""A constraint to allow flows from to a storage based on the storage level.

SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: Johannes Kochems
SPDX-FileCopyrightText: Deutsches Zentrum für Luft- und Raumfahrt (DLR)

SPDX-License-Identifier: MIT
"""

from pyomo import environ as po


def storage_level_constraint(
    model,
    name,
    storage_component,
    multiplexer_bus,
    input_levels,
    output_levels,
):
    r"""
    Add constraints to implement storage content based access.

    As a GenericStorage just allows exactly one input and one output,
    an additional bus, the multiplexer_bus, is used for the connections.
    Note that all Flow objects connected to the multiplexer_bus have to have
    a nominal_value.

    Parameters
    ----------
    model : oemof.solph.Model
        Model to which the constraint is added.
    name : string
        Name of the multiplexer.
    storage_component : oemof.solph.components.GenericStorage
        Storage component whose content should mandate
        the possible inputs and outputs.
    multiplexer_bus : oemof.solph.Bus
        Bus which connects the input and output levels to the storage.
    input_levels : dictionary with oemof.solph.Bus as keys and float as values
        Dictionary of buses which act as inputs and corresponding levels
    output_levels : dictionary with oemof.solph.Bus as keys and float as values
        Dictionary of buses which act as outputs and corresponding level

    Verbose description can be found in https://arxiv.org/abs/2211.14080
    """

    def _outputs():
        OUTPUTS = po.Set(initialize=output_levels.keys())
        setattr(model, f"{name}_OUTPUTS", OUTPUTS)

        active_output = po.Var(
            OUTPUTS, model.TIMESTEPS, domain=po.Binary, bounds=(0, 1)
        )
        setattr(model, f"{name}_active_output", active_output)

        constraint_name = f"{name}_output_active_constraint"

        def _output_active_rule(m):
            r"""
            .. math::
                y_n \le E(t) / E_n
            """
            for t in m.TIMESTEPS:
                for o in output_levels:
                    getattr(m, constraint_name).add(
                        (o, t),
                        m.GenericStorageBlock.storage_content[
                            storage_component, t + 1
                        ]
                        / storage_component.nominal_storage_capacity
                        >= active_output[o, t] * output_levels[o],
                    )

        setattr(
            model,
            constraint_name,
            po.Constraint(
                OUTPUTS,
                model.TIMESTEPS,
                noruleinit=True,
            ),
        )
        setattr(
            model,
            constraint_name + "build",
            po.BuildAction(rule=_output_active_rule),
        )

        # Define constraints on the output flows
        def _constraint_output_rule(m, o, p, t):
            return (
                m.flow[multiplexer_bus, o, p, t]
                / m.flows[multiplexer_bus, o].nominal_value
                <= active_output[o, t]
            )

        setattr(
            model,
            f"{name}_output_constraint",
            po.Constraint(
                OUTPUTS,
                model.TIMEINDEX,
                rule=_constraint_output_rule,
            ),
        )

    def _outputs_tsam():
        OUTPUTS = po.Set(initialize=output_levels.keys())
        setattr(model, f"{name}_OUTPUTS", OUTPUTS)

        active_output = po.Var(
            OUTPUTS, model.TIMEINDEX_TYPICAL_CLUSTER_OFFSET, domain=po.Binary, bounds=(0, 1)
        )
        setattr(model, f"{name}_active_output", active_output)

        constraint_name = f"{name}_output_active_constraint"

        def _output_active_rule(m):
            r"""
            .. math::
                y_n \le E(t) / E_n
            """
            for p, k, g in m.TIMEINDEX_TYPICAL_CLUSTER:
                t = m.get_timestep_from_tsam_timestep(p, k, g)
                for o in output_levels:
                    getattr(m, constraint_name).add(
                        (o, p, k, g),
                        m.GenericStorageBlock.storage_content_intra[
                            storage_component,  p, k, g + 1
                        ]
                        / storage_component.nominal_storage_capacity
                        >= active_output[o, p, k, g] * output_levels[o],
                    )

        setattr(
            model,
            constraint_name,
            po.Constraint(
                OUTPUTS,
                model.TIMEINDEX_TYPICAL_CLUSTER,
                noruleinit=True,
            ),
        )
        setattr(
            model,
            constraint_name + "build",
            po.BuildAction(rule=_output_active_rule),
        )

        # Define constraints on the output flows
        def _constraint_output_rule(m, o, p, k, g):
            t = m.get_timestep_from_tsam_timestep(p, k, g)
            return (
                m.flow[multiplexer_bus, o, p, t]
                / m.flows[multiplexer_bus, o].nominal_value
                <= active_output[o, p, k, g]
            )

        setattr(
            model,
            f"{name}_output_constraint",
            po.Constraint(
                OUTPUTS,
                model.TIMEINDEX_TYPICAL_CLUSTER,
                rule=_constraint_output_rule,
            ),
        )

    if not model.TSAM_MODE:
        _outputs()
    else:
        _outputs_tsam()

    def _inputs():
        INPUTS = po.Set(initialize=input_levels.keys())
        setattr(model, f"{name}_INPUTS", INPUTS)

        inactive_input = po.Var(
            INPUTS, model.TIMESTEPS, domain=po.Binary, bounds=(0, 1)
        )
        setattr(model, f"{name}_active_input", inactive_input)

        constraint_name = f"{name}_input_active_constraint"

        def _input_active_rule(m):
            r"""
            .. math::
                \hat{y}_n \ge (E(t) - E_n) / E_{max}
            """
            for t in m.TIMESTEPS:
                for i in input_levels:
                    getattr(m, constraint_name).add(
                        (i, t),
                        (
                            m.GenericStorageBlock.storage_content[
                                storage_component, t
                            ]
                            / storage_component.nominal_storage_capacity
                            - input_levels[i]
                        )
                        <= inactive_input[i, t],
                    )

        setattr(
            model,
            constraint_name,
            po.Constraint(
                INPUTS,
                model.TIMESTEPS,
                noruleinit=True,
            ),
        )
        setattr(
            model,
            constraint_name + "build",
            po.BuildAction(rule=_input_active_rule),
        )

        # Define constraints on the input flows
        def _constraint_input_rule(m, i, p, t):
            return (
                m.flow[i, multiplexer_bus, p, t]
                / m.flows[i, multiplexer_bus].nominal_value
                <= 1 - inactive_input[i, t]
            )

        setattr(
            model,
            f"{name}_input_constraint",
            po.Constraint(
                INPUTS,
                model.TIMEINDEX,
                rule=_constraint_input_rule,
            ),
        )

    def _inputs_tsam():
        INPUTS = po.Set(initialize=input_levels.keys())
        setattr(model, f"{name}_INPUTS", INPUTS)

        inactive_input = po.Var(
            INPUTS, model.TIMEINDEX_TYPICAL_CLUSTER_OFFSET, domain=po.Binary, bounds=(0, 1)
        )
        setattr(model, f"{name}_active_input", inactive_input)

        constraint_name = f"{name}_input_active_constraint"

        def _input_active_rule(m):
            r"""
            .. math::
                \hat{y}_n \ge (E(t) - E_n) / E_{max}
            """
            for p, k, g in m.TIMEINDEX_TYPICAL_CLUSTER:
                t = m.get_timestep_from_tsam_timestep(p, k, g)
                for i in input_levels:
                    getattr(m, constraint_name).add(
                        (i, p, k, g),
                        (
                            m.GenericStorageBlock.storage_content_intra[
                                storage_component, p, k, g + 1
                            ]
                            / storage_component.nominal_storage_capacity
                            - input_levels[i]
                        )
                        <= inactive_input[i, p, k, g],
                    )

        setattr(
            model,
            constraint_name,
            po.Constraint(
                INPUTS,
                model.TIMEINDEX_TYPICAL_CLUSTER,
                noruleinit=True,
            ),
        )
        setattr(
            model,
            constraint_name + "build",
            po.BuildAction(rule=_input_active_rule),
        )

        # Define constraints on the input flows
        def _constraint_input_rule(m, i, p, k, g):
            t = m.get_timestep_from_tsam_timestep(p, k, g)
            return (
                m.flow[i, multiplexer_bus, p, t]
                / m.flows[i, multiplexer_bus].nominal_value
                <= 1 - inactive_input[i, p, k, g]
            )

        setattr(
            model,
            f"{name}_input_constraint",
            po.Constraint(
                INPUTS,
                model.TIMEINDEX_TYPICAL_CLUSTER,
                rule=_constraint_input_rule,
            ),
        )

    if not model.TSAM_MODE:
        _inputs()
    else:
        _inputs_tsam()
