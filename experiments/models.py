import pickle

import brotli
import numpy as np

import cpmpy as cp
from cpmpy.expressions.utils import all_pairs, flatlist, is_num, is_any_list
from cpmpy.expressions.variables import _BoolVarImpl, _IntVarImpl, NegBoolView, NDVarArray

def jobshop_model_cumulative(n_jobs=None, task_to_mach=None, duration=None, precedence=None, horizon=None, **kwargs):

    if n_jobs is None or task_to_mach is None or duration is None or precedence is None or horizon is None:
        raise ValueError("No parameters can be None")

    # convert to numpy
    task_to_mach = np.array(task_to_mach)
    duration = np.array(duration)
    precedence = np.array(precedence)

    machines = set(task_to_mach.flatten().tolist())

    model = cp.Model()

    # decision variables
    start = cp.intvar(0,horizon, shape=task_to_mach.shape, name="start")
    end = cp.intvar(0,horizon, shape=task_to_mach.shape, name="end")
    makespan = cp.intvar(0,horizon, name="makespan")

    # precedence constraints
    for chain in precedence:
        for (j1, t1), (j2, t2) in zip(chain[:-1], chain[1:]):
            model += end[j1,t1] <= start[j2,t2]

    # cumulative constraints per machine
    for m in machines:
        tasks_on_mach = np.where(task_to_mach == m)
        model += cp.Cumulative(start[tasks_on_mach],
                           duration[tasks_on_mach],
                           end[tasks_on_mach],
                           demand=1, capacity=1)

    last_times = [end[j,t] for j,t in precedence[:,-1]]
    model += makespan == cp.max(last_times)

    model.minimize(makespan)
    return model, (start, end, makespan)


def sudoku_model(givens=None):
    assert givens is not None

    givens = np.array(givens)
    from math import sqrt
    dim = givens.shape[0]

    cells = cp.intvar(1,dim, shape=(dim,dim), name="cells")
    bsize = int(sqrt(dim))

    model = cp.Model()

    # alldiff row
    model += [cp.AllDifferent(row) for row in cells]
    # alldiff col
    model += [cp.AllDifferent(col) for col in cells.T]
    # alldiff blocks
    for i in range(0,dim, bsize):
        for j in range(0, dim, bsize):
            model += [cp.AllDifferent(cells[i:i+bsize, j:j+bsize])]

    # givens must match
    model += [cells[givens != 0] == givens[givens != 0]]

    return model, (cells,)



def _replace_varnames_constraint(constraint):
    if is_any_list(constraint):
        new_elements = [_replace_varnames_constraint(e) for e in constraint]
        if isinstance(constraint, NDVarArray):
            return cp.cpm_array(new_elements)
        else:
            return new_elements

    if hasattr(constraint, "args"):
        for i, arg in enumerate(constraint.args):
            constraint.args[i] = _replace_varnames_constraint(arg)
        return constraint
    elif isinstance(constraint, NegBoolView):
        return ~cp.boolvar(name=constraint._bv.name.replace("BV", "bv"))
    elif isinstance(constraint, _BoolVarImpl):
        return cp.boolvar(name=constraint.name.replace("BV", "bv"))
    elif isinstance(constraint, _IntVarImpl):
        return cp.intvar(constraint.lb, constraint.ub, name=constraint.name.replace("IV", "iv"))
    elif is_num(constraint):
        return constraint
    else:
        raise ValueError("Unknown expression:", constraint)

def load_unsat_model(filename):
    print("Loading", filename)
    model = cp.Model.from_file(filename)
    constraints = _replace_varnames_constraint(model.constraints)

    assert cp.Model(constraints).solve() is False, f"Model should be UNSAT! {filename}"
    return cp.Model(constraints), ()

def load_optimization_model(filename):
    if filename.endswith(".bt"):
        with open(filename, "rb") as f:
            return pickle.loads(brotli.decompress(f.read())), ()
    else:
        return cp.Model.from_file(filename), ()

