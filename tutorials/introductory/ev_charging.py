# %%[imports]
"""
First of all, we create some input data. We use Pandas to do so and will also
import matplotlib to plot the data right away and import solph
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import oemof.solph as solph

# %%[trip_data]

time_index = pd.date_range(
    start="2025-01-01",
    end="2025-01-02",
    freq="5min",
    inclusive="both",
)

# Define the trip demand series for the real trip scenario.
# As the demand is a power time series, it has N-1 entries
# when compared to the N entires of time axis for the energy.
ev_demand = pd.Series(0, index=time_index[:-1])

# Morning Driving: 07:00 to 08:00
driving_start_morning = pd.Timestamp("2025-01-01 07:10")
driving_end_morning = pd.Timestamp("2025-01-01 08:10")
ev_demand.loc[driving_start_morning:driving_end_morning] = 10  # kW

# Evening Driving: 17:00 to 18:00.
# Note that time points work even if they are not in the index.
driving_start_evening = pd.Timestamp("2025-01-01 17:13:37")
driving_end_evening = pd.Timestamp("2025-01-01 18:47:11")
ev_demand.loc[driving_start_evening:driving_end_evening] = 9  # kW

plt.figure()
plt.title("Driving pattern")
plt.plot(ev_demand)
plt.ylabel("Power (kW)")
plt.gcf().autofmt_xdate()

# %%[base_system]
"""
Now, let's create an energy system model of the electric vehicle that
follows the driving pattern. It uses the same time index defined above
and consists of a Battery (partly charged in the beginning)
and an electricity demand.
"""


def create_base_system():
    energy_system = solph.EnergySystem(
        timeindex=time_index,
        infer_last_interval=False,
    )

    b_car = solph.Bus(label="Car Electricity")

    energy_system.add(b_car)

    # As we have a demand time series which is actually in kW, we use a common
    # "hack" here: We set the nominal capacity to 1 (kW), so that
    # multiplication by the time series will just yield the correct result.
    demand_driving = solph.components.Sink(
        label="Driving Demand",
        inputs={b_car: solph.Flow(nominal_capacity=1, fix=ev_demand)},
    )

    energy_system.add(demand_driving)

    # We define a "storage revenue" (negative costs) for the last time step,
    # so that energy inside the storage in the last time step is worth
    # something.
    storage_revenue = np.zeros(len(time_index) - 1)
    storage_revenue[-1] = -0.6  # 60 ct/kWh in the last time step

    car_battery = solph.components.GenericStorage(
        label="Car Battery",
        nominal_capacity=50,  # kWh
        inputs={b_car: solph.Flow()},
        outputs={b_car: solph.Flow()},
        initial_storage_level=0.75,  # 75 % full in the beginning
        loss_rate=0.001,  # 0.1 % / hr
        inflow_conversion_factor=0.9,  # 90 % charging efficiency
        balanced=False,  # True: content at beginning and end need to be equal
        storage_costs=storage_revenue,  # Only has an effect on charging.
    )
    energy_system.add(car_battery)

    return energy_system


# %%[solve_and_plot]
"""
Solve the model and show results
"""


def solve_and_plot(plot_title):
    model = solph.Model(es)
    model.solve(solve_kwargs={"tee": False})
    results = solph.processing.results(model)

    battery_series = solph.views.node(results, "Car Battery")["sequences"]

    plt.figure()
    plt.title(plot_title)
    plt.plot(battery_series[(("Car Battery", "None"), "storage_content")])
    plt.ylabel("Energy (kWh)")
    plt.ylim(0, 60)
    plt.twinx()
    plt.ylim(0, 12)
    energy_enters_battery = battery_series[
        (("Car Electricity", "Car Battery"), "flow")
    ]
    energy_leaves_battery = battery_series[
        (("Car Battery", "Car Electricity"), "flow")
    ]
    plt.step(energy_leaves_battery.index, energy_leaves_battery, "r--")
    plt.step(energy_enters_battery.index, energy_enters_battery, "r-")
    plt.grid()
    plt.ylabel("Power (kW)")
    plt.gcf().autofmt_xdate()


es = create_base_system()
solve_and_plot("Driving demand only")


# %%[AC_30ct_charging]
"""
Now, let's assume the car battery can be charged at home. Unfortunately, there
is only a power so cket available, limiting the charging process to 16 A at
230 V. This, of course, can only happen while the car is present.
"""


def add_domestic_socket_charging():
    car_at_home = pd.Series(1, index=time_index[:-1])
    car_at_home.loc[driving_start_morning:driving_end_evening] = 0

    b_car = es.node["Car Electricity"]

    # To be able to load the battery a electric source e.g. electric grid is
    # necessary. We set the maximum use to 1 if the car is present, while it
    # is 0 between the morning start and the evening arrival back home.
    # While the car itself can potentially charge with at a higher power,
    # we just add an AC source with 16 A at 230 V.
    charger230V = solph.components.Source(
        label="230V AC",
        outputs={
            b_car: solph.Flow(
                nominal_capacity=3.68,  # 230 V * 16 A = 3.68 kW
                variable_costs=0.3,  # 30 ct/kWh
                max=car_at_home,
            )
        },
    )

    es.add(charger230V)


es = create_base_system()
add_domestic_socket_charging()
solve_and_plot("Domestic power socket charging")

# %%[DC_charging]
"""
Now, we add an 11 kW charger (no costs) which is available at work.
This, of course, can only happen while the car is present at work.
"""


def add_11kW_charging():
    car_at_work = pd.Series(0, index=time_index[:-1])
    car_at_work.loc[driving_end_morning:driving_start_evening] = 1

    b_car = es.node["Car Electricity"]

    # variable_costs in the Flow default to 0, so it's free
    charger11kW = solph.components.Source(
        label="11kW",
        outputs={
            b_car: solph.Flow(
                nominal_capacity=11,  # 11 kW
                max=car_at_work,
            )
        },
    )

    es.add(charger11kW)


es = create_base_system()
add_domestic_socket_charging()
add_11kW_charging()
solve_and_plot("Home and work charging")


# %%[DC_charging_fixed]
"""
To avoid the energy from looping in the battery, we introduce marginal costs
to battery charging. This is a way to model cyclic aging of the battery.
"""


def create_base_system():
    energy_system = solph.EnergySystem(
        timeindex=time_index,
        infer_last_interval=False,
    )

    b_car = solph.Bus(label="Car Electricity")

    energy_system.add(b_car)

    demand_driving = solph.components.Sink(
        label="Driving Demand",
        inputs={b_car: solph.Flow(nominal_capacity=1, fix=ev_demand)},
    )

    energy_system.add(demand_driving)

    storage_revenue = np.zeros(len(time_index) - 1)
    storage_revenue[-1] = -0.6

    car_battery = solph.components.GenericStorage(
        label="Car Battery",
        nominal_capacity=50,
        inputs={
            b_car: solph.Flow(
                variable_costs=1e-4,  # models cyclic aging
            )
        },
        outputs={b_car: solph.Flow()},
        initial_storage_level=0.75,
        loss_rate=0.001,
        inflow_conversion_factor=0.9,
        balanced=False,
        storage_costs=storage_revenue,
    )
    energy_system.add(car_battery)

    return energy_system


es = create_base_system()
add_domestic_socket_charging()
add_11kW_charging()
solve_and_plot("Home and work charging (fixed)")

# %%[AC_var_charging]
"""
Now, we replace the home socket charging by a version with variable
electricity prices.
"""


def add_domestic_socket_charging_var():
    car_at_home = pd.Series(1, index=time_index[:-1])
    car_at_home.loc[driving_start_morning:driving_end_evening] = 0

    b_car = es.node["Car Electricity"]

    # Same as above, but electricity is cheaper every other step.
    # Thus, battery is only charged these steps.
    charger230V = solph.components.Source(
        label="230V AC",
        outputs={
            b_car: solph.Flow(
                nominal_capacity=3.68,  # 230 V * 16 A = 3.68 kW
                variable_costs=[0.2, 0.3] * (len(time_index) // 2),
                max=car_at_home,
            )
        },
    )

    es.add(charger230V)


es = create_base_system()
add_domestic_socket_charging_var()
add_11kW_charging()
solve_and_plot("Variable price charging")

plt.show()
