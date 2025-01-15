===========
oemof.solph
===========

.. image:: /_static/_logo/logo_oemof_solph_FULL.svg
   :align: center
   :class: only-light


.. image:: /_static/_logo/logo_oemof_solph_FULL_darkmode.svg
   :align: center
   :class: only-dark

Introduction
============
`oemof.solph` is a model generator for energy system modelling and Optimisation
(LP/MILP). The oemof.solph package is part of the
`open energy modelling framework (oemof) <https://github.com/oemof/oemof>`_.
This is an organisational framework to bundle tools for energy (system) modelling.
oemof-solph is a model generator for energy system modelling and optimisation.

The package ``oemof.solph`` is very often called just ``oemof``.
This is because installing the ``oemof`` meta package was once the best way to get ``oemof.solph``.
Notice that you should prefeably install ``oemof.solph`` instead of ``oemof``
if you want to use ``solph``.

Everybody is welcome to use and/or develop oemof.solph.
Read our `contribution <https://oemof.readthedocs.io/en/latest/contributing.html>`_ section.

Contribution is already possible on a low level by simply fixing typos in
oemof's documentation or rephrasing sections which are unclear.
If you want to support us that way please fork the oemof-solph repository to your own
GitHub account and make changes as described in the `github guidelines <https://docs.github.com/en/get-started/quickstart/hello-world>`_

If you have questions regarding the use of oemof including oemof.solph you can visit the openmod forum (`tag oemof <https://forum.openmod-initiative.org/tags/c/qa/oemof>`_ or `tag oemof-solph <https://forum.openmod-initiative.org/tags/c/qa/oemof-solph>`_) and open a new thread if your questions hasn't been already answered.

Keep in touch! - You can become a watcher at our `github site <https://github.com/oemof/oemof>`_,
but this will bring you quite a few mails and might be more interesting for developers.
If you just want to get the latest news, like when is the next oemof meeting,
you can follow our news-blog at `oemof.org <https://oemof.org/>`_.

Quick Installation
==================

For oemof.solph you need a solver on top of the software itself. Complete
installation instructions can be found
:ref:`here <installation_and_setup_label>`. For example, you can install
oemof.solph together with the CBC solver in a conda environment:

.. code:: console

    (venv) conda install -c conda-forge coincbc
    (venv) pip install oemof.solph

Contributing
============

A warm welcome to all who want to join the developers and contribute to
oemof.solph. Information on the details and how to approach us can be found
:ref:`in this section <contribute_label>`.

Cite oemof.solph
================

For explicitly citing oemof.solph, you might want to refer to
`DOI:10.1016/j.simpa.2020.100028 <https://doi.org/10.1016/j.simpa.2020.100028>`_,
which gives an overview over the capabilities of oemof.solph.
The core ideas of oemof as a whole are described in
`DOI:10.1016/j.esr.2018.07.001 <https://doi.org/10.1016/j.esr.2018.07.001>`_
(preprint at `arXiv:1808.0807 <https://arxiv.org/abs/1808.08070v1>`_).
To allow citing specific versions, we use the zenodo project to get a DOI for
each version.

Example Applications
====================
The combination of specific modules (often including other packages) is called
an application (app). For example, it can depict a concrete energy system model.
You can find a large variety of helpful examples in the in these sections:

- :ref:`introductory tutorials <introductory_tutorials_label>`
- :ref:`advanced tutorials <advanced_tutorials_label>`
- :ref:`showcase applications <showcase_examples_label>`

You are welcome to contribute your own examples via a
`pull request <https://github.com/oemof/oemof-solph/pulls>`_
or by e-mailing us (see `here <https://oemof.org/contact/>`_ for contact
information).

License
=======

Copyright (c) oemof developer group

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
