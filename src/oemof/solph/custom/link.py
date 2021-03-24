# -*- coding: utf-8 -*-

"""
In-development component to add some intelligence
to connection between two Nodes.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: Johannes Röder
SPDX-FileCopyrightText: jakob-wo
SPDX-FileCopyrightText: gplssm
SPDX-FileCopyrightText: jnnr

SPDX-License-Identifier: MIT

"""

from oemof.network import network as on
from pyomo.core.base.block import SimpleBlock
from pyomo.core import Binary, Set, Var
from pyomo.environ import BuildAction
from pyomo.environ import Constraint

from oemof.solph.plumbing import sequence


class Link(on.Transformer):
    """A Link object with 1...2 inputs and 1...2 outputs.

    Parameters
    ----------
    conversion_factors : dict
        Dictionary containing conversion factors for conversion of each flow.
        Keys are the connected tuples (input, output) bus objects.
        The dictionary values can either be a scalar or an iterable with length
        of time horizon for simulation.

    Note: This component is experimental. Use it with care.

    Notes
    -----
    The sets, variables, constraints and objective parts are created
     * :py:class:`~oemof.solph.custom.link.LinkBlock`

    Examples
    --------

    >>> from oemof import solph
    >>> bel0 = solph.Bus(label="el0")
    >>> bel1 = solph.Bus(label="el1")

    >>> link = solph.custom.Link(
    ...    label="transshipment_link",
    ...    inputs={bel0: solph.Flow(nominal_value=4),
    ...            bel1: solph.Flow(nominal_value=2)},
    ...    outputs={bel0: solph.Flow(), bel1: solph.Flow()},
    ...    conversion_factors={(bel0, bel1): 0.8, (bel1, bel0): 0.9})
    >>> print(sorted([x[1][5] for x in link.conversion_factors.items()]))
    [0.92, 0.99]

    >>> type(link)
    <class 'oemof.solph.custom.link.Link'>

    >>> sorted([str(i) for i in link.inputs])
    ['el0', 'el1']

    >>> link.conversion_factors[(bel0, bel1)][3]
    0.8
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.conversion_factors = {
            k: sequence(v)
            for k, v in kwargs.get("conversion_factors", {}).items()
        }

        wrong_args_message = (
            "Component `Link` must have exactly"
            + "2 inputs, 2 outputs, and 2"
            + "conversion factors connecting these."
        )
        assert len(self.inputs) == 2, wrong_args_message
        assert len(self.outputs) == 2, wrong_args_message
        assert len(self.conversion_factors) == 2, wrong_args_message

    def constraint_group(self):
        return LinkBlock


class LinkBlock(SimpleBlock):
    r"""Block for the relation of nodes with type
    :class:`~oemof.solph.custom.Link`

    Note: This component is experimental. Use it with care.

    **The following constraints are created:**

    .. _Link-equations:

    .. math::
        &
        (1) \qquad P_{\mathrm{in},n}(t) = c_n(t) \times P_{\mathrm{out},n}(t)
            \quad \forall t \in T, \forall n in {1,2} \\
        &
        (2) \qquad 1 \ge \hat{S} + P_{\mathrm{in},1}(t)
                                 / P_{\mathrm{in},1,\mathrm{max}}
            \quad \forall t \in T \\
        &
        (3) \qquad 0 \le \hat{S} - P_{\mathrm{in},2}(t)
                                 / P_{2\mathrm{in},2,\mathrm{max}}
            \quad \forall t \in T \\
        &

    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """Creates the relation for the class:`Link`.

        Parameters
        ----------
        group : list
            List of oemof.solph.custom.Link objects for which
            the relation of inputs and outputs is createdBuildAction
            e.g. group = [link1, link2, link3, ...]. The components inside
            the list need to hold an attribute `conversion_factors` of type
            dict containing the conversion factors for all inputs to outputs.
        """
        if group is None:
            return None

        m = self.parent_block()

        all_conversions = {}
        for n in group:
            all_conversions[n] = {
                k: v for k, v in n.conversion_factors.items()
            }

        self.LINKS = Set(initialize=[g for g in group])
        self.LINK_1ST_INFLOWS = Set(
            initialize=[(list(c)[0][0], n)
                        for n, c in all_conversions.items()])
        self.LINK_2ND_INFLOWS = Set(
            initialize=[(list(c)[1][0], n)
                        for n, c in all_conversions.items()])

        #  0: Flows 1 connected; 1: Flows 2 connected
        self.direction = Var(self.LINKS, m.TIMESTEPS, within=Binary)

        def _input_output_relation(block):
            for t in m.TIMESTEPS:
                for n, conversion in all_conversions.items():
                    for cidx, c in conversion.items():
                        try:
                            expr = (
                                m.flow[n, cidx[1], t]
                                == c[t] * m.flow[cidx[0], n, t]
                            )
                        except ValueError:
                            raise ValueError(
                                "Error in constraint creation",
                                "from: {0}, to: {1}, via: {2}".format(
                                    cidx[0], cidx[1], n
                                ),
                            )
                        block.relation.add((n, cidx[0], cidx[1], t), (expr))

        self.relation = Constraint(
            [
                (n, cidx[0], cidx[1], t)
                for t in m.TIMESTEPS
                for n, conversion in all_conversions.items()
                for cidx, c in conversion.items()
            ],
            noruleinit=True,
        )
        self.relation_build = BuildAction(rule=_input_output_relation)

        def _flow1_rule(block, i, link, t):
            """Rule definition for Eq. (2)."""
            expr = (
                1 >= (self.direction[link, t]
                      + m.flow[i, link, t]
                      * m.flows[i, link].max[t]
                      * m.flows[i, link].nominal_value
                     )
            )
            return expr

        self.flow1 = Constraint(
            self.LINK_1ST_INFLOWS, m.TIMESTEPS, rule=_flow1_rule
        )

        def _flow2_rule(block, i, link, t):
            """Rule definition for Eq. (3)."""
            expr = (
                0 <= (self.direction[link, t]
                      - m.flow[i, link, t]
                      * m.flows[i, link].max[t]
                      * m.flows[i, link].nominal_value
                     )
            )
            return expr

        self.flow2 = Constraint(
            self.LINK_2ND_INFLOWS, m.TIMESTEPS, rule=_flow2_rule
        )
