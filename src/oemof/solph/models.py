# -*- coding: utf-8 -*-

"""Solph Optimization Models.

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Simon Hilpert
SPDX-FileCopyrightText: Cord Kaldemeyer
SPDX-FileCopyrightText: gplssm
SPDX-FileCopyrightText: Patrik Schönfeldt

SPDX-License-Identifier: MIT

"""
import logging
import warnings
from collections import defaultdict

from pyomo import environ as po
from pyomo.core.plugins.transform.relax_integrality import RelaxIntegrality
from pyomo.opt import SolverFactory

from oemof.solph import blocks
from oemof.solph import processing
from oemof.solph.plumbing import sequence


class BaseModel(po.ConcreteModel):
    """The BaseModel for other solph-models (Model, MultiPeriodModel, etc.)

    Parameters
    ----------
    energysystem : EnergySystem object
        Object that holds the nodes of an oemof energy system graph
    constraint_groups : list (optional)
        Solph looks for these groups in the given energy system and uses them
        to create the constraints of the optimization problem.
        Defaults to `Model.CONSTRAINTS`
    objective_weighting : array like (optional)
        Weights used for temporal objective function
        expressions. If nothing is passed `timeincrement` will be used which
        is calculated from the freq length of the energy system timeindex .
    auto_construct : boolean
        If this value is true, the set, variables, constraints, etc. are added,
        automatically when instantiating the model. For sequential model
        building process set this value to False
        and use methods `_add_parent_block_sets`,
        `_add_parent_block_variables`, `_add_blocks`, `_add_objective`

    Attributes:
    -----------
    timeincrement : sequence
        Time increments.
    flows : dict
        Flows of the model.
    name : str
        Name of the model.
    es : solph.EnergySystem
        Energy system of the model.
    meta : `pyomo.opt.results.results_.SolverResults` or None
        Solver results.
    dual : ... or None
    rc : ... or None

    """

    CONSTRAINT_GROUPS = []

    def __init__(self, energysystem, **kwargs):
        super().__init__()

        # ########################  Arguments #################################

        self.name = kwargs.get("name", type(self).__name__)
        self.es = energysystem
        self.timeincrement = sequence(
            kwargs.get("timeincrement", self.es.timeincrement)
        )
        if self.timeincrement[0] is None:
            try:
                self.timeincrement = sequence(
                    self.es.timeindex.freq.nanos / 3.6e12
                )
            except AttributeError:
                msg = (
                    "No valid time increment found. Please pass a valid "
                    "timeincremet parameter or pass an EnergySystem with "
                    "a valid time index. Please note that a valid time"
                    "index need to have a 'freq' attribute."
                )
                raise AttributeError(msg)

        self.objective_weighting = kwargs.get(
            "objective_weighting", self.timeincrement
        )

        self._constraint_groups = type(self).CONSTRAINT_GROUPS + kwargs.get(
            "constraint_groups", []
        )

        self._constraint_groups += [
            i
            for i in self.es.groups
            if hasattr(i, "CONSTRAINT_GROUP")
            and i not in self._constraint_groups
        ]

        self.flows = self.es.flows()

        self.solver_results = None
        self.dual = None
        self.rc = None

        if kwargs.get("auto_construct", True):
            self._construct()

    def _construct(self):
        """"""
        self._add_parent_block_sets()
        self._add_parent_block_variables()
        self._add_child_blocks()
        self._add_objective()

    def _add_parent_block_sets(self):
        """ " Method to create all sets located at the parent block, i.e. the
        model itself as they are to be shared across all model components.
        """
        pass

    def _add_parent_block_variables(self):
        """ " Method to create all variables located at the parent block,
        i.e. the model itself as these variables  are to be shared across
        all model components.
        """
        pass

    def _add_child_blocks(self):
        """Method to add the defined child blocks for components that have
        been grouped in the defined constraint groups.
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
        """Returns a nested dictionary of the results of this optimization"""
        return processing.results(self)

    def solve(self, solver="cbc", solver_io="lp", **kwargs):
        r"""Takes care of communication with solver to solve the model.

        Parameters
        ----------
        solver : string
            solver to be used e.g. "glpk","gurobi","cplex"
        solver_io : string
            pyomo solver interface file format: "lp","python","nl", etc.
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
            {"interior":" "} results in "--interior"
            Gurobi solver takes numeric parameter values such as
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
    """An  energy system model for operational and investment
    optimization.

    Parameters
    ----------
    energysystem : EnergySystem object
        Object that holds the nodes of an oemof energy system graph
    constraint_groups : list
        Solph looks for these groups in the given energy system and uses them
        to create the constraints of the optimization problem.
        Defaults to `Model.CONSTRAINTS`

    **The following basic sets are created**:

    NODES :
        A set with all nodes of the given energy system.

    TIMESTEPS :
        A set with all timesteps of the given time horizon.

    FLOWS :
        A 2 dimensional set with all flows. Index: `(source, target)`

    **The following basic variables are created**:

    flow
        Flow from source to target indexed by FLOWS, TIMESTEPS.
        Note: Bounds of this variable are set depending on attributes of
        the corresponding flow object.

    """

    CONSTRAINT_GROUPS = [
        blocks.Bus,
        blocks.Transformer,
        blocks.InvestmentFlow,
        blocks.Flow,
        blocks.NonConvexFlow,
    ]

    def __init__(self, energysystem, **kwargs):
        super().__init__(energysystem, **kwargs)

    def _add_parent_block_sets(self):
        """"""
        # set with all nodes
        self.NODES = po.Set(initialize=[n for n in self.es.nodes])

        # pyomo set for timesteps of optimization problem
        self.TIMESTEPS = po.Set(
            initialize=range(len(self.es.timeindex)), ordered=True
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
            initialize=[
                k
                for (k, v) in self.flows.items()
                if hasattr(v, "bidirectional")
            ],
            ordered=True,
            dimen=2,
            within=self.FLOWS,
        )

        self.UNIDIRECTIONAL_FLOWS = po.Set(
            initialize=[
                k
                for (k, v) in self.flows.items()
                if not hasattr(v, "bidirectional")
            ],
            ordered=True,
            dimen=2,
            within=self.FLOWS,
        )

    def _add_parent_block_variables(self):
        """"""
        self.flow = po.Var(self.FLOWS, self.TIMESTEPS, within=po.Reals)

        for (o, i) in self.FLOWS:
            if self.flows[o, i].nominal_value is not None:
                if self.flows[o, i].fix[self.TIMESTEPS[1]] is not None:
                    for t in self.TIMESTEPS:
                        self.flow[o, i, t].value = (
                            self.flows[o, i].fix[t]
                            * self.flows[o, i].nominal_value
                        )
                        self.flow[o, i, t].fix()
                else:
                    for t in self.TIMESTEPS:
                        self.flow[o, i, t].setub(
                            self.flows[o, i].max[t]
                            * self.flows[o, i].nominal_value
                        )

                    if not self.flows[o, i].nonconvex:
                        for t in self.TIMESTEPS:
                            self.flow[o, i, t].setlb(
                                self.flows[o, i].min[t]
                                * self.flows[o, i].nominal_value
                            )
                    elif (o, i) in self.UNIDIRECTIONAL_FLOWS:
                        for t in self.TIMESTEPS:
                            self.flow[o, i, t].setlb(0)
            else:
                if (o, i) in self.UNIDIRECTIONAL_FLOWS:
                    for t in self.TIMESTEPS:
                        self.flow[o, i, t].setlb(0)


