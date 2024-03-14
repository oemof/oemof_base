# -*- coding: utf-8 -*-

"""Solph Optimization Models.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: gplssm
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-FileCopyrightText: Saeed Sayadi
SPDX-FileCopyrightText: Johannes Kochems
SPDX-FileCopyrightText: Lennart Schürmann

SPDX-License-Identifier: MIT

"""
import logging
import warnings
from logging import getLogger

from oemof.tools import debugging
from pyomo import environ as po
from pyomo.core.plugins.transform.relax_integrality import RelaxIntegrality
from pyomo.opt import SolverFactory

from oemof.solph import processing
from oemof.solph.buses._bus import BusBlock
from oemof.solph.components._converter import ConverterBlock
from oemof.solph.flows._invest_non_convex_flow_block import (
    InvestNonConvexFlowBlock,
)
from oemof.solph.flows._investment_flow_block import InvestmentFlowBlock
from oemof.solph.flows._non_convex_flow_block import NonConvexFlowBlock
from oemof.solph.flows._simple_flow_block import SimpleFlowBlock


class LoggingError(BaseException):
    """Raised when the wrong logging level is used."""

    pass


class BaseModel(po.ConcreteModel):
    """The BaseModel for other solph-models (Model)

    Parameters
    ----------
    energysystem : EnergySystem object or (experimental) list
        Object that holds the nodes of an oemof energy system graph.
        Experimental: If a list is passed, the list needs to hold EnergySystem
        objects and a cellular structure is assumed. In this case, the first
        element needs to be the upmost energy cell (structurally containing
        all other cells).
    constraint_groups : list (optional)
        Solph looks for these groups in the given energy system and uses them
        to create the constraints of the optimization problem.
        Defaults to `Model.CONSTRAINTS`
    objective_weighting : array like (optional)
        Weights used for temporal objective function
        expressions. If nothing is passed, `timeincrement` will be used which
        is calculated from the freq length of the energy system timeindex or
        can be directly passed as a sequence.
    auto_construct : boolean
        If this value is true, the set, variables, constraints, etc. are added,
        automatically when instantiating the model. For sequential model
        building process set this value to False
        and use methods `_add_parent_block_sets`,
        `_add_parent_block_variables`, `_add_blocks`, `_add_objective`

    Attributes
    ----------
    timeincrement : sequence
        Time increments
    flows : dict
        Flows of the model
    name : str
        Name of the model
    es : solph.EnergySystem
        Energy system of the model (upmost energy cell for cellular structures)
    meta : `pyomo.opt.results.results_.SolverResults` or None
        Solver results
    dual : `pyomo.core.base.suffix.Suffix` or None
        Store the dual variables of the model if pyomo suffix is set to IMPORT
    rc : `pyomo.core.base.suffix.Suffix` or None
        Store the reduced costs of the model if pyomo suffix is set to IMPORT
    """

    # The default list of constraint groups to be used for a model
    CONSTRAINT_GROUPS = []

    def __init__(self, energysystem, **kwargs):
        """Initialize a BaseModel, using its energysystem as well as
        optional kwargs for specifying the timeincrement, objective_weighting
        and constraint_groups."""
        super().__init__()

        # Check root logger. Due to a problem with pyomo the building of the
        # model will take up to a 100 times longer if the root logger is set
        # to DEBUG

        if getLogger().level <= 10 and kwargs.get("debug", False) is False:
            msg = (
                "The root logger level is 'DEBUG'.\nDue to a communication "
                "problem between solph and the pyomo package,\nusing the "
                "DEBUG level will slow down the modelling process by the "
                "factor ~100.\nIf you need the debug-logging you can "
                "initialise the Model with 'debug=True`\nYou should only do "
                "this for small models. To avoid the slow-down use the "
                "logger\nfunction of oemof.tools (read docstring) or "
                "change the level of the root logger:\n\nimport logging\n"
                "logging.getLogger().setLevel(logging.INFO)"
            )
            raise LoggingError(msg)

        # ########################  Arguments #################################

        self.name = kwargs.get("name", type(self).__name__)
        self.is_cellular = isinstance(energysystem, list)

        if self.is_cellular:
            self.es = energysystem[0]
            self.ec = energysystem[1:]
        else:
            self.es = energysystem
        self.timeincrement = kwargs.get("timeincrement", self.es.timeincrement)

        self.objective_weighting = kwargs.get(
            "objective_weighting",
            [1] * len(self.timeincrement)
            if self.timeincrement is not None
            else [1],
        )

        self._constraint_groups = type(self).CONSTRAINT_GROUPS + kwargs.get(
            "constraint_groups", []
        )

        if self.is_cellular:
            for es in energysystem:
                self._constraint_groups += [
                    i
                    for i in es.groups
                    if hasattr(i, "CONSTRAINT_GROUP")
                    and i not in self._constraint_groups
                ]
        else:
            self._constraint_groups += [
                i
                for i in self.es.groups
                if hasattr(i, "CONSTRAINT_GROUP")
                and i not in self._constraint_groups
            ]

        self.flows = self.es.flows()
        if self.is_cellular:
            for cell in self.ec:
                for io, f in cell.flows().items():
                    self.flows.update({io: f})

        self.solver_results = None
        self.dual = None
        self.rc = None

        if kwargs.get("auto_construct", True):
            self._construct()

    def _construct(self):
        """Construct a BaseModel by adding parent block sets and variables
        as well as child blocks and variables to it.
        """
        self._add_parent_block_sets()
        self._add_parent_block_variables()
        self._add_child_blocks()
        self._add_objective()

    def _add_parent_block_sets(self):
        """Method to create all sets located at the parent block, i.e. in the
        model itself, as they are to be shared across all model components.
        See the class :py:class:~oemof.solph._models.Model
        for the sets created.
        """
        pass

    def _add_parent_block_variables(self):
        """Method to create all variables located at the parent block,
        i.e. the model itself as these variables  are to be shared across
        all model components.
        See the class :py:class:~oemof.solph._models.Model
        for the `flow` variable created.
        """
        pass

    def _add_child_blocks(self):
        """Method to add the defined child blocks for components that have
        been grouped in the defined constraint groups. This collects all the
        constraints from the buses, components and flows blocks
        and adds them to the model.
        """
        for group in self._constraint_groups:
            # create instance for block
            block = group()
            # Add block to model
            self.add_component(str(block), block)
            # create constraints etc. related with block for all nodes
            # in the group
            block._create(group=self.es.groups.get(group))

    def _add_objective(self, sense=po.minimize, update=False):
        """Method to sum up all objective expressions from the child blocks
        that have been created. This method looks for `_objective_expression`
        attribute in the block definition and will call this method to add
        their return value to the objective function.
        """
        if update:
            self.del_component("objective")

        expr = 0

        for block in self.component_data_objects():
            if hasattr(block, "_objective_expression"):
                expr += block._objective_expression()

        self.objective = po.Objective(sense=sense, expr=expr)

    def receive_duals(self):
        """Method sets solver suffix to extract information about dual
        variables from solver. Shadow prices (duals) and reduced costs (rc) are
        set as attributes of the model.
        """
        # shadow prices
        self.dual = po.Suffix(direction=po.Suffix.IMPORT)
        # reduced costs
        self.rc = po.Suffix(direction=po.Suffix.IMPORT)

    def results(self):
        """Returns a nested dictionary of the results of this optimization.
        See the processing module for more information on results extraction.
        """
        return processing.results(self)

    def solve(self, solver="cbc", solver_io="lp", **kwargs):
        r"""Takes care of communication with solver to solve the model.

        Parameters
        ----------
        solver : string
            solver to be used e.g. "cbc", "glpk", "gurobi", "cplex"
        solver_io : string
            pyomo solver interface file format: "lp", "python", "nl", etc.
        \**kwargs : keyword arguments
            Possible keys can be set see below:

        Other Parameters
        ----------------
        solve_kwargs : dict
            Other arguments for the pyomo.opt.SolverFactory.solve() method
            Example : {"tee":True}
        cmdline_options : dict
            Dictionary with command line options for solver e.g.
            {"mipgap":"0.01"} results in "--mipgap 0.01"
            \{"interior":" "} results in "--interior"
            \Gurobi solver takes numeric parameter values such as
            {"method": 2}
        """
        solve_kwargs = kwargs.get("solve_kwargs", {})
        solver_cmdline_options = kwargs.get("cmdline_options", {})

        opt = SolverFactory(solver, solver_io=solver_io)
        # set command line options
        options = opt.options
        for k in solver_cmdline_options:
            options[k] = solver_cmdline_options[k]

        solver_results = opt.solve(self, **solve_kwargs)

        status = solver_results["Solver"][0]["Status"]
        termination_condition = solver_results["Solver"][0][
            "Termination condition"
        ]

        if status == "ok" and termination_condition == "optimal":
            logging.info("Optimization successful...")
        else:
            msg = (
                "Optimization ended with status {0} and termination "
                "condition {1}"
            )
            warnings.warn(
                msg.format(status, termination_condition), UserWarning
            )
        self.es.results = solver_results
        self.solver_results = solver_results

        return solver_results

    def relax_problem(self):
        """Relaxes integer variables to reals of optimization model self."""
        relaxer = RelaxIntegrality()
        relaxer._apply_to(self)

        return self


