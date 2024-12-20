# -*- coding: utf-8 -*-

"""
solph version of oemof.network.MultiInputMultiOutputConverter including
sets, variables, constraints and parts of the objective function
for MultiInputMultiOutputConverterBlock objects.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: Stephan Günther
SPDX-FileCopyrightText: Birgit Schachler
SPDX-FileCopyrightText: jnnr
SPDX-FileCopyrightText: jmloenneberga
SPDX-FileCopyrightText: David Fuhrländer
SPDX-FileCopyrightText: Johannes Röder
SPDX-FileCopyrightText: Johannes Kochems
SPDX-FileCopyrightText: Hendrik Huyskens <hendrik.huyskens@rl-institut.de>

SPDX-License-Identifier: MIT

"""

import operator
from functools import reduce
from typing import Dict
from typing import Iterable
from typing import Union

from oemof.network import Node
from pyomo.core import BuildAction
from pyomo.core import Constraint
from pyomo.core.base.block import ScalarBlock
from pyomo.environ import NonNegativeReals
from pyomo.environ import Set
from pyomo.environ import Var

from oemof.solph._helpers import warn_if_missing_attribute
from oemof.solph._plumbing import sequence
from oemof.solph.buses import Bus
from oemof.solph.flows import Flow

FLOW_SHARE_TYPES = ("min", "max", "fix")