class MultiObjectiveModel(Model):
    """An  energy system model for operational and investment
    optimization.

    Parameters
    ----------
    energysystem : EnergySystem object
        Object that holds the nodes of an oemof energy system graph
    constraint_groups : list
        Solph looks for these groups in the given energy system and uses them
        to create the constraints of the optimization problem.
        Defaults to `Model.CONSTRAINTS`

    **The following basic sets are created**:

    NODES :
        A set with all nodes of the given energy system.

    TIMESTEPS :
        A set with all timesteps of the given time horizon.

    FLOWS :
        A 2 dimensional set with all flows. Index: `(source, target)`

    **The following basic variables are created**:

    flow
        Flow from source to target indexed by FLOWS, TIMESTEPS.
        Note: Bounds of this variable are set depending on attributes of
        the corresponding flow object.

    """

    CONSTRAINT_GROUPS = [
        blocks.Bus,
        blocks.Transformer,
        blocks.InvestmentFlow,
        blocks.Flow,
        blocks.NonConvexFlow,
        blocks.MultiObjectiveFlow
    ]

    def __init__(self, energysystem, **kwargs):
        super().__init__(energysystem, **kwargs)

    def _add_objective(self, sense=po.minimize, update=False):
        """ Method to sum up all objective expressions from the child blocks
        that have been created. This method looks for `_objective_expression`
        attribute in the block definition and will call this method to add
        their return value to the objective function or to the respective
        objective function if multiple objective function keys are given.
        """

        if update:
            self.del_component('objective')

        # create dict for all distinct objective expressions
        self.objective_functions = defaultdict(lambda: 0, {'_standard': 0})

        # set sign based on optimisation sense
        if sense == po.minimize:
            sign = 1
        else:
            sign = -1

        for block in self.component_data_objects():
            if hasattr(block, '_objective_expression'):
                expr = block._objective_expression()
                if isinstance(expr, defaultdict):
                    for obj_key, obj_val in expr.items():
                        self.objective_functions[obj_key] += (
                            sign * obj_val)
                else:
                    self.objective_functions['_standard'] += (
                        sign * expr)

    def solve(self, solver='cbc', solver_io='lp', **kwargs):
        r""" Takes care of communication with solver to solve the model.
        Differentiates between single objective optimization or multi
        objective optimization. Defaults to single objective optimization.

        Parameters
        ----------
        solver : string
            solver to be used e.g. "glpk","gurobi","cplex"
        solver_io : string
            pyomo solver interface file format: "lp","python","nl", etc.
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
            {"interior":" "} results in "--interior"
            Gurobi solver takes numeric parameter values such as
            {"method": 2}
        optimization_type: str, default 'singular'
            Sets type of optimization, currently either 'singular' for single
            objective or 'weighted' for weighted sum of several objectives.
        objective (with 'singular'): str, default '_standard'
            Name of singular objective function to use. Defaults to internal
            standard name.
        objective_weights (with 'weighted'): dict, default {'_standard': 1}
            Dictionary with names of objectives as keys and numeric weights
            as values.
        """
        solve_kwargs = kwargs.get('solve_kwargs', {})
        solver_cmdline_options = kwargs.get("cmdline_options", {})

        opt = SolverFactory(solver, solver_io=solver_io)
        # set command line options
        options = opt.options
        for k in solver_cmdline_options:
            options[k] = solver_cmdline_options[k]

        # get type of optimisation
        optimization_type = kwargs.get('optimization_type', 'singular')

        # delete objective if it exists
        self.del_component('objective')

        if optimization_type == 'singular':
            # get function to use
            objective = kwargs.get('objective', '_standard')

            if not isinstance(objective, str):
                raise TypeError('Objective is not of type "string"')
            if objective not in self.objective_functions.keys():
                raise ValueError(
                    'No cost for objective "{0}"'.format(objective))

            # log objective
            logging.info('Objective set to {0}.'.format(objective))

            # set chosen objective function
            self.objective = po.Objective(
                sense=po.minimize,
                expr=self.objective_functions.get(objective, 0.0))

            solver_results = opt.solve(self, **solve_kwargs)

            status = solver_results["Solver"][0]["Status"]
            termination_condition = (
                solver_results["Solver"][0]["Termination condition"])

            if status == "ok" and termination_condition == "optimal":
                logging.info("Optimization successful...")
            else:
                msg = ("Optimization ended with status {0} and termination "
                       "condition {1}")
                warnings.warn(msg.format(status, termination_condition),
                              UserWarning)
            self.es.results = solver_results
            self.solver_results = solver_results

            return solver_results

        elif optimization_type == 'weighted':

            # get function names and weights to use
            obj_weights = kwargs.get(
                'objective_weights',
                {'_standard': 1})

            # check for correct type
            if not isinstance(obj_weights, dict):
                raise TypeError("Objective weights must be of type 'dict'.")

            # check existance of objectives
            if len(obj_weights) == 0:
                raise ValueError("Objective weights must not be empty.")

            # initialise weighted sum of objectives
            expr = 0

            # check and set objectives and weights
            for obj_name, obj_weight in obj_weights.items():
                if not isinstance(obj_name, str):
                    raise TypeError(
                        'Objective "{0}" is not of type "string"'.format(
                            obj_name))
                if obj_name not in self.objective_functions.keys():
                    raise ValueError('No cost for objective "{0}"'.format(
                        obj_name))

                # add to summed objective
                expr += (obj_weight
                         * self.objective_functions.get(obj_name))

            # log objective and weights
            logging.info('Objectives set to: {0} with weights: {1}'.format(
                ', '.join(obj_weights.keys()), str(obj_weights)))

            # create objective
            self.objective = po.Objective(sense=po.minimize, expr=expr)

            # solve
            solver_results = opt.solve(self, **solve_kwargs)

            status = solver_results["Solver"][0]["Status"]
            termination_condition = (
                solver_results["Solver"][0]["Termination condition"])

            if status == "ok" and termination_condition == "optimal":
                logging.info("Optimization successful...")
            else:
                msg = ("Optimization ended with status {0} and termination "
                       "condition {1}")
                warnings.warn(msg.format(status, termination_condition),
                              UserWarning)
            self.es.results = solver_results
            self.solver_results = solver_results

            return solver_results
        else:
            raise Exception('Invalid optimization type')
