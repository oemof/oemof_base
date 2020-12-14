import pandas as pd
from oemof.solph import Bus
from oemof.solph import EnergySystem
from oemof.solph import Flow
from oemof.solph import Investment
from oemof.solph import Model
from oemof.solph import Sink
from oemof.solph import Source


def test_gradient():
    solver = 'cbc'

    periods = 4
    datetimeindex = pd.date_range('1/1/2016', periods=periods, freq='H')
    energysystem = EnergySystem(timeindex=datetimeindex)

    bel = Bus(label='electricity')

    energysystem.add(bel)

    # an excess and a shortage variable can help to avoid infeasible problems
    # energysystem.add(Sink(label='excess_el', inputs={bel: Flow()}))
    energysystem.add(
        Source(
            label='shortage_el',
            outputs={bel: Flow(variable_costs=200)}
        )
    )

    energysystem.add(
        Source(
            label='plants',
            outputs={
                bel: Flow(
                    investment=Investment(),
                    positive_gradient={'ub': 0.2, 'costs': 0},
                    negative_gradient={'ub': 0.2, 'costs': 0}
                    )
            }
        )
    )

    energysystem.add(
        Sink(
            label='demand',
            inputs={
                bel: Flow(
                    nominal_value=150,
                    fix=[1, 0.3, 0.75, 0.2]
                )
            }
        )
    )

    # ################################ optimization ###########################

    # create optimization model based on energy_system
    optimization_model = Model(energysystem=energysystem)

    # solve problem
    optimization_model.solve(solver=solver,
                             solve_kwargs={'tee': True, 'keepfiles': False})

    # write back results from optimization object to energysystem
    optimization_model.results()
