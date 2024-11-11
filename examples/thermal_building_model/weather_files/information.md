------------------------------

===========
Weather Files
===========

**A model generator for energy system modelling and optimisation (LP/MILP)**

.. contents::
    :depth: 2
    :local:
    :backlinks: top

Source
============

The listed weather files are extracted from the `repository of free climate data for building performance simulation  <https://climate.onebuilding.org/default.html>`_ (from the Creators of EPW). The repository provides world wide weather data for typical meteorological years (TMY).
In addition the repository provides  test reference years (TRY). The TRF are intended to represent an average but typical weather pattern for the year. Such data sets are mainly used by planners and engineers for simulations and calculations in the heating and ventilation sector.

Listed Files
============

In this folder are TRY weather files listed. DWD separated for  germany into 15 typical weather regions. For further information we refer to `test reference years TRY <https://www.dwd.de/DE/leistungen/klimastatusbericht/publikationen/ksb2004_pdf/22_2004.pdf?__blob=publicationFile&v=1>`_.
Following this separation the typical weather files for this 15 different locations are added from the Source repository. The files are added for 2035 and include therefore a forecast. Historical data can be found as well on the homepage as well.

Structure of the Files
============

The weather files follow the structure of the EnergyPlus Weather File (EPW) Data Dictionary. For further information about the structure we refer to `Energy Plus Weather File Format <https://climate.onebuilding.org/papers/EnergyPlus_Weather_File_Format.pdf>`_.
This table shows the field attributes of the weather files:

.. list-table:: Field Attributes
   :header-rows: 1

   * - Field Number
     - Name
     - Units
     - Missing
     - Minimum
     - Maximum
   * - N1
     - Year
     -
     -
     -
     -
   * - N2
     - Month
     -
     -
     -
     -
   * - N3
     - Day
     -
     -
     -
     -
   * - N4
     - Hour
     -
     -
     -
     -
   * - N5
     - Minute
     -
     -
     -
     -
   * - N6
     - Dry Bulb Temperature
     - C
     - 99.9
     - -70
     - 70
   * - N7
     - Dew Point Temperature
     - C
     - 99.9
     - -70
     - 70
   * - N8
     - Relative Humidity
     -
     - 999.
     - 0
     - 110
   * - N9
     - Atmospheric Station Pressure
     - Pa
     - 999999.
     - 31000
     - 120000
   * - N10
     - Extraterrestrial Horizontal Radiation
     - Wh/m2
     - 9999.
     - 0
     -
   * - N11
     - Extraterrestrial Direct Normal Radiation
     - Wh/m2
     - 9999.
     - 0
     -
   * - N12
     - Horizontal Infrared Radiation Intensity
     - Wh/m2
     - 9999.
     - 0
     -
   * - N13
     - Global Horizontal Radiation
     - Wh/m2
     - 9999.
     - 0
     -
   * - N14
     - Direct Normal Radiation
     - Wh/m2
     - 9999.
     - 0
     -
   * - N15
     - Diffuse Horizontal Radiation
     - Wh/m2
     - 9999.
     - 0
     -
   * - N16
     - Global Horizontal Illuminance
     - lux
     - 999999.
     - 0
     -
   * - N17
     - Direct Normal Illuminance
     - lux
     - 999999.
     - 0
     -
   * - N18
     - Diffuse Horizontal Illuminance
     - lux
     - 999999.
     - 0
     -
   * - N19
     - Zenith Luminance
     - Cd/m2
     - 9999.
     - 0
     -
   * - N20
     - Wind Direction
     - degrees
     - 999.
     - 0
     - 360
   * - N21
     - Wind Speed
     - m/s
     - 999.
     - 0
     - 40
   * - N22
     - Total Sky Cover
     -
     - 99
     - 0
     - 10
   * - N23
     - Opaque Sky Cover (used if Horizontal IR Intensity missing)
     -
     - 99
     - 0
     - 10
   * - N24
     - Visibility
     - km
     - 9999
     -
     -
   * - N25
     - Ceiling Height
     - m
     - 99999
     -
     -
   * - N26
     - Present Weather Observation
     -
     -
     -
     -
   * - N27
     - Present Weather Codes
     -
     -
     -
     -
   * - N28
     - Precipitable Water
     - mm
     - 999
     -
     -
   * - N29
     - Aerosol Optical Depth
     -
     - .999
     -
     -
   * - N30
     - Snow Depth
     - cm
     - 999
     -
     -
   * - N31
     - Days Since Last Snowfall
     -
     - 99
     -
     -
   * - N32
     - Albedo
     -
     - 999
     -
     -
   * - N33
     - Liquid Precipitation Depth
     - mm
     - 999
     -
     -
   * - N34
     - Liquid Precipitation Quantity
     - hr
     - 99
     -
     -

License
=======

?
