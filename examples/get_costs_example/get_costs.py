# -*- coding: utf-8 -*-
r"""
General description
-------------------
Example that shows how to use of the processing methods get_set_costs_from_lpfile, time_dependent_values_as_dataframe and time_independent_values_as_dataframe.

The methods are combined to get the actual caused costs per timestep and the caused scalar costs e.g. invest-costs

The energysystem is copied from the exampel generic_invest_limit

There are two supply chains. The energy systems looks like that:

.. code-block:: text

                  bus_a_0          bus_a_1
                   |                 |
    source_a_0 --->|---> trafo_a --->|--->demand_a
                                     |
                       source_a_1--->|
                                     |

                  bus_b_0          bus_b_1
                   |                 |
    source_b_0 --->|---> trafo_b --->|--->demand_b
                                     |
                       source_b_1--->|
                                     |

Everything is identical - the costs for the sources, the demand, the efficiency
of the Converter. And both Converter have an investment at the output.
The source '\*_1' is in both cases very expensive, so that
a investment is probably done in the converter.
Now, both investments share a third resource, which is called "space" in this
example. (This could be anything, and you could use as many additional
resources as you want.) And this resource is limited. In this case, every
converter capacity unit, which might be installed, needs 2 space for
'trafo a', and 1 space per installed capacity for 'trafo b'.
And the total space is limited to 24.
See what happens, have fun ;)

Code
----
Download source code: :download:`example_generic_invest.py </../examples/generic_invest_limit/example_generic_invest.py>`

.. dropdown:: Click to display code

    .. literalinclude:: /../examples/generic_invest_limit/example_generic_invest.py
        :language: python
        :lines: 62-

Installation requirements
-------------------------
This example requires oemof.solph (v0.5.x), install by:

.. code:: bash

    pip install oemof.solph[examples]

License
-------
Johannes Röder <johannes.roeder@uni-bremen.de>

`MIT license <https://github.com/oemof/oemof-solph/blob/dev/LICENSE>`_
"""

import logging
import os

from oemof import solph
from oemof.solph import _experimental_processing as exppro


def main():
    data = [0, 15, 30, 35, 20, 25, 27, 10, 5, 2, 15, 40, 20, 0, 0]

    # create an energy system
    idx = solph.create_time_index(2020, number=len(data))
    es = solph.EnergySystem(timeindex=idx, infer_last_interval=False)

    # Parameter: costs for the sources
    c_0 = 10
    c_1 = 100

    epc_invest = 500

    # commodity a
    bus_a_0 = solph.Bus(label="bus_a_0")
    bus_a_1 = solph.Bus(label="bus_a_1")
    es.add(bus_a_0, bus_a_1)

    es.add(
        solph.components.Source(
            label="source_a_0",
            outputs={bus_a_0: solph.Flow(variable_costs=c_0)},
        )
    )

    es.add(
        solph.components.Source(
            label="source_a_1",
            outputs={bus_a_1: solph.Flow(variable_costs=c_1)},
        )
    )

    es.add(
        solph.components.Sink(
            label="demand_a",
            inputs={bus_a_1: solph.Flow(fix=data, nominal_value=1)},
        )
    )

    # commodity b
    bus_b_0 = solph.Bus(label="bus_b_0")
    bus_b_1 = solph.Bus(label="bus_b_1")
    es.add(bus_b_0, bus_b_1)
    es.add(
        solph.components.Source(
            label="source_b_0",
            outputs={bus_b_0: solph.Flow(variable_costs=data)},
        )
    )

    es.add(
        solph.components.Source(
            label="source_b_1",
            outputs={bus_b_1: solph.Flow(variable_costs=c_1)},
        )
    )

    es.add(
        solph.components.Sink(
            label="demand_b",
            inputs={bus_b_1: solph.Flow(fix=data, nominal_value=1)},
        )
    )

    # Converter a
    es.add(
        solph.components.Converter(
            label="trafo_a",
            inputs={bus_a_0: solph.Flow()},
            outputs={
                bus_a_1: solph.Flow(
                    nominal_value=solph.Investment(
                        ep_costs=epc_invest, custom_attributes={"space": 2}
                    )
                )
            },
            conversion_factors={bus_a_1: 0.8},
        )
    )

    # Converter b
    es.add(
        solph.components.Converter(
            label="trafo_b",
            inputs={bus_b_0: solph.Flow()},
            outputs={
                bus_b_1: solph.Flow(
                    nominal_value=solph.Investment(
                        ep_costs=epc_invest, custom_attributes={"space": 1}
                    )
                )
            },
            conversion_factors={bus_a_1: 0.8},
        )
    )

    # create an optimization problem and solve it
    om = solph.Model(es)

    # add constraint for generic investment limit
    om = solph.constraints.additional_investment_flow_limit(
        om, "space", limit=24
    )

    # export lp file
    filename = os.path.join(
        solph.helpers.extend_basic_path("lp_files"), "GenericInvest.lp"
    )
    logging.info("Store lp-file in {0}.".format(filename))
    om.write(filename, io_options={"symbolic_solver_labels": True})

    # solve model
    om.solve(solver="cbc", solve_kwargs={"tee": True})

    # to get the set costs use the method get_set_costs_from_lpfile

    set_tdc, set_tic = exppro.get_set_costs_from_lpfile(filename, om)

    # create result object. The last timestep has to be removed
    results = solph.processing.results(om, remove_last_time_point=True)

    # now get the timedependent  optimized values as dataframe

    dataframe_tdv = exppro.time_dependent_values_as_dataframe(results)

    # now get the timeindependent  optimized values as dataframe
    dataframe_tiv = exppro.time_independent_values_as_dataframe(results)

    #  filter values with costs

    td_intersect = set_tdc.columns.intersection(dataframe_tdv.columns)
    ti_intersect = set_tic.columns.intersection(dataframe_tiv.columns)

    # calculate costs
    time_dependent_costs = dataframe_tdv[td_intersect] * set_tdc[td_intersect]

    time_independent_costs = (
        dataframe_tiv[ti_intersect] * set_tic[ti_intersect]
    )

    print(time_dependent_costs)

    print(time_independent_costs)


if __name__ == "__main__":
    main()
