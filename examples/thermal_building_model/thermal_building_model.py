import os
import pprint as pp
import logging

import pandas as pd
from matplotlib import pyplot as plt

import calculate_gain_by_Sun
from tabula_reader import Building

import oemof.solph as solph
from oemof.solph import views
from oemof.tools import logger

"""
General description
-------------------
This examples optimizes the internal building temperature.
It is suppose to show how to use the component GenericBuilding.
For the generation of a GenericBuilding the tabula building data set is used.
In the end it compares the heat demand calculated by oemof and the tabula data sheet.


Installation requirements
-------------------------
This example requires the version v0.5.x of oemof.solph. Install by:

    pip install 'oemof.solph>=0.5,<0.6'

"""

__copyright__ = "oemof developer group"
__license__ = "MIT"


def main():
    #  create solver
    solver = "cbc"  # 'glpk', 'gurobi',....
    solver_verbose = False  # show/hide solver output
    number_of_time_steps = 8760
    mainPath = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    building_example = None

    # Generates 5RC Building-Model
    building_status = "no_refurbishment"
    expert_mode = None
    if expert_mode:
        if building_status == "no_refurbishment":
            building_example = Building(
                tabula_building_code="DE.N.SFH.04.Gen.ReEx.001.001",
                class_building="average",
                number_of_time_steps=number_of_time_steps,
            )
        elif building_status == "usual_refurbishment":
            building_example = Building(
                tabula_building_code="DE.N.SFH.04.Gen.ReEx.001.002",
                class_building="average",
                number_of_time_steps=number_of_time_steps,
            )
        elif building_status == "advanced_refurbishment":
            building_example = Building(
                tabula_building_code="DE.N.SFH.04.Gen.ReEx.001.003",
                class_building="average",
                number_of_time_steps=number_of_time_steps,
            )
    else:
        building_example = Building(
            country = "DE",
            construction_year = 1980,
            floor_area = 200,
            class_building="average",
            building_type ="SFH",
            refurbishment_status = "no_refurbishment",
            number_of_time_steps=number_of_time_steps,
        )
    building_example.calculate_all_parameters()

    # Pre-Calculation of solar gains with weather_data and building_data
    location = calculate_gain_by_Sun.Location(
        epwfile_path=os.path.join(
            mainPath,
            "thermal_building_model",
            "weather_files",
            "12_BW_Mannheim_TRY2035.csv",
        ),
    )
    solar_gains = building_example.calc_solar_gaings_through_windows(
        object_location_of_building=location
    )
    t_outside = location.weather_data["drybulb_C"].to_list()

    # Internal gains of residents, machines (f.e. fridge, computer,...) and lights have to be added manually
    internal_gains = []
    for _ in range(number_of_time_steps):
        internal_gains.append(0)
    # initiate the logger (see the API docs for more information)
    logger.define_logging(
        logfile="oemof_example.log",
        screen_level=logging.INFO,
        file_level=logging.INFO,
    )

    logging.info("Initialize the energy system")
    date_time_index = solph.create_time_index(
        2012, number=number_of_time_steps
    )
    es = solph.EnergySystem(
        timeindex=date_time_index, infer_last_interval=False
    )

    # create heat and cooling flow
    b_heat = solph.buses.Bus(label="b_heat")
    es.add(b_heat)
    b_cool = solph.buses.Bus(label="b_cool")
    es.add(b_cool)
    b_elect = solph.buses.Bus(label="electricity_from_grid")
    es.add(b_elect)

    es.add(
        solph.components.Source(
            label="elect_from_grid",
            outputs={b_elect: solph.flows.Flow(variable_costs=30)},
        )
    )

    es.add(
        solph.components.Sink(
            label="elect_into_grid",
            inputs={b_elect: solph.flows.Flow(variable_costs=10)},
        )
    )

    es.add(
        solph.components.Transformer(
            label="ElectricalHeater",
            inputs={b_elect: solph.flows.Flow()},
            outputs={b_heat: solph.flows.Flow(nominal_value=65000)},
            conversion_factors={b_elect: 1},
        )
    )
    es.add(
        solph.components.Transformer(
            label="ElectricalCooler",
            inputs={b_cool: solph.flows.Flow()},
            outputs={b_elect: solph.flows.Flow(nominal_value=65000)},
            conversion_factors={b_elect: 1},
        )
    )

    es.add(
        solph.components.experimental.GenericBuilding(
            label="GenericBuilding",
            inputs={b_heat: solph.flows.Flow(variable_costs=0)},
            outputs={b_cool: solph.flows.Flow(variable_costs=0)},
            solar_gains=solar_gains,
            t_outside=t_outside,
            internal_gains=internal_gains,
            t_set_heating=20,
            t_set_cooling=30,
            building_config=building_example.building_config,
            t_inital=20,
        )
    )

    ##########################################################################
    # Optimise the energy system and plot the results
    ##########################################################################

    logging.info("Optimise the energy system")

    # initialise the operational model
    model = solph.Model(es)

    # if tee_switch is true solver messages will be displayed
    logging.info("Solve the optimization problem")
    model.solve(solver=solver, solve_kwargs={"tee": solver_verbose})

    logging.info("Store the energy system with the results.")

    # The processing module of the outputlib can be used to extract the results
    # from the model transfer them into a homogeneous structured dictionary.

    # add results to the energy system to make it possible to store them.
    es.results["main"] = solph.processing.results(model)
    es.results["meta"] = solph.processing.meta_results(model)
    results = es.results["main"]
    custom_building = views.node(results, "GenericBuilding")

    fig, ax = plt.subplots(figsize=(10, 5))
    custom_building["sequences"][(("GenericBuilding", "None"), "t_air")].plot(
        ax=ax, kind="line", drawstyle="steps-post"
    )

    ax.set_ylabel("t_air in Celsius")
    plt.show()

    fig, ax = plt.subplots(figsize=(10, 5))
    custom_building = views.node(results, "GenericBuilding")
    custom_building["sequences"][(("b_heat", "GenericBuilding"), "flow")].plot(
        ax=ax, kind="line", drawstyle="steps-post"
    )
    ax.set_ylabel("heat demand in Watt")

    fig, ax = plt.subplots(figsize=(10, 5))
    custom_building = views.node(results, "GenericBuilding")
    custom_building["sequences"][(("GenericBuilding", "b_cool"), "flow")].plot(
        ax=ax, kind="line", drawstyle="steps-post"
    )
    ax.set_ylabel("cooling demand in Watt")
    plt.show()

    # print the solver results
    print("********* Meta results *********")
    pp.pprint(es.results["meta"])
    print("")


if __name__ == "__main__":
    main()
