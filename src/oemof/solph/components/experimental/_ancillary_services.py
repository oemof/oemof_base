# -*- coding: utf-8 -*-

"""
In-development component for ancillary services demand

SPDX-FileCopyrightText: Ekaterina Zolotarevskaia (e-zolotarevskaya)

SPDX-License-Identifier: MIT

"""
from oemof.solph.components._sink import Sink

class AncillaryServices(Sink):
    """
    request
    timeindex
    price
    """
    def __init__(self, request, timeindex, price):
        self.request = request
        self.timeindex = timeindex
        self.price = price


