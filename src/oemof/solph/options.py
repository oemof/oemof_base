# -*- coding: utf-8 -*-

"""Optional classes to be added to a network class.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Stephan Günther
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: jmloenneberga

SPDX-License-Identifier: MIT

"""

from oemof.solph.plumbing import sequence


class Investment:
    """
    Parameters
    ----------
    maximum : float, :math:`P_{invest,max}` or :math:`E_{invest,max}`
        Maximum of the additional invested capacity
    minimum : float, :math:`P_{invest,min}` or :math:`E_{invest,min}`
        Minimum of the additional invested capacity. If `nonconvex` is `True`,
        `minimum` defines the threshold for the invested capacity.
    ep_costs : float, :math:`c_{invest,var}`
        Equivalent periodical costs for the investment per flow capacity.
    other_needs : dict
    existing : float, :math:`P_{exist}` or :math:`E_{exist}`
        Existing / installed capacity. The invested capacity is added on top
        of this value. Not applicable if `nonconvex` is set to `True`.
    nonconvex : bool
        If `True`, a binary variable for the status of the investment is
        created. This enables additional fix investment costs (*offset*)
        independent of the invested flow capacity. Therefore, use the `offset`
        parameter.
    offset : float, :math:`c_{invest,fix}`
        Additional fix investment costs. Only applicable if `nonconvex` is set
        to `True`.


    For the variables, constraints and parts of the objective function, which
    are created, see :class:`oemof.solph.blocks.InvestmentFlow` and
    :class:`oemof.solph.components.GenericInvestmentStorageBlock`.

    """

    def __init__(
        self,
        maximum=float("+inf"),
        minimum=0,
        ep_costs=0,
        existing=0,
        nonconvex=False,
        offset=0,
        other_needs=None,
        **kwargs,
    ):

        self.maximum = maximum
        self.minimum = minimum
        self.ep_costs = ep_costs
        self.existing = existing
        self.nonconvex = nonconvex
        self.offset = offset
        if other_needs is not None:
            self.other_needs = other_needs
        else:
            self.other_needs = {}

        for attribute in kwargs.keys():
            value = kwargs.get(attribute)
            setattr(self, attribute, value)

        self._check_invest_attributes()
        self._check_invest_attributes_maximum()
        self._check_invest_attributes_offset()

    def _check_invest_attributes(self):
        if (self.existing != 0) and (self.nonconvex is True):
            e1 = (
                "Values for 'offset' and 'existing' are given in"
                " investement attributes. \n These two options cannot be "
                "considered at the same time."
            )
            raise AttributeError(e1)

    def _check_invest_attributes_maximum(self):
        if (self.maximum == float("+inf")) and (self.nonconvex is True):
            e2 = (
                "Please provide an maximum investment value in case of"
                " nonconvex investemnt (nonconvex=True), which is in the"
                " expected magnitude."
                " \nVery high maximum values (> 10e8) as maximum investment"
                " limit might lead to numeric issues, so that no investment"
                " is done, although it is the optimal solution!"
            )
            raise AttributeError(e2)

    def _check_invest_attributes_offset(self):
        if (self.offset != 0) and (self.nonconvex is False):
            e3 = (
                "If `nonconvex` is `False`, the `offset` parameter will be"
                " ignored."
            )
            raise AttributeError(e3)


class NonConvex:
    """
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
    """

    def __init__(self, **kwargs):
        scalars = [
            "minimum_uptime",
            "minimum_downtime",
            "initial_status",
            "maximum_startups",
            "maximum_shutdowns",
        ]
        sequences = ["startup_costs", "shutdown_costs", "activity_costs"]
        defaults = {"initial_status": 0}

        for attribute in set(scalars + sequences + list(kwargs)):
            value = kwargs.get(attribute, defaults.get(attribute))
            setattr(
                self,
                attribute,
                sequence(value) if attribute in sequences else value,
            )

        self._max_up_down = None

    def _calculate_max_up_down(self):
        """
        Calculate maximum of up and downtime for direct usage in constraints.

        The maximum of both is used to set the initial status for this
        number of timesteps within the edge regions.
        """
        if self.minimum_uptime is not None and self.minimum_downtime is None:
            max_up_down = self.minimum_uptime
        elif self.minimum_uptime is None and self.minimum_downtime is not None:
            max_up_down = self.minimum_downtime
        else:
            max_up_down = max(self.minimum_uptime, self.minimum_downtime)

        self._max_up_down = max_up_down

    @property
    def max_up_down(self):
        """Compute or return the _max_up_down attribute."""
        if self._max_up_down is None:
            self._calculate_max_up_down()

        return self._max_up_down
