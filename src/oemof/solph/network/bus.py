# -*- coding: utf-8 -*-

"""
solph version of oemof.network.bus

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Stephan Günther
SPDX-FileCopyrightText: Birgit Schachler

SPDX-License-Identifier: MIT

"""

from oemof.network import network as on

from oemof.solph import blocks


class Bus(on.Bus):
    """A balance object. Every node has to be connected to Bus.

    If a MultiPeriodModel is created, :attr:`multiperiod`
    has to be set to True.

    Notes
    -----
    The following sets, variables, constraints and objective parts are created
     * :py:class:`~oemof.solph.blocks.bus.Bus`
     * :py:class:`~oemof.solph.blocks.MultiPeriodBus` for a MultiPeriodModel

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.balanced = kwargs.get("balanced", True)
        self.multiperiod = kwargs.get("multiperiod", False)

    def constraint_group(self):
        if self.balanced and not self.multiperiod:
            return blocks.Bus
        if self.balanced and self.multiperiod:
            return blocks.MultiPeriodBus
        else:
            return None
