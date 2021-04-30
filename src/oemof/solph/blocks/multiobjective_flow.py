# -*- coding: utf-8 -*-

"""Creating sets, variables, constraints and parts of the objective function
for MultiObjectiveFlow objects.
"""

from collections import defaultdict

from pyomo.core import Set
from pyomo.core.base.block import SimpleBlock


class MultiObjectiveFlow(SimpleBlock):
    r""" Block for all flows with :attr:`multiobjective` being not None.

    Adds no additional variables or constraints. Used solely to add index set
    and objective expressions.

    **The following sets are created:** (-> see basic sets at :class:`.Model` )

    MULTIOBJECTIVEFLOWS
        A set of flows with the attribute :attr:`multiobjective` of type
        :class:`.options.MultiObjective`.

    **The following parts of the objective function are created:**

    If :attr:`variable_costs` are set by the user:
      .. math::
          \sum_{(i,o)} \sum_t flow(i, o, t) \cdot variable\_costs(e, i, o, t)

          \forall e \in \{set\ of\ objective\ functions\}

    Specific objectives are created in the same manner as for :class:`Flow`.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        r"""Creates sets, variables and constraints for all standard flows.

        Parameters
        ----------
        group : list
            List containing tuples containing flow (f) objects and the
            associated source (s) and target (t)
            of flow e.g. groups=[(s1, t1, f1), (s2, t2, f2),..]
        """
        if group is None:
            return None

        # ########################## SETS #################################
        self.MULTIOBJECTIVEFLOWS = Set(
            initialize=[(g[0], g[1]) for g in group])

    def _objective_expression(self):
        r"""Objective expression for all multiobjective flows with fixed costs
        and variable costs.
        """
        if not hasattr(self, "MULTIOBJECTIVEFLOWS"):
            return 0
        m = self.parent_block()

        mo_costs = defaultdict(lambda: 0, {'_standard': 0})

        for i, o in self.MULTIOBJECTIVEFLOWS:
            for mo_key, mo_param in m.flows[i, o].multiobjective.items():
                variable_costs = 0
                gradient_costs = 0
                if mo_param.variable_costs[0] is not None:
                    for t in m.TIMESTEPS:
                        variable_costs += (
                            m.flow[i, o, t]
                            * m.objective_weighting[t]
                            * mo_param.variable_costs[t])

                if mo_param.positive_gradient["ub"][0] is not None:
                    for t in m.TIMESTEPS:
                        gradient_costs += (
                            self.positive_gradient[i, o, t]
                            * mo_param.positive_gradient["costs"])

                if mo_param.negative_gradient["ub"][0] is not None:
                    for t in m.TIMESTEPS:
                        gradient_costs += (
                            self.negative_gradient[i, o, t]
                            * mo_param.negative_gradient["costs"])

                mo_costs[mo_key] += variable_costs + gradient_costs

        return mo_costs
