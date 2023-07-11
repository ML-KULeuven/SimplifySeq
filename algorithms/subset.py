from time import time
import cpmpy as cp


def _maxsat_grow(subset, dmap, hard):

    solver = cp.SolverLookup.get("ortools")
    solver += hard
    solver += cp.all(subset)
    for a, cons in dmap.items():
        solver += a.implies(cons)
    solver.maximize(cp.sum(list(dmap.keys())))
    return {a for a in dmap if not a.value()}

def _greedy_grow(dmap):
    sat_subset = {assump for assump, cons in dmap.items() if assump.value() or cons.value()}
    return set(dmap.keys()) - sat_subset

def _corr_subsets(subset, dmap, solver, hard):
    start_time = time()
    sat_subset = {s for s in subset}
    corr_subsets = []
    while solver.solve(assumptions=list(sat_subset)):
        corr_subset = _maxsat_grow(sat_subset, dmap, hard=hard)
        # corr_subset = _greedy_grow(dmap)
        if len(corr_subset) == 0:
            return corr_subsets
        sat_subset |= corr_subset
        corr_subsets.append(corr_subset)

    return corr_subsets

def ocus_oneof(soft, hard=[], oneof_idxes=[], weights=1, solver="ortools", hs_solver="ortools"):
    start_time = time()

    assump = cp.boolvar(shape=len(soft), name="assump")
    if len(soft) == 1:
        assump = cp.cpm_array([assump])
    m = cp.Model(hard + [assump.implies(soft)])  # each assumption variable implies a candidate
    dmap = dict(zip(assump, soft))
    s = cp.SolverLookup.get(solver, m)
    assert not s.solve(assumptions=assump), "MUS: model must be UNSAT"

    # hitting set solver stuff
    hs_solver = cp.SolverLookup.get(hs_solver)
    if len(oneof_idxes):
        hs_solver += cp.sum(assump[oneof_idxes]) == 1
    hs_solver.minimize(cp.sum(weights * assump))

    while hs_solver.solve():

        subset = assump[assump.value() == 1]
        if s.solve(assumptions=subset) is True:
            # grow subset while staying satisfiable under assumptions
            for grown in _corr_subsets(subset, dmap, s, hard=hard):
                hs_solver += cp.sum(grown) >= 1
        else:
            return [dmap[a] for a in subset]

def smus(soft, hard=[], weights=1, solver="ortools", hs_solver="ortools"):
    return ocus_oneof(soft, hard, [], weights, solver, hs_solver)