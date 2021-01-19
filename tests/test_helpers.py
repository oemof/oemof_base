# -*- coding: utf-8 -*-

"""This module is designed to test the helper functions..

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT

"""

import os

from oemof.solph import helpers


def test_creation_of_extended_path():
    """Creation of a sub-folder based on the base path failed."""
    p = helpers.extend_basic_path("test_subfolder_X345qw34_tmp")
    assert os.path.isdir(p)
    os.rmdir(p)
