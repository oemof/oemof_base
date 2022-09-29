# -*- coding: utf-8 -*-

"""Constraints to relate variables in an existing model.

SPDX-FileCopyrightText: Jann Launer

SPDX-License-Identifier: MIT
"""
from pyomo import environ as po


def set_idle_time(model, f1, f2, n, name_constraint="constraint_idle_time"):
    r"""
    Adds a constraint to the given model that enforces f1 to be inactive
    for n timesteps before f2 can be active.

    For each timestep status of f2 can only be active if f1 has been inactive
    the previous n timesteps.

    **Constraints:**

    .. math:: X_1(s) + X_2(t) <= 1 \forall 0 < t < n, 0 \le s \le t
    .. math:: X_1(s) + X_2(t) <= 1 \forall t \ge n, t-n \le s \le t

    Parameters
    ----------
    model : oemof.solph.Model
        Model to which the constraint is added.
    f1 : tuple
        First flow tuple.
    f2 : tuple
        Second flow tuple. Has to be inactive for a defined number of
        timesteps after first flow was active.
    n : int
        Number of timesteps f2 has to be inactive after f1 has been active.
    name_constraint : str, default='constraint_idle_time'
        Name for the equation e.g. in the LP file.

    Returns
    -------
    the updated model.
    """
    # make sure that idle time is not longer than number of timesteps
    n_timesteps = len(model.TIMESTEPS)
    assert n_timesteps > n, (
        f"Selected idle time {n}"
        f"is longer than total number of timesteps {n_timesteps}"
    )

    # Create an index for the idle time
    model.idle_time = po.RangeSet(0, n)

    def _idle_rule(m):
        # In the first n steps, the status of f1 has to be inactive
        # for f2 to be active. For all following timesteps, f1 has to be
        # inactive in the preceding window of n timesteps for f2 to be active.
        for ts in list(m.TIMESTEPS):
            for delay in model.idle_time:

                if ts - delay < 0:
                    continue

                expr = (
                    m.NonConvexFlowBlock.status[f2[0], f2[1], ts]
                    + m.NonConvexFlowBlock.status[f1[0], f1[1], ts - delay]
                    <= 1
                )
                if expr is not True:
                    getattr(m, name_constraint).add((ts, ts - delay), expr)

    setattr(
        model,
        name_constraint,
        po.Constraint(
            [
                (t, t - delay)
                for t in model.TIMESTEPS
                for delay in model.idle_time
            ],
            noruleinit=True,
        ),
    )

    setattr(
        model,
        name_constraint + "_build",
        po.BuildAction(rule=_idle_rule),
    )

    return model