class MultiInputMultiOutputConverter(Node):
    """A linear ConverterBlock object with n inputs and n outputs.

    Node object that relates any number of inflow and outflows with
    conversion factors. Inputs and outputs must be given as dictinaries.

    Parameters
    ----------
    inputs : dict
        Dictionary with inflows. Keys must be the starting node(s) of the
        inflow(s).
    outputs : dict
        Dictionary with outflows. Keys must be the ending node(s) of the
        outflow(s).
    conversion_factors : dict
        Dictionary containing conversion factors for conversion of each flow.
        Keys must be the connected nodes (typically Buses).
        The dictionary values can either be a scalar or an iterable with
        individual conversion factors for each time step.
        Default: 1. If no conversion_factor is given for an in- or outflow, the
        conversion_factor is set to 1.
    input_flow_shares : dict
        Dictionary containing flow shares which shall be hold within related
        input group. Keys must be connected input nodes (typically Buses).
        The dictionary values can either be a scalar or an iterable with
        individual flow shares for each time step. If no flow share is given
        for an input flow, no share is set for this flow.
    output_flow_shares : dict
        Dictionary containing flow shares which shall be hold within related
        input group. Keys must be connected input nodes (typically Buses).
        The dictionary values can either be a scalar or an iterable with
        individual flow shares for each time step. If no flow share is given
        for an input flow, no share is set for this flow.

    Examples
    --------
    Defining a MIMO-converter:

    >>> from oemof import solph
    >>> bgas = solph.buses.Bus(label='natural_gas')
    >>> bcoal = solph.buses.Bus(label='hard_coal')
    >>> bel = solph.buses.Bus(label='electricity')
    >>> bheat = solph.buses.Bus(label='heat')

    >>> trsf = solph.components.Converter(
    ...    label='pp_gas_1',
    ...    inputs={bgas: solph.flows.Flow(), bcoal: solph.flows.Flow()},
    ...    outputs={bel: solph.flows.Flow(), bheat: solph.flows.Flow()},
    ...    conversion_factors={bel: 0.3, bheat: 0.5,
    ...                        bgas: 0.8, bcoal: 0.2})
    >>> print(sorted([x[1][5] for x in trsf.conversion_factors.items()]))
    [0.2, 0.3, 0.5, 0.8]

    >>> type(trsf)
    <class 'oemof.solph.components._converter.Converter'>

    >>> sorted([str(i) for i in trsf.inputs])
    ['hard_coal', 'natural_gas']

    >>> trsf_new = solph.components.Converter(
    ...    label='pp_gas_2',
    ...    inputs={bgas: solph.flows.Flow()},
    ...    outputs={bel: solph.flows.Flow(), bheat: solph.flows.Flow()},
    ...    conversion_factors={bel: 0.3, bheat: 0.5})
    >>> trsf_new.conversion_factors[bgas][3]
    1

    Notes
    -----
    The following sets, variables, constraints and objective parts are created
     * :py:class:`~oemof.solph.components.experimental._mimo_converter.
     MultiInputMultiOutputConverterBlock`
    """

    def __init__(
        self,
        label=None,
        inputs=None,
        outputs=None,
        conversion_factors=None,
        input_flow_shares=None,
        output_flow_shares=None,
        custom_attributes=None,
    ):
        self.label = label

        if inputs is None:
            warn_if_missing_attribute(self, "inputs")
            inputs = {}
        if outputs is None:
            warn_if_missing_attribute(self, "outputs")
            outputs = {}
        self.input_groups = self._init_group_dict(inputs)
        self.output_groups = self._init_group_dict(outputs)

        if custom_attributes is None:
            custom_attributes = {}

        super().__init__(
            label=label,
            inputs=reduce(operator.ior, self.input_groups.values(), {}),
            outputs=reduce(operator.ior, self.output_groups.values(), {}),
            **custom_attributes,
        )

        self.conversion_factors = self._init_conversion_factors(
            conversion_factors
        )

        self._check_flow_shares(input_flow_shares)
        self._check_flow_shares(output_flow_shares)
        self.input_flow_shares = self._init_flow_shares(input_flow_shares)
        self.output_flow_shares = self._init_flow_shares(output_flow_shares)

    def _init_conversion_factors(
        self, conversion_factors: Dict[Bus, Union[float, Iterable]]
    ) -> Dict[Bus, Iterable]:
        """
        Set up the conversion_factors for each connected node.
        Parameters
        ----------
        conversion_factors : Dict[Bus, Union[float, Iterable]]
            Conversion factors set up by the user.

        Returns
        -------
        Dict[Bus, Iterable]
            Conversion factors for each connected node.
            Defaults to sequence(1).
        """
        if conversion_factors is None:
            conversion_factors = {}
        conversion_factors = {
            k: sequence(v) for k, v in conversion_factors.items()
        }
        missing_conversion_factor_keys = (
            set(self.outputs) | set(self.inputs)
        ) - set(conversion_factors)
        for cf in missing_conversion_factor_keys:
            conversion_factors[cf] = sequence(1)
        return conversion_factors

    @staticmethod
    def _check_flow_shares(flow_shares):
        if flow_shares is None:
            return

        # Check for invalid share types
        invalid_flow_share_types = set(flow_shares) - set(FLOW_SHARE_TYPES)
        if invalid_flow_share_types:
            raise ValueError(
                f"Invalid flow share types found: {invalid_flow_share_types}. "
                "Must be one of 'min', 'max' or 'fix'."
            )

        # Check if fix flow share is combined with min or max flow share
        if "fix" in flow_shares:
            for node in flow_shares["fix"]:
                if "min" in flow_shares and node in flow_shares["min"]:
                    raise ValueError(
                        "Cannot combine 'fix' and 'min' flow share for same "
                        "node."
                    )
                if "max" in flow_shares and node in flow_shares["max"]:
                    raise ValueError(
                        "Cannot combine 'fix' and 'max' flow share for same "
                        "node."
                    )

    @staticmethod
    def _init_flow_shares(
        flow_shares: Dict[str, Dict[Bus, Union[float, Iterable]]]
    ) -> Dict[str, Dict[Bus, Iterable]]:
        """
        Init minimum, maximum and fix flow shares. Set up empty dict, if flow
        shares are not set. For each given flow share, turn value into sequence
        if necessary.

        Parameters
        ----------
        flow_shares : Dict[str, Dict[Bus, Union[float, Iterable]]]
            flow shares set up by the user.

        Returns
        -------
        Dict[str, Dict[Bus, Iterable]]
            Flow shares as sequences
        """
        if flow_shares is None:
            return {}

        # Turn flow shares into sequences
        return {
            share_type: {
                node: sequence(value) for node, value in shares.items()
            }
            for share_type, shares in flow_shares.items()
        }

    @staticmethod
    def _init_group_dict(
        flows: Union[Dict[Bus, Flow], Dict[str, Dict[Bus, Flow]]]
    ) -> Dict[str, Dict[Bus, Flow]]:
        """
        Group all inputs and outputs if they are not grouped yet.

        Single bus-flow entities are grouped into a single group thereby.

        Parameters
        ----------
        flows
            Input or output flows. This can be one of:
            1. a dict of groups, containing buses with related flows
            2. a dict of buses and related flows (as in default converter)
            3. a mix of option 1 and 2

        Returns
        -------
        dict
            Grouped input or output flows (as in option 1)
        """
        group_dict = {}
        group_counter = 0
        for key, flow in flows.items():
            if isinstance(key, Bus):
                new_group = f"group_{group_counter}"
                group_dict[new_group] = {key: flow}
                group_counter += 1
            else:
                group_dict[key] = flow
        return group_dict

    @staticmethod
    def constraint_group():
        return MultiInputMultiOutputConverterBlock


