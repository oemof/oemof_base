.. _contribute_label:

============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

Bug reports
===========

When `reporting a bug <https://github.com/oemof/oemof-solph/issues>`_ please include:

    * Your operating system name and version.
    * Any details about your local setup that might be helpful in troubleshooting.
    * Detailed steps to reproduce the bug.

Documentation improvements
==========================

oemof-solph could always use more documentation, whether as part of the
official oemof-solph docs, in docstrings, or even on the web in blog posts,
articles, and such.

.. _feature_requests_and_feedback:

Feature requests and feedback
=============================

The best way to send feedback is to file an issue at https://github.com/oemof/oemof-solph/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that code contributions are welcome :)

Development
===========

To set up `oemof-solph` for local development:

1. Fork `oemof-solph <https://github.com/oemof/oemof-solph>`_
   (look for the "Fork" button).
2. Clone your fork locally::

    git clone git@github.com:oemof/oemof-solph.git

3. Install oemof.solph in editable mode with dev dependencies::

    pip install -e ./path/to/local/clone[dev]

4. Create a branch for local development::

    git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes run all the checks and docs builder with `tox <https://tox.wiki/en/latest/installation.html>`_ one command::

    tox

6. Commit your changes and push your branch to GitHub::

    git add .
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

If you need some code review or feedback while you're developing the code just make the pull request.

For merging, you should:

1. Include passing tests (run ``tox``) [1]_.
2. Update documentation when there's new API, functionality etc.
3. Add a note about the changes to ``docs/whatsnew/next_version.rst``.
4. Add your name to ``AUTHORS.rst`` and ``CITATION.cff``.

.. [1] If you don't have all the necessary python versions available locally,
       you can rely on the CI pipeline at GitHub.

       It will be slower though ...

Tests
-----

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox

Tips
----

To run only parts of the testing pipeline (e.g. documentation, stylcheck,
specific python version)::

    tox -e envname

Available standard environments are::

    clean
    check
    docs
    py39
    py310
    py311

To run a subset of tests::

    tox -e envname -- pytest -k test_myfeature

To run all the test environments in *parallel* (you need to ``pip install detox``)::

    detox
