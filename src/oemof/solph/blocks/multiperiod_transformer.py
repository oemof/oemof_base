# -*- coding: utf-8 -*-

"""Creating sets, variables, constraints and parts of the objective function
for Transformer objects.

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
from pyomo.core.base.block import SimpleBlock


class MultiPeriodTransformer(SimpleBlock):
    r"""Block for the linear relation of nodes with type
    :class:`~oemof.solph.network.Transformer` used if :attr:`multiperiod` or
    :attr:`multiperiodinvestment` is True

    **The following sets are created:** (-> see basic sets at
    :class:`.MultiPeriodModel` )

    TRANSFORMERS
        A set with all :class:`~oemof.solph.network.Transformer` objects.

    **The following constraints are created:**

    Linear relation :attr:`om.Transformer.relation[i,o,p, t]`
        .. math::
            \P_{i,n}(p, t) \times \eta_{n,o}(t) = \
            \P_{n,o}(p, t) \times \eta_{n,i}(t), \\
            \forall p, t \in \textrm{TIMEINDEX}, \\
            \forall n \in \textrm{TRANSFORMERS}, \\
            \forall i \in \textrm{INPUTS(n)}, \\
            \forall o \in \textrm{OUTPUTS(n)},

    ======================  ====================================  =============
    symbol                  attribute                             explanation
    ======================  ====================================  =============
    :math:`P_{i,n}(p, t)`      :py:obj:`flow[i, n, t]`            Transformer
                                                                  inflow

    :math:`P_{n,o}(p, t)`      :py:obj:`flow[n, o, t]`            Transformer
                                                                  outflow

    :math:`\eta_{i,n}(t)`   :py:obj:`conversion_factor[i, n, t]`  Conversion
                                                                  efficiency

    ======================  ====================================  =============
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
            [(n, i, o, p, t)
             for p, t in m.TIMEINDEX
             for n in group
             for o in out_flows[n]
             for i in in_flows[n]], noruleinit=True)

        def _input_output_relation(block):
            for p, t in m.TIMEINDEX:
                for n in group:
                    for o in out_flows[n]:
                        for i in in_flows[n]:
                            try:
                                lhs = (m.flow[i, n, p, t]
                                       * n.conversion_factors[o][t])
                                rhs = (m.flow[n, o, p, t]
                                       * n.conversion_factors[i][t])
                            except ValueError:
                                raise ValueError(
                                    "Error in constraint creation",
                                    "source: {0}, target: {1}".format(
                                        n.label, o.label))
                            block.relation.add((n, i, o, p, t), (lhs == rhs))

        self.relation_build = BuildAction(rule=_input_output_relation)
