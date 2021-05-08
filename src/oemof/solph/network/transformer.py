# -*- coding: utf-8 -*-

"""
solph version of oemof.network.Transformer

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: Stephan Günther
SPDX-FileCopyrightText: Birgit Schachler

SPDX-License-Identifier: MIT

"""

from oemof.network import network as on

from oemof.solph import blocks
from oemof.solph.plumbing import sequence

from ._helpers import check_node_object_for_missing_attribute


class Transformer(on.Transformer):
    """A linear Transformer object with n inputs and n outputs.

    For a MultiPeriodModel, the Flow output(s) should either have a
    boolean attribute :attr:`multiperiod`, to indicate a transformer used in
    the dispatch mode, or an attribute :attr:`multiperiodinvestment` of type
    :class:`MultiPeriodInvestment <oemof.solph.options.MultiPeriodInvestment>`
    for a transformer that will be invested in.

    Parameters
    ----------
    conversion_factors : dict
        Dictionary containing conversion factors for conversion of each flow.
        Keys are the connected bus objects.
        The dictionary values can either be a scalar or an iterable with length
        of time horizon for simulation.

    Examples
    --------
    Defining an linear transformer:

    >>> from oemof import solph
    >>> bgas = solph.Bus(label='natural_gas')
    >>> bcoal = solph.Bus(label='hard_coal')
    >>> bel = solph.Bus(label='electricity')
    >>> bheat = solph.Bus(label='heat')

    >>> trsf = solph.Transformer(
    ...    label='pp_gas_1',
    ...    inputs={bgas: solph.Flow(), bcoal: solph.Flow()},
    ...    outputs={bel: solph.Flow(), bheat: solph.Flow()},
    ...    conversion_factors={bel: 0.3, bheat: 0.5,
    ...                        bgas: 0.8, bcoal: 0.2})
    >>> print(sorted([x[1][5] for x in trsf.conversion_factors.items()]))
    [0.2, 0.3, 0.5, 0.8]

    >>> type(trsf)
    <class 'oemof.solph.network.transformer.Transformer'>

    >>> sorted([str(i) for i in trsf.inputs])
    ['hard_coal', 'natural_gas']

    >>> trsf_new = solph.Transformer(
    ...    label='pp_gas_2',
    ...    inputs={bgas: solph.Flow()},
    ...    outputs={bel: solph.Flow(), bheat: solph.Flow()},
    ...    conversion_factors={bel: 0.3, bheat: 0.5})
    >>> trsf_new.conversion_factors[bgas][3]
    1

    Notes
    -----
    The following sets, variables, constraints and objective parts are created
     * :py:class:`~oemof.solph.blocks.transformer.Transformer`
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        check_node_object_for_missing_attribute(self, "inputs")
        check_node_object_for_missing_attribute(self, "outputs")

        self.conversion_factors = {
            k: sequence(v)
            for k, v in kwargs.get("conversion_factors", {}).items()
        }

        missing_conversion_factor_keys = (
            set(self.outputs) | set(self.inputs)
        ) - set(self.conversion_factors)

        for cf in missing_conversion_factor_keys:
            self.conversion_factors[cf] = sequence(1)

        # Check outputs for multiperiod modeling
        for v in self.outputs.values():
            if (hasattr(v, 'multiperiod')
                    or hasattr(v, 'multiperiodinvestment')):
                if (v.multiperiod is not None
                        or v.multiperiodinvestment is not None):
                    self.multiperiod = True
                    break
                else:
                    self.multiperiod = False

    def constraint_group(self):
        if not self.multiperiod:
            return blocks.Transformer
        else:
            return blocks.MultiPeriodTransformer
