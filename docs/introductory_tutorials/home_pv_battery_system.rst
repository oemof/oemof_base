.. _home_pv_battery_system_label:

Home PV installation with battery storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's start with a more or less blank scenario: Imagine you want to set up a PV
plant on top of your single family house. How would you find out which system
fits best and why? Here are some possible points to think about:

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

Step 1: PV installation without storage
---------------------------------------

1. Which information is required? (no code)

  - heat demand time series
  - gas price
  - gas boiler capactiy and technical specifications

2. Import dependencies + setup EnergySystem (code snippet)

.. literalinclude:: /../tutorials/introductory/pv_battery_system_1.py
    :language: python
    :start-after: [sec_1_start]
    :end-before: [sec_1_end]

:download:`pv_battery_system_1.py </../tutorials/introductory/pv_battery_system_1.py>`

.. attention::

    Hier musst du aufmerksam sein!


.. dropdown:: Click to expand

    Das ist versteckt
