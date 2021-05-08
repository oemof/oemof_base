"""
Test for creating an MultiPeriod optimization model

Create an energy system consisting of the following fleets
- lignite
- hardcoal
- CCGT
- GT
- Wind
- GenericStorage unit
for Germany

Add wind source and demand sink for FR and links for exchange.
"""

import matplotlib.pyplot as plt
import pandas as pd

from oemof.solph import (models, network, components, custom, options,
                         processing, views)

# import models
# import network
# import components
# import custom
# import options
# import processing
# import views

t_idx_1 = pd.date_range('1/1/2020', periods=3, freq='H')
t_idx_2 = pd.date_range('1/1/2030', periods=3, freq='H')
t_idx_3 = pd.date_range('1/1/2040', periods=3, freq='H')
t_idx_4 = pd.date_range('1/1/2050', periods=3, freq='H')

# timeindex = {'1': t_idx_1, '2': t_idx_2, '3': t_idx_3}

# Create an overall timeindex
t_idx_1_Series = pd.Series(index=t_idx_1, dtype='float64')
t_idx_2_Series = pd.Series(index=t_idx_2, dtype='float64')
t_idx_3_Series = pd.Series(index=t_idx_3, dtype='float64')
t_idx_4_Series = pd.Series(index=t_idx_4, dtype='float64')

# timeindex = pd.concat([t_idx_1_Series, t_idx_2_Series,
#                        t_idx_3_Series]).index
timeindex = pd.concat([t_idx_1_Series, t_idx_2_Series,
                       t_idx_3_Series, t_idx_4_Series]).index

es = network.EnergySystem(timeindex=timeindex,
                          timeincrement=[1] * len(timeindex))

# Create buses
bus_lignite = network.Bus(label='DE_bus_lignite',
                          # balanced=True)
                          balanced=True,
                          multiperiod=True)
bus_hardcoal = network.Bus(label='DE_bus_hardcoal',
                           # balanced=True)
                           balanced=True,
                           multiperiod=True)
bus_natgas = network.Bus(label='DE_bus_natgas',
                         # balanced=True)
                         balanced=True,
                         multiperiod=True)
bus_el = network.Bus(label='DE_bus_el',
                     # balanced=True)
                     balanced=True,
                     multiperiod=True)
bus_el_FR = network.Bus(label='FR_bus_el',
                        # balanced=True)
                        balanced=True,
                        multiperiod=True)

# Create sources
source_lignite = network.Source(
    label='DE_source_lignite',
    outputs={bus_lignite: network.Flow(
        # variable_costs=5)})
        variable_costs=5,
        multiperiod=True)})
source_hardcoal = network.Source(
    label='DE_source_hardcoal',
    outputs={bus_hardcoal: network.Flow(
        # variable_costs=10)})
        variable_costs=10,
        multiperiod=True)})
source_natgas = network.Source(
    label='DE_source_natgas',
    outputs={bus_natgas: network.Flow(
        # variable_costs=20)})
        variable_costs=20,
        multiperiod=True)})
source_wind = network.Source(
    label='DE_source_wind',
    outputs={bus_el: network.Flow(  # variable_costs=0)})
        variable_costs=0,
        # fix=[90] * len(timeindex),
        fix=[110] + [90] * (len(timeindex) - 1),
        # nominal_value=1)})
        nominal_value=1,
        multiperiod=True)})
source_shortage = network.Source(
    label='DE_source_shortage',
    outputs={bus_el: network.Flow(
        variable_costs=1e10,
        # nominal_value=1e10)})
        nominal_value=1e10,
        multiperiod=True)})

source_wind_FR = network.Source(
    label='FR_source_wind',
    outputs={bus_el_FR: network.Flow(  # variable_costs=0)})
        variable_costs=0,
        fix=[45] * len(timeindex),
        # nominal_value=1)})
        nominal_value=1,
        multiperiod=True)})
source_shortage_FR = network.Source(
    label='FR_source_shortage',
    outputs={bus_el_FR: network.Flow(
        variable_costs=1e10,
        # nominal_value=1e10)})
        nominal_value=1e10,
        multiperiod=True)})

# Create sinks
sink_el = network.Sink(
    label='DE_sink_el',
    inputs={bus_el: network.Flow(
        # Use this when using storage / demand response / exchange
        fix=[80] * len(timeindex),
        # Use this when simulating only the basic config, without the above
        # fix=[100] * len(timeindex),
        # nominal_value=1)})
        nominal_value=1,
        multiperiod=True)})

sink_excess = network.Sink(
    label='DE_sink_excess',
    inputs={bus_el: network.Flow(
        # variable_costs=1e3,
        variable_costs=1e10,
        # nominal_value=1e10)})
        nominal_value=1e10,
        multiperiod=True)})