class Model(BaseModel):
    """An energy system model for operational and/or investment
    optimization.

    Parameters
    ----------
    energysystem : EnergySystem object or (experimental) list
        Object that holds the nodes of an oemof energy system graph.
        Experimental: If a list is passed, the list needs to hold EnergySystem
        objects and a cellular structure is assumed. In this case, the first
        element needs to be the upmost energy cell (structurally containing
        all other cells).
    constraint_groups : list
        Solph looks for these groups in the given energy system and uses them
        to create the constraints of the optimization problem.
        Defaults to `Model.CONSTRAINT_GROUPS`
    discount_rate : float or None
        The rate used for discounting in a multi-period model.
        A 2% discount rate needs to be defined as 0.02.

    Note
    ----

    * The discount rate is only applicable for a multi-period model.
    * If you want to work with costs data in nominal terms,
      you should specify a discount rate.
    * By default, there is a discount rate of 2% in a multi-period model.
    * If you want to provide your costs data in real terms,
      just specify `discount_rate = 0`, i.e. effectively there will be
      no discounting.


    **The following basic sets are created**:

    NODES
        A set with all nodes of the given energy system.

    TIMESTEPS
        A set with all timesteps of the given time horizon.

    PERIODS
        A set with all investment periods of the given time horizon.

    TIMEINDEX
        A set with all time indices of the given time horizon, whereby
        time indices are defined as a tuple consisting of the period and the
        timestep. E.g. (2, 10) would be timestep 10 (which is exactly the same
        as in the TIMESTEPS set) and which is in period 2.

    FLOWS
        A 2 dimensional set with all flows. Index: `(source, target)`

    **The following basic variables are created**:

    flow
        Flow from source to target indexed by FLOWS, TIMEINDEX.
        Note: Bounds of this variable are set depending on attributes of
        the corresponding flow object.

    """

    CONSTRAINT_GROUPS = [
        BusBlock,
        ConverterBlock,
        InvestmentFlowBlock,
        SimpleFlowBlock,
        NonConvexFlowBlock,
        InvestNonConvexFlowBlock,
    ]

    def __init__(self, energysystem, discount_rate=None, **kwargs):
        if discount_rate is not None:
            self.discount_rate = discount_rate
        elif (
            not isinstance(energysystem, list)
            and energysystem.periods is not None
        ):
            self._set_discount_rate_with_warning()
        elif (
            isinstance(energysystem, list)
            and energysystem[0].periods is not None
        ):
            self._set_discount_rate_with_warning()
        else:
            pass
        super().__init__(energysystem, **kwargs)

    def _set_discount_rate_with_warning(self):
        """
        Sets the discount rate to the standard value and raises a warning.
        """
        self.discount_rate = 0.02
        msg = (
            f"By default, a discount_rate of {self.discount_rate} "
            f"is used for a multi-period model. "
            f"If you want to use another value, "
            f"you have to specify the `discount_rate` attribute."
        )
        warnings.warn(msg, debugging.SuspiciousUsageWarning)

    def _add_parent_block_sets(self):
        """Add all basic sets to the model, i.e. NODES, TIMESTEPS and FLOWS.
        Also create sets PERIODS and TIMEINDEX used for multi-period models.
        """
        self.nodes = list(self.es.nodes)
        if self.is_cellular:
            # collect all nodes from the child cells
            for cell in self.ec:
                self.nodes.extend(cell.nodes)
        # create set with all nodes
        self.NODES = po.Set(initialize=[n for n in self.nodes])

        if self.es.timeincrement is None:
            msg = (
                "The EnergySystem needs to have a valid 'timeincrement' "
                "attribute to build a model."
            )
            raise AttributeError(msg)

        # pyomo set for timesteps of optimization problem
        self.TIMESTEPS = po.Set(
            initialize=range(len(self.es.timeincrement)), ordered=True
        )
        self.TIMEPOINTS = po.Set(
            initialize=range(len(self.es.timeincrement) + 1), ordered=True
        )

        if self.es.periods is None:
            self.TIMEINDEX = po.Set(
                initialize=list(
                    zip(
                        [0] * len(self.es.timeincrement),
                        range(len(self.es.timeincrement)),
                    )
                ),
                ordered=True,
            )
            self.PERIODS = po.Set(initialize=[0])
        else:
            nested_list = [
                [k] * len(self.es.periods[k])
                for k in range(len(self.es.periods))
            ]
            flattened_list = [
                item for sublist in nested_list for item in sublist
            ]
            self.TIMEINDEX = po.Set(
                initialize=list(
                    zip(flattened_list, range(len(self.es.timeincrement)))
                ),
                ordered=True,
            )
            self.PERIODS = po.Set(
                initialize=sorted(list(set(range(len(self.es.periods)))))
            )

        # (Re-)Map timesteps to periods
        timesteps_in_period = {p: [] for p in self.PERIODS}
        for p, t in self.TIMEINDEX:
            timesteps_in_period[p].append(t)
        self.TIMESTEPS_IN_PERIOD = timesteps_in_period

        # Set up disaggregated timesteps from original timeseries
        self.TSAM_MODE = False
        if self.es.tsa_parameters is None:
            self.tsam_weighting = [1] * len(self.timeincrement)
        else:
            self.TSAM_MODE = True

            # Construct weighting from occurrences and order
            self.tsam_weighting = list(
                self.es.tsa_parameters[p]["occurrences"][k]
                for p in self.PERIODS
                for k in range(len(self.es.tsa_parameters[p]["occurrences"]))
                for _ in range(
                    self.es.tsa_parameters[p]["timesteps"]
                )
            )
            self.CLUSTERS = po.Set(
                initialize=list(
                    range(
                        sum(
                            len(self.es.tsa_parameters[p]["order"])
                            for p in self.PERIODS
                        )
                    )
                )
            )
            self.CLUSTERS_OFFSET = po.Set(
                initialize=list(
                    range(
                        sum(
                            len(self.es.tsa_parameters[p]["order"])
                            for p in self.PERIODS
                        )
                        + 1
                    )
                )
            )
            self.TYPICAL_CLUSTERS = po.Set(
                initialize=[
                    (p, i)
                    for p in self.PERIODS
                    for i in range(
                        len(self.es.tsa_parameters[p]["occurrences"])
                    )
                ]
            )

            self.TIMEINDEX_CLUSTER = self.get_cluster_index("order", 0)
            self.TIMEINDEX_TYPICAL_CLUSTER = self.get_cluster_index(
                "occurrences", 0
            )
            self.TIMEINDEX_TYPICAL_CLUSTER_OFFSET = self.get_cluster_index(
                "occurrences", 1
            )

        # previous timesteps
        previous_timesteps = [x - 1 for x in self.TIMESTEPS]
        previous_timesteps[0] = self.TIMESTEPS.last()

        self.previous_timesteps = dict(zip(self.TIMESTEPS, previous_timesteps))

        # pyomo set for all flows in the energy system graph
        self.FLOWS = po.Set(
            initialize=self.flows.keys(), ordered=True, dimen=2
        )

        self.BIDIRECTIONAL_FLOWS = po.Set(
            initialize=[k for (k, v) in self.flows.items() if v.bidirectional],
            ordered=True,
            dimen=2,
            within=self.FLOWS,
        )

        self.UNIDIRECTIONAL_FLOWS = po.Set(
            initialize=[
                k for (k, v) in self.flows.items() if not v.bidirectional
            ],
            ordered=True,
            dimen=2,
            within=self.FLOWS,
        )

    def _add_parent_block_variables(self):
        """Add the parent block variables, which is the `flow` variable,
        indexed by FLOWS and TIMEINDEX."""
        self.flow = po.Var(self.FLOWS, self.TIMEINDEX, within=po.Reals)

        for o, i in self.FLOWS:
            if self.flows[o, i].nominal_value is not None:
                if self.flows[o, i].fix[self.TIMESTEPS.at(1)] is not None:
                    for p, t in self.TIMEINDEX:
                        self.flow[o, i, p, t].value = (
                            self.flows[o, i].fix[t]
                            * self.flows[o, i].nominal_value
                        )
                        self.flow[o, i, p, t].fix()
                else:
                    for p, t in self.TIMEINDEX:
                        self.flow[o, i, p, t].setub(
                            self.flows[o, i].max[t]
                            * self.flows[o, i].nominal_value
                        )
                    if not self.flows[o, i].nonconvex:
                        for p, t in self.TIMEINDEX:
                            self.flow[o, i, p, t].setlb(
                                self.flows[o, i].min[t]
                                * self.flows[o, i].nominal_value
                            )
                    elif (o, i) in self.UNIDIRECTIONAL_FLOWS:
                        for p, t in self.TIMEINDEX:
                            self.flow[o, i, p, t].setlb(0)
            else:
                if (o, i) in self.UNIDIRECTIONAL_FLOWS:
                    for p, t in self.TIMEINDEX:
                        self.flow[o, i, p, t].setlb(0)

    def get_timestep_from_tsam_timestep(self, p, ik, g):
        """Return original timestep from cluster-based timestep"""
        t = (
            p * len(self.TIMESTEPS_IN_PERIOD[p])
            + ik * self.es.tsa_parameters[p]["timesteps"]
            + g
        )
        return t

    def get_cluster_index(self, cluster_type, offset):
        """
        Return cluster index for original or typical periods with or
        without offset
        """
        return [
            (p, k, t)
            for p in range(len(self.es.tsa_parameters))
            for k in range(len(self.es.tsa_parameters[p][cluster_type]))
            for t in range(
                self.es.tsa_parameters[p]["timesteps"] + offset
            )
        ]
