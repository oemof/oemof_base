# -*- coding: utf-8 -*-

"""
General description
-------------------
Example that illustrates how to model startup and shutdown costs attributed
to a binary flow.

Code
----
Download source code: :download:`startup_shutdown.py </../examples/start_and_shutdown_costs/startup_shutdown.py>`

.. dropdown:: Click to display code

    .. literalinclude:: /../examples/start_and_shutdown_costs/startup_shutdown.py
        :language: python
        :lines: 32-

Installation requirements
-------------------------
This example requires oemof.solph (v0.5.x), install by:

.. code:: bash

    pip install oemof.solph[examples]

License
-------
`MIT license <https://github.com/oemof/oemof-solph/blob/dev/LICENSE>`_

"""
import matplotlib.pyplot as plt
import pandas as pd

from oemof import solph


def main():
    demand_el = [
        0,
        0,
        0,
        1,
        1,
        1,
        0,
        0,
        1,
        1,
        1,
        0,
        0,
        1,
        1,
        1,
        0,
        0,
        1,
        1,
        1,
        1,
        0,
        0,
    ]
    # create an energy system
    idx = solph.create_time_index(2017, number=len(demand_el))
    es = solph.EnergySystem(timeindex=idx, infer_last_interval=False)

    # power bus and components
    bel = solph.Bus(label="bel")

    demand_el = solph.components.Sink(
        label="demand_el",
        inputs={bel: solph.Flow(fix=demand_el, nominal_value=10)},
    )

    # pp1 and pp2 are competing to serve overall 12 units load at lowest cost
    # summed costs for pp1 = 12 * 10 * 10.25 = 1230
    # summed costs for pp2 = 4*5 + 4*5 + 12 * 10 * 10 = 1240
    # => pp1 serves the load despite of higher variable costs since
    #    the start and shutdown costs of pp2 change its marginal costs
    pp1 = solph.components.Source(
        label="power_plant1",
        outputs={bel: solph.Flow(nominal_value=10, variable_costs=10.25)},
    )

    # shutdown costs only work in combination with a minimum load
    # since otherwise the status variable is "allowed" to be active i.e.
    # it permanently has a value of one which does not allow to set the shutdown
    # variable which is set to one if the status variable changes from one to zero
    pp2 = solph.components.Source(
        label="power_plant2",
        outputs={
            bel: solph.Flow(
                nominal_value=10,
                min=0.5,
                max=1.0,
                variable_costs=10,
                nonconvex=solph.NonConvex(startup_costs=5, shutdown_costs=5),
            )
        },
    )
    es.add(bel, demand_el, pp1, pp2)

    # create an optimization problem and solve it
    om = solph.Model(es)

    # debugging
    # om.write('problem.lp', io_options={'symbolic_solver_labels': True})

    # solve model
    om.solve(solver="cbc", solve_kwargs={"tee": True})

    # create result object
    results = solph.processing.results(om)

    # plot electrical bus
    to_bus = pd.DataFrame(
        {
            k[0].label: v["sequences"]["flow"]
            for k, v in results.items()
            if k[1] == bel
        }
    )
    from_bus = pd.DataFrame(
        {
            k[1].label: v["sequences"]["flow"] * -1
            for k, v in results.items()
            if k[0] == bel
        }
    )
    data = pd.concat([from_bus, to_bus], axis=1)
    ax = data.plot(kind="line", drawstyle="steps-post", grid=True, rot=0)
    ax.set_xlabel("Hour")
    ax.set_ylabel("P (MW)")
    plt.show()


if __name__ == "__main__":
    main()
