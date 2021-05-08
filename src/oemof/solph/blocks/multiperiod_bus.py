# -*- coding: utf-8 -*-

"""Creating sets, variables, constraints and parts of the objective function
for Bus objects.

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


class MultiPeriodBus(SimpleBlock):
    r"""Block for all balanced MultiPeriodBuses.

    **The following constraints are build:**

    Bus balance  :attr:`om.Bus.balance[i, o, t]`
      .. math::
        \sum_{i \in INPUTS(n)} flow(i, n, p, t) =
        \sum_{o \in OUTPUTS(n)} flow(n, o, p, t), \\
        \forall n \in \textrm{MULTIPERIODBUSES},
        \forall p, t \in \textrm{TIMEINDEX}.
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

        ins = {}
        outs = {}
        for n in group:
            ins[n] = [i for i in n.inputs]
            outs[n] = [o for o in n.outputs]

        def _busbalance_rule(block):
            for p, t in m.TIMEINDEX:
                for g in group:
                    lhs = sum(m.flow[i, g, p, t] for i in ins[g])
                    rhs = sum(m.flow[g, o, p, t] for o in outs[g])
                    expr = (lhs == rhs)
                    # no inflows no outflows yield: 0 == 0 which is True
                    if expr is not True:
                        block.balance.add((g, p, t), expr)

        self.balance = Constraint(group, m.TIMEINDEX, noruleinit=True)
        self.balance_build = BuildAction(rule=_busbalance_rule)