class MultiInputMultiOutputConverterBlock(ScalarBlock):
    r"""Block for the linear relation of nodes with type
    :class:`~oemof.solph.components._converter.ConverterBlock`

    **The following sets are created:** (-> see basic sets at
    :class:`.Model` )

    CONVERTERS
        A set with all
        :class:`~oemof.solph.components._converter.Converter` objects.

    **The following constraints are created:**

    Linear relation :attr:`om.ConverterBlock.relation[i,o,t]`
        .. math::
            P_{i}(p, t) \cdot \eta_{o}(t) =
            P_{o}(p, t) \cdot \eta_{i}(t), \\
            \forall p, t \in \textrm{TIMEINDEX}, \\
            \forall n \in \textrm{CONVERTERS}, \\
            \forall i \in \textrm{INPUTS}, \\
            \forall o \in \textrm{OUTPUTS}

    While INPUTS is the set of Bus objects connected with the input of the
    Transformer and OUPUTS the set of Bus objects connected with the output of
    the Transformer. The constraint above will be created for all combinations
    of INPUTS and OUTPUTS for all TIMESTEPS. A Transformer with two inflows and
    two outflows for one day with an hourly resolution will lead to 96
    constraints.

    The index :math: n is the index for the Transformer node itself. Therefore,
    a `flow[i, n, p, t]` is a flow from the Bus i to the Transformer n at
    time index p, t.

    ======================  ============================  ====================
    symbol                  attribute                     explanation
    ======================  ============================  ====================
    :math:`P_{i,n}(p, t)`   `flow[i, n, p, t]`            Converter, inflow

    :math:`P_{n,o}(p, t)`   `flow[n, o, p, t]`            Converter, outflow

    :math:`\eta_{i}(t)`     `conversion_factor[i, n, t]`  Inflow, efficiency

    :math:`\eta_{o}(t)`     `conversion_factor[n, o, t]`  Outflow, efficiency

    ======================  ============================  ====================

    """

    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """Creates the linear constraint for the class:`ConverterBlock`
        block.

        Parameters
        ----------

        group : list
            List of oemof.solph.components.Converters objects for which
            the linear relation of inputs and outputs is created
            e.g. group = [trsf1, trsf2, trsf3, ...]. Note that the relation
            is created for all existing relations of all inputs and all outputs
            of the converter. The components inside the list need to hold
            an attribute `conversion_factors` of type dict containing the
            conversion factors for all inputs to outputs.
        """
        if group is None:
            return None

        m = self.parent_block()

        self.INPUT_GROUPS = Set(
            initialize=[(n, g) for n in group for g in n.input_groups], dimen=2
        )
        self.OUTPUT_GROUPS = Set(
            initialize=[(n, g) for n in group for g in n.output_groups],
            dimen=2,
        )

        self.INPUT_GROUP_FLOW = Var(
            self.INPUT_GROUPS,
            m.TIMEINDEX,
            within=NonNegativeReals,
        )
        self.OUTPUT_GROUP_FLOW = Var(
            self.OUTPUT_GROUPS, m.TIMEINDEX, within=NonNegativeReals
        )

        def _input_group_relation(block, n, g, p, t):
            lhs = sum(
                m.flow[i, n, p, t] / n.conversion_factors[i][t]
                for i in n.input_groups[g]
            )
            rhs = block.INPUT_GROUP_FLOW[n, g, p, t]
            return lhs == rhs

        self.input_relation = Constraint(
            [
                (n, g, p, t)
                for p, t in m.TIMEINDEX
                for n in group
                for g in n.input_groups
            ],
            rule=_input_group_relation,
        )

        def _output_group_relation(block, n, g, p, t):
            lhs = block.OUTPUT_GROUP_FLOW[n, g, p, t]
            rhs = sum(
                m.flow[n, o, p, t] / n.conversion_factors[o][t]
                for o in n.output_groups[g]
            )
            return lhs == rhs

        self.output_relation = Constraint(
            [
                (n, g, p, t)
                for p, t in m.TIMEINDEX
                for n in group
                for g in n.output_groups
            ],
            rule=_output_group_relation,
        )

        self.input_output_group_relation = Constraint(
            [
                (n, g, p, t)
                for p, t in m.TIMEINDEX
                for n in group
                for g in list(n.input_groups) + list(n.output_groups)
            ],
            noruleinit=True,
        )

        def _input_output_group_relation(block):
            for p, t in m.TIMEINDEX:
                for n in group:
                    # Connect input groups
                    for i, ii in zip(
                        list(n.input_groups)[:-1], list(n.input_groups)[1:]
                    ):
                        block.input_output_group_relation.add(
                            (n, i, p, t),
                            (
                                block.INPUT_GROUP_FLOW[n, i, p, t]
                                == block.INPUT_GROUP_FLOW[n, ii, p, t]
                            ),
                        )
                    # Connect output groups
                    for o, oo in zip(
                        list(n.output_groups)[:-1], list(n.output_groups)[1:]
                    ):
                        block.input_output_group_relation.add(
                            (n, o, p, t),
                            (
                                block.OUTPUT_GROUP_FLOW[n, o, p, t]
                                == block.OUTPUT_GROUP_FLOW[n, oo, p, t]
                            ),
                        )
                    # Connect input with output group:
                    # Use last input item as index
                    last_input = list(n.input_groups)[-1]
                    last_output = list(n.output_groups)[-1]
                    block.input_output_group_relation.add(
                        (n, last_input, p, t),
                        (
                            block.INPUT_GROUP_FLOW[n, last_input, p, t]
                            == block.OUTPUT_GROUP_FLOW[n, last_output, p, t]
                        ),
                    )

        self.input_output_group_relation_build = BuildAction(
            rule=_input_output_group_relation
        )

        def _get_operator_from_flow_share_type(flow_share_type):
            if flow_share_type == "min":
                return operator.gt
            if flow_share_type == "max":
                return operator.lt
            if flow_share_type == "fix":
                return operator.eq
            raise ValueError(f"Unknown flow share type: {flow_share_type}")

        self.input_flow_share_relation = Constraint(
            [
                (n, g, s, p, t)
                for p, t in m.TIMEINDEX
                for n in group
                for g in n.input_groups
                for s in FLOW_SHARE_TYPES
            ],
            noruleinit=True,
        )

        def _input_flow_share_relation(block):
            for p, t in m.TIMEINDEX:
                for n in group:
                    for flow_share_type, shares in n.input_flow_shares.items():
                        op = _get_operator_from_flow_share_type(
                            flow_share_type
                        )
                        for i, flow_share in shares.items():
                            # Find related input group for given input node:
                            g = next(
                                g
                                for g, inputs in n.input_groups.items()
                                if i in inputs
                            )
                            lhs = (
                                m.flow[i, n, p, t] / n.conversion_factors[i][t]
                            )
                            rhs = (
                                block.INPUT_GROUP_FLOW[n, g, p, t]
                                * flow_share[t]
                            )
                            block.input_flow_share_relation.add(
                                (n, g, flow_share_type, p, t),
                                op(lhs, rhs),
                            )

        self.input_flow_share_relation_build = BuildAction(
            rule=_input_flow_share_relation
        )

        self.output_flow_share_relation = Constraint(
            [
                (n, g, p, t)
                for p, t in m.TIMEINDEX
                for n in group
                for g in n.output_groups
                for s in FLOW_SHARE_TYPES
            ],
            noruleinit=True,
        )

        def _output_flow_share_relation(block):
            for p, t in m.TIMEINDEX:
                for n in group:
                    for (
                        flow_share_type,
                        shares,
                    ) in n.output_flow_shares.items():
                        op = _get_operator_from_flow_share_type(
                            flow_share_type
                        )
                        for o, flow_share in shares.items():
                            # Find related output group for given input node:
                            g = next(
                                g
                                for g, outputs in n.output_groups.items()
                                if o in outputs
                            )
                            lhs = (
                                m.flow[n, o, p, t] / n.conversion_factors[o][t]
                            )
                            rhs = (
                                block.OUTPUT_GROUP_FLOW[n, g, p, t]
                                * flow_share[t]
                            )
                            block.input_flow_share_relation.add(
                                (n, g, flow_share_type, p, t), op(lhs, rhs)
                            )

        self.output_flow_share_relation_build = BuildAction(
            rule=_output_flow_share_relation
        )