sink_excess_FR = network.Sink(
    label='FR_sink_excess',
    inputs={bus_el_FR: network.Flow(
        variable_costs=1e3,
        # nominal_value=1e10)})
        nominal_value=1e10,
        multiperiod=True)})

sink_el_FR = network.Sink(
    label='FR_sink_el',
    inputs={bus_el_FR: network.Flow(fix=[50] * len(timeindex),
                                    # nominal_value=1)})
                                    nominal_value=1,
                                    multiperiod=True)})

# Create multiperiod transformers
pp_lignite = network.Transformer(
    label='DE_pp_lignite',
    inputs={bus_lignite: network.Flow(  # )},
        multiperiod=True)},
    outputs={bus_el: network.Flow(
        # investment=options.Investment(
        multiperiodinvestment=options.MultiPeriodInvestment(
            maximum=1000,
            ep_costs=2e6,
            existing=0,
            lifetime=20,
            age=0,
            interest_rate=0.02,
        ),
        # nominal_value=100,
        variable_costs=1
    )},
    conversion_factors={bus_el: 0.38})

pp_hardcoal = network.Transformer(
    label='DE_pp_hardcoal',
    inputs={bus_hardcoal: network.Flow(  # )},
        multiperiod=True)},
    outputs={bus_el: network.Flow(
        # investment=options.Investment(
        multiperiodinvestment=options.MultiPeriodInvestment(
            maximum=1000,
            ep_costs=1.6e6,
            existing=0,
            lifetime=20,
            age=0,
            interest_rate=0.02,
        ),
        # nominal_value=100,
        variable_costs=2
    )},
    conversion_factors={bus_el: 0.45})

pp_natgas_CCGT = network.Transformer(
    label='DE_pp_natgas_CCGT',
    inputs={bus_natgas: network.Flow(  # )},
        multiperiod=True)},
    outputs={bus_el: network.Flow(
        # investment=options.Investment(
        multiperiodinvestment=options.MultiPeriodInvestment(
            maximum=1000,
            ep_costs=1e6,
            existing=0,
            lifetime=20,
            age=0,
            interest_rate=0.02,
            #     overall_minimum=2,
        ),
        # nominal_value=100,
        variable_costs=3,
        # fixed_cost=10
    )},
    conversion_factors={bus_el: 0.6})

pp_natgas_GT = network.Transformer(
    label='DE_pp_natgas_GT',
    inputs={bus_natgas: network.Flow(  # )},
        multiperiod=True)},
    outputs={bus_el: network.Flow(
        # investment=options.Investment(
        multiperiodinvestment=options.MultiPeriodInvestment(
            maximum=1000,
            # ep_costs=0.6e6,
            # ep_costs=[0.6e6, 0.5e6, 0.8e6],
            ep_costs=[0.6e6, 0.5e6, 0.8e6, 0.4e6],
            existing=0,
            lifetime=20,
            age=0,
            interest_rate=0.02,
            fixed_costs=1000,
            # overall_maximum=9,
            # nonconvex=True,
            # offset=400,
            # age=1,
            # lifetime=2,
            # age=39,
            # lifetime=40
        ),
        # summed_max=2,
        # min=0.1,
        # max=0.9,
        # fix=1,
        # multiperiod=True,
        # nominal_value=100,
        variable_costs=4,
        # fixed_costs=30
    )},
    conversion_factors={bus_el: 0.4})

storage_el = components.GenericStorage(
    label='DE_storage_el',
    inputs={bus_el: network.Flow(
        # nominal_value=20,
        variable_costs=0,
        max=1,
        # multiperiod=True
        # investment=options.Investment(
        multiperiodinvestment=options.MultiPeriodInvestment(
            maximum=20,
            ep_costs=1000,
            existing=10,
            lifetime=2,
            age=1,
            interest_rate=0.02,
            # age=39,
            # lifetime=40
        )
    )},
    outputs={bus_el: network.Flow(
        # nominal_value=20,
        variable_costs=0,
        max=1,
        # multiperiod=True
        # investment=options.Investment(
        multiperiodinvestment=options.MultiPeriodInvestment(
            maximum=20,
            ep_costs=1000,
            existing=10,
            lifetime=2,
            age=1,
            interest_rate=0.02,
            # age=39,
            # lifetime=40
        )
    )},
    # nominal_storage_capacity=20,
    loss_rate=0,
    initial_storage_level=0,
    max_storage_level=1,
    min_storage_level=0,
    inflow_conversion_factor=1,
    outflow_conversion_factor=1,
    balanced=True,
    invest_relation_input_output=1,
    invest_relation_input_capacity=None,
    invest_relation_output_capacity=None,
    # multiperiod=True,
    fixed_costs=10,
    # investment=options.Investment(
    multiperiodinvestment=options.MultiPeriodInvestment(
        maximum=20,
        ep_costs=1000,
        existing=10,
        lifetime=2,
        age=1,
        interest_rate=0.02,
        # fixed_costs=10,
        # overall_maximum=9,
        # overall_minimum=14,
        # nonconvex=True,
        # age=39,
        # lifetime=40
    )
)

