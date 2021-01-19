# -*- coding: utf-8 -*-

"""
This is a collection of helper functions which work on their own and can be
used by various classes. If there are too many helper-functions, they will
be sorted in different modules.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Caroline Möller
SPDX-FileCopyrightText: henhuy
SPDX-FileCopyrightText: gplssm
SPDX-FileCopyrightText: Stephan Günther
SPDX-FileCopyrightText: elisapap

SPDX-License-Identifier: MIT

"""

import datetime as dt
import os
from collections import MutableMapping

import pandas as pd


def get_basic_path():
    """Returns the basic oemof path and creates it if necessary.
    The basic path is the '.oemof' folder in the $HOME directory.
    """
    basicpath = os.path.join(os.path.expanduser('~'), '.oemof')
    if not os.path.isdir(basicpath):
        os.mkdir(basicpath)
    return basicpath


def extend_basic_path(subfolder):
    """Returns a path based on the basic oemof path and creates it if
     necessary. The subfolder is the name of the path extension.
    """
    extended_path = os.path.join(get_basic_path(), subfolder)
    if not os.path.isdir(extended_path):
        os.mkdir(extended_path)
    return extended_path


def flatten(d, parent_key='', sep='_'):
    """
    Flatten dictionary by compressing keys.

    See: https://stackoverflow.com/questions/6027558/
         flatten-nested-python-dictionaries-compressing-keys

    d : dictionary
    sep : separator for flattening keys

    Returns
    -------
    dict
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + str(k) if parent_key else str(k)
        if isinstance(v, MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def calculate_timeincrement(timeindex, fill_value=None):
    """
    Calculates timeincrement for `timeindex`

    Parameters
    ----------
    timeindex: pd.DatetimeIndex
        timeindex of energysystem
    fill_value: numerical
        timeincrement for first timestep in hours
    """
    if isinstance(timeindex, pd.DatetimeIndex) and \
        (fill_value and isinstance(fill_value, pd.Timedelta) or
         fill_value is None):
        if len(set(timeindex)) != len(timeindex):
            raise IndexError("No equal DatetimeIndex allowed!")
        timeindex = timeindex.to_series()
        timeindex_sorted = timeindex.sort_values()
        if fill_value:
            timeincrement = timeindex_sorted.diff().fillna(value=fill_value)
        else:
            timeincrement = timeindex_sorted.diff().fillna(method='bfill')
        timeincrement_sec = timeincrement.map(dt.timedelta.total_seconds)
        timeincrement_hourly = list(timeincrement_sec.map(
                                    lambda x: x/3600))
        timeincrement = timeincrement_hourly
        return timeincrement
    else:
        raise AttributeError(
            "'timeindex' must be of type 'DatetimeIndex' and " +
            "'fill_value' of type 'Timedelta'.")
