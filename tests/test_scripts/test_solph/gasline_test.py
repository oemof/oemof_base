import oemof.solph as solph
import oemof.solph.exnet as ex
from oemof.outputlib import *
import math
import pandas as pd
import time

# Please run this file as normal project
# when oemof verison with exnet is installed

datetimeindex = pd.date_range('1/1/2017', periods=3, freq='H')

es = solph.EnergySystem(timeindex=datetimeindex)
input_list = []
input_list.append(-1)
i = 0
while i < 101:
    ob = i / 100
    input_list.append(ob)
    i = i + 1
output_list = []
output_list.append(0)

for ob in input_list:
    if ob != -1:
        s = math.sqrt(ob)
        output_list.append(s)

b_gas1 = ex.GasBus(label='b_gas1', slack=True)
b_gas2 = ex.GasBus(label='b_gas2')
b_gas3 = ex.GasBus(label='b_gas3')


gas_line_12 = ex.GasLine(label='gas_line_12',
                         inputs={b_gas1: solph.Flow(nominal_value=200)},
                         outputs={b_gas2: solph.Flow(nominal_value=200)},
                         input_list=input_list,
                         output_list=output_list,
                         K_1=100,
                         conv_factor=0.99)

gas_line_13 = ex.GasLine(label='gas_line_13',
                         inputs={b_gas1: solph.Flow(nominal_value=200)},
                         outputs={b_gas3: solph.Flow(nominal_value=200)},
                         input_list=input_list,
                         output_list=output_list,
                         K_1=100,
                         conv_factor=0.99)

gas_line_23 = ex.GasLine(label='gas_line_23',
                         inputs={b_gas2: solph.Flow(nominal_value=200)},
                         outputs={b_gas3: solph.Flow(nominal_value=200)},
                         input_list=input_list,
                         output_list=output_list,
                         K_1=100,
                         conv_factor=0.99)

gas_line_32 = ex.GasLine(label='gas_line_32',
                         inputs={b_gas3: solph.Flow(nominal_value=200)},
                         outputs={b_gas2: solph.Flow(nominal_value=200)},
                         input_list=input_list,
                         output_list=output_list,
                         K_1=100,
                         conv_factor=0.99)

source_1 = solph.Source(label='source_1',
                        outputs={b_gas1: solph.Flow(nominal_value=300)})


sink_1 = solph.Sink(label='sink_1',
                    inputs={b_gas2: solph.Flow(nominal_value=100,
                                               actual_value=[1, 1, 0],
                                               fixed=True)})

sink_2 = solph.Sink(label='sink_2',
                    inputs={b_gas3: solph.Flow(nominal_value=100,
                                               actual_value=[1, 0, 1],
                                               fixed=True)})

es.add(b_gas1)
es.add(b_gas2)
es.add(b_gas3)
es.add(gas_line_12)
es.add(gas_line_13)
es.add(gas_line_23)
es.add(gas_line_32)

es.add(source_1)
es.add(sink_1)
es.add(sink_2)

model = solph.Model(es)
model.solve(solver='cbc')
model.results()
results = processing.results(model)
