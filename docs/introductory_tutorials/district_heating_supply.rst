.. _district_heating_portfolio_optimization_label:

District heating portfolio optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this tutorial we will optimize the portfolio of an existing heat supply.

The tutorial is set up in 4 different steps

- The existing system delivering heat with a gas boiler
- The optimization of a heat pump capacity utilizing waste heat from datacenter
  with heat storage (ad-hoc dimensioning, ~2 days of maximum heat demand)
- Introduce minimal load with converter concept (just minimal load)

.. figure:: /_files/example_network.svg
    :align: center
    :alt: Structure of the heating supplier's portfolio
    :figclass: only-light

    Structure of the heating supplier's portfolio

.. figure:: /_files/example_network_darkmode.svg
    :align: center
    :alt: Structure of the heating supplier's portfolio
    :figclass: only-dark

    Structure of the heating supplier's portfolio

Step 1: Status-Quo system
-------------------------

1. Which information is required? (no code)

  - heat demand time series
  - gas price
  - gas boiler capactiy and technical specifications

2. Import dependencies + setup EnergySystem (code snippet)

.. literalinclude:: /../tutorials/introductory/district_heating_supply.py
    :language: python
    :start-after: [sec_1_start]
    :end-before: [sec_1_end]

3. Description of which buses are required + setup? (code snippet)

.. literalinclude:: /../tutorials/introductory/district_heating_supply.py
    :language: python
    :start-after: [sec_2_start]
    :end-before: [sec_2_end]

4. Description which sinks and sources are required, load the necessary data, setup (code snippet)

.. literalinclude:: /../tutorials/introductory/district_heating_supply.py
    :language: python
    :start-after: [sec_3_start]
    :end-before: [sec_3_end]

5. Converter setup (gas boiler), how to connect buses, variable costs, capacity (code snippet)

.. literalinclude:: /../tutorials/introductory/district_heating_supply.py
    :language: python
    :start-after: [sec_4_start]
    :end-before: [sec_4_end]

6. "Optimization" of dispatch, has to follow load (code snippet)

.. literalinclude:: /../tutorials/introductory/district_heating_supply.py
    :language: python
    :start-after: [sec_5_start]
    :end-before: [sec_5_end]

7. Some results, LCOH, CO2 emissions (how to calculate and resulting numbers),
   dispatch plot(s). Include the plots in the page here!!

.. dropdown:: Click to show plotting code

    .. literalinclude:: /../tutorials/introductory/district_heating_supply.py
        :language: python
        :start-after: [sec_6_start]
        :end-before: [sec_6_end]

.. figure:: /_files/example_network.svg
    :align: center
    :alt: System dispatch of heating system with gas boiler
    :figclass: only-light

    System dispatch

.. figure:: /_files/example_network_darkmode.svg
    :align: center
    :alt: System dispatch of heating system with gas boiler
    :figclass: only-dark

    System dispatch

Step 2: Plan capacity of heat pump and heat storage
---------------------------------------------------

.. dropdown:: See the complete code

    .. literalinclude:: /../tutorials/introductory/district_heating_supply.py
        :language: python
        :start-after: [sec_6_start]
        :end-before: [sec_6_end]

1. What information is required on the new components? (data, no code, include waste heat time series)

2. Add new buses (electricity, waste heat)

3. Add waste heat source and electricity source

4. Add heat storage

5. Add heat pump

6. Run model and analyze results

Step 3: Introduce a minimal load for the converters
---------------------------------------------------

1. Modify the converters, remaining parts are identical.

.. tip::

    What if minimum demand cannot be supplied? Add a slack source for the heat
    demand.

2. Run optimization, get results, what is the difference to before?