link_DE_FR = custom.Link(
    label='link_DE_FR',
    inputs={
        bus_el: network.Flow(
            # nominal_value=10)},
            nominal_value=10,
            multiperiod=True),
        bus_el_FR: network.Flow(
            # nominal_value=10)},
            nominal_value=10,
            multiperiod=True)
    },
    outputs={
        bus_el_FR: network.Flow(
            multiperiod=True
        ),
        bus_el: network.Flow(
            multiperiod=True
        )
    },
    conversion_factors={
        (bus_el, bus_el_FR): 0.999999,
        (bus_el_FR, bus_el): 0.999999},
    multiperiod=True
)

approach = 'DLR'

kwargs_all = {
    'label': 'demand_dsm',
    'inputs': {bus_el: network.Flow(
        variable_costs=0,
        multiperiod=True
    )},
    'demand': [1] * len(timeindex),
    'capacity_up': [1] * len(timeindex),
    'capacity_down': [1] * len(timeindex),
    'delay_time': 4,
    'shed_time': 2,
    'recovery_time_shift': 0,
    'recovery_time_shed': 24,
    'cost_dsm_up': 0.01,
    'cost_dsm_down_shift': 0.01,
    'cost_dsm_down_shed': 1000,
    'efficiency': 1.0,
    'shed_eligibility': False,
    'shift_eligibility': True,
    # 'max_demand': 20,
    # 'max_capacity_down': 10,
    # 'max_capacity_up': 10,
    'flex_share_down': 1,
    'flex_share_up': 1,
    'shift_time': 2}

kwargs_dict = {
    'oemof': {'shift_interval': 24},

    'DIW': {},

    'DLR': {'ActivateYearLimit': False,
            'ActivateDayLimit': False,
            'n_yearLimit_shift': None,
            'n_yearLimit_shed': 10,
            't_dayLimit': None,
            'addition': True,
            'fixes': True},
}

dsm_unit = custom.SinkDSM(
    **kwargs_all,
    approach=approach,
    **kwargs_dict[approach],
    # multiperiod=True,
    multiperiodinvestment=options.MultiPeriodInvestment(
        # investment=options.Investment(
        existing=10,
        maximum=20,
        ep_costs=10,
        lifetime=2,
        age=1,
        interest_rate=0.02
    )
)

es.add(source_lignite, source_hardcoal, source_natgas, source_wind,
       source_shortage,
       bus_lignite, bus_hardcoal, bus_natgas, bus_el,
       pp_lignite, pp_hardcoal, pp_natgas_CCGT, pp_natgas_GT,
       sink_el, sink_excess, storage_el,
       source_wind_FR, source_shortage_FR,
       bus_el_FR, sink_el_FR, sink_excess_FR, link_DE_FR,
       dsm_unit,
       )

# test = models.Model(es)
test = models.MultiPeriodModel(es, discount_rate=0.02)
# test.pprint()
test.receive_duals()

test.solve(solver='gurobi', solve_kwargs={'tee': True})

meta = processing.meta_results(test)

# es.results['main'] = processing.results(test)
results = processing.results(test)

# Show inflows and outflows from electricity bus
bus_el_flow_res = views.node(results, bus_el)['sequences']
# Collect all investment results
invest_units = [bus_el, dsm_unit, storage_el]
# invest_units = [bus_el]

invest_res = {}

for el in invest_units:
    invest_res[el] = views.node(results, el)['scalars']

invest_results = pd.concat(invest_res.values(), axis=0)
invest_results.index = pd.MultiIndex.from_tuples(invest_results.index)
invest_results.reset_index(inplace=True)
invest_results.drop_duplicates(inplace=True)
invest_results.rename(columns={'level_0': 'node', 'level_1': 'period'},
                      inplace=True)
invest_results = invest_results.pivot(index='period', columns='node')
invest_results.columns = invest_results.columns.swaplevel()

invest_cols = invest_results.columns.get_level_values(1) == 'invest'
investments = invest_results.loc[:, invest_cols]

investments.plot(kind='bar')
plt.title('Investments per period')
plt.show()
