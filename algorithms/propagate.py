import cpmpy as cp
from cpmpy.transformations.get_variables import get_variables
from cpmpy.expressions.utils import is_any_list
from cpmpy.expressions.core import Comparison, Expression, BoolVal
from cpmpy.expressions.variables import _NumVarImpl
from cpmpy.tools.explain.utils import make_assump_model
from cpmpy.solvers.solver_interface import ExitStatus
from cpmpy.transformations.normalize import toplevel_list

def filter_lits_to_vars(literals, vars):
    vars = frozenset(vars)
    
    cons_lits= set()
    for lit in literals:
        if set(get_variables(lit)) & vars:
            cons_lits.add(lit)

    return list(cons_lits)


def allowed_domain(literals, vars):
    domainset = {var : set(range(var.lb, var.ub+1)) for var in vars}
    for lit in literals:
        if isinstance(lit, BoolVal) and lit.value() is False:
            return {var : set() for var in vars}
        assert isinstance(lit, Comparison)
        assert lit.name == "!="
        lhs, rhs = lit.args
        assert isinstance(lhs, _NumVarImpl)
        assert isinstance(rhs, int)
        if lhs in domainset:
            domainset[lhs].remove(rhs)

    return domainset


class Propagator:

    def __init__(self, constraints: list, caching=True):
        # bi-level cache with level 1 = constraint(s), level 2 = domains,
        self.cache = dict() if caching else None
        self.vars = set(get_variables(constraints))
        self.scope_cache = dict()
        assert is_any_list(constraints), f"expected list but got {type(constraints)}"
        for cons in constraints:
            self.scope_cache[cons] = frozenset(get_variables(cons))

    def _probe_cache(self, literals, constraints):
        if self.cache is None: return None

        assert isinstance(literals, list)

        if isinstance(constraints, Expression):
            constraints = [constraints]
        cons_vars = frozenset(get_variables(constraints))
        assert isinstance(constraints, list)

        constraints = frozenset(constraints)
        if constraints not in self.cache:
            return None

        cons_lits = filter_lits_to_vars(literals, cons_vars)

        # convert to frozenset for hashing
        cons_lits = frozenset(cons_lits)
        return self.cache[constraints].get(cons_lits)


    def _fill_cache(self, literals, constraints, new_lits):
        if self.cache is None: return None

        assert isinstance(constraints, list)

        if isinstance(constraints, Expression):
            constraints = [constraints]

        cons_vars = frozenset(get_variables(constraints))

        constraints = frozenset(constraints)
        cons_lits = frozenset(filter_lits_to_vars(literals, cons_vars))
        new_lits = frozenset(filter_lits_to_vars(new_lits, cons_vars))

        if constraints not in self.cache:
            self.cache[constraints] = dict()

        self.cache[constraints][cons_lits] = new_lits
        return new_lits

    def propagate(self, domains, constraints, time_limit):
        raise NotImplementedError(f"Propagation for propagator {type(self)} not implemented")


class MaximalPropagate(Propagator):
    """ Naive implementation of maximal propagation.
        Enumerates solutions ensuring at least variable has an unseen variable
    """

    def propagate(self, literals, constraints, solver="ortools",time_limit=3600):
        """
            Find all literals that are implied by the constraints an input literals.
            Also returns input literals, as they are trivially implied.
        """

        literals = list(literals)
        constraints = toplevel_list(constraints, merge_and=False)

        # check cache
        cached = self._probe_cache(literals, constraints)
        if cached is not None: return cached | literals # re-add input literals

        solver = cp.SolverLookup.get(solver)
        solver += list(literals) + list(constraints)
        cons_vars = set(get_variables(constraints))

        values_seen = {var : set() for var in cons_vars}
        while solver.solve(time_limit=time_limit) is True:
            time_limit = time_limit - solver.status().runtime
            if time_limit <= 0:
                raise TimeoutError("Time limit reached during maximal propagation")

            for var in cons_vars:
                values_seen[var].add(var.value())
            
            # find at least one new value for a variable
            clause = []
            for var in cons_vars:
                clause += [var == val for val in set(range(var.lb, var.ub+1)) - values_seen[var]]
            solver += cp.any(clause)

        if any(len(values_seen[var]) == 0 for var in cons_vars):
            return {BoolVal(False)}

        new_lits = []
        for var in cons_vars:
            new_lits += [var != val for val in set(range(var.lb, var.ub+1)) - values_seen[var]]

        self._fill_cache(literals, constraints, new_lits)
        new_lits = frozenset(new_lits) | frozenset(literals) # also input counts

        return new_lits


class MaximalPropagateSolveAll(Propagator):
    """ Alternative implementation of maximal propagate using OR-tools' solveAll function
        Enumerates all solutions of the constraints, and post-processes them to find all possible values for each variable
        Can be more efficient than MaximalPropagate if solutions are sparse.
    """

    def propagate(self, literals, constraints, solver="ortools", time_limit=3600):
        """
            Find all literals that are implied by the constraints an input literals.
            Also returns input literals, as they are trivially implied.
        """

        literals = list(literals)
        constraints = toplevel_list(constraints, merge_and=False)

        # check cache
        cached = self._probe_cache(literals, constraints)
        if cached is not None: return cached

        # only care about variables in constraints
        cons_vars = set(get_variables(constraints))

        solver = cp.SolverLookup.get(solver)
        solver += filter_lits_to_vars(literals, cons_vars)
        solver += constraints

        visited = {var: set() for var in cons_vars}
        def callback():
            for var in cons_vars:
                visited[var].add(var.value())
        num_sols = solver.solveAll(display=callback, time_limit=time_limit)

        if solver.status().runtime >= time_limit:
            raise TimeoutError

        if num_sols == 0:
            assert solver.status().exitstatus == ExitStatus.UNSATISFIABLE
            return {cp.BoolVal(False)}

        new_lits = []
        for var, dom in visited.items():
            new_lits += [var != val for val in set(range(var.lb, var.ub+1)) - dom]

        # store new domains in cache
        self._fill_cache(literals, constraints, new_lits)
        new_lits = frozenset(new_lits) | frozenset(literals) # also input counts

        return new_lits


class ExactPropagate(Propagator):
    """ Exact propagation using the exact solver.
        Uses Exacts' builtin domain pruning method.
        Stateful, so can be used repeatedly without re-initializing the solver.
    """

    def __init__(self, constraints, caching=True):
        super().__init__(constraints, caching)

        # initialize solver and do all necesessary things in background
        model, soft, assump = make_assump_model(soft=constraints)
        self.cons_dict = dict(zip(soft, assump))
        self.solver = cp.SolverLookup.get("exact")
        self.solver.encoding = "onehot"
        self.solver += model.constraints
        assert self.solver.solve()

    def propagate(self, literals, constraints, time_limit=3600):
        """
            Find all literals that are implied by the constraints an input literals.
            Also returns input literals, as they are trivially implied.
        """

        literals = list(literals)
        constraints = toplevel_list(constraints, merge_and=False)
        
        # check cache
        cached = self._probe_cache(literals, constraints)
        if cached is not None: 
            return list(frozenset(cached) | frozenset(literals)) # re-add input literals

        self.solver.xct_solver.clearAssumptions()
        if len(constraints) == 0:
            cons_vars = get_variables(literals)
        else:
            cons_vars = get_variables(constraints)
        domainset = allowed_domain(literals, cons_vars)

        # set assumptions related to domains
        assump_list = []
        for var, values in dict(domainset).items():
            if set(values) == set(range(var.lb,var.ub+1)):
                continue # full domain, do not set assumptions
            elif len(values) == 0: # empty domain, conflict
                return {BoolVal(False)}
            else:
                assump_list.append((self.solver.solver_var(var), list(values)))

        self.solver.xct_solver.setAssumptionsList(assump_list)

        # set assumptions for constraints
        if len(constraints) > 0:
            assump = self.solver.solver_vars([self.cons_dict[c] for c in constraints])
            self.solver.xct_solver.setAssumptions(list(zip(assump, [1]*len(constraints))))

        status, new_domains = self.solver.xct_solver.pruneDomains(vars=self.solver.solver_vars(cons_vars),
                                                                  timeout=time_limit)
        

        if status == "TIMEOUT":
            raise TimeoutError
        elif status == "INCONSISTENT":
            return {BoolVal(False)}
        elif status == "SAT":
            new_lits = []
            for var, dom in zip(cons_vars, new_domains):
                new_lits += [var != val for val in set(range(var.lb, var.ub + 1)) - set(dom)]

            # store new domains in cache
            self._fill_cache(literals, constraints, new_lits)
            new_lits = frozenset(new_lits) | frozenset(literals)  # also input counts

            return new_lits

        else:
            raise ValueError("Unexpected status", status)


class CPPropagate(Propagator):
    """
        Propagatoar using OR-Tools' presolve function
        Does root-level propagation so (much) weaker than MaximalPropagate, but very fast.
    """

    # Required parameters to use the presolve function as propagator
    req_kwargs = dict(
        stop_after_presolve=True,
        keep_all_feasible_solutions_in_presolve=True,
        fill_tightened_domains_in_response=True
    )

    # If we want true unit propagation, we need the following parameters
    prop_kwargs = dict(
        cp_model_probing_level = 0,
        presolve_bve_threshold = -1,
        presolve_probing_deterministic_time_limit = 0,
        presolve_blocked_clause = False,
        presolve_use_bva = False,
        max_presolve_iterations = 1,
        table_compression_level = 0,
        merge_no_overlap_work_limit = 0,
        merge_at_most_one_work_limit = 0,
        presolve_substitution_level = 0,
        presolve_inclusion_work_limit = 0,
    )

    def propagate(self, literals, constraints, time_limit, only_unit_propagation=True):
        
        literals = list(literals)
        constraints = toplevel_list(constraints, merge_and=False)

        # check cache       
        cached = self._probe_cache(literals, constraints)
        if cached is not None: 
            return list(frozenset(cached) | frozenset(literals)) # re-add input literals

        # only care about domains of variables in constraints
        cons_vars = set(get_variables(constraints))

        solver = cp.SolverLookup.get("ortools")
        solver += constraints
        solver += literals

        
        if only_unit_propagation:
            solver.solve(**self.req_kwargs, **self.prop_kwargs)
        else:
            solver.solve(**self.req_kwargs)

        bounds = solver.ort_solver.ResponseProto().tightened_variables

        if len(bounds) == 0:
            # UNSAT, no propagation possible
            return frozenset({BoolVal(False)})
    
        else:
            # convert bounded domains to != literals
            new_lits = []
            for var in cons_vars:
                ort_var = solver.solver_var(var)
                var_bounds = bounds[ort_var.Index()].domain

                lbs = [val for i, val in enumerate(var_bounds) if i % 2 == 0]
                ubs = [val for i, val in enumerate(var_bounds) if i % 2 == 1]

                prop_dom = set()
                for lb, ub in zip(lbs, ubs):
                    prop_dom |= set(range(lb, ub + 1))
                
                new_lits += [var != val for val in set(range(var.lb, var.ub + 1)) - prop_dom]

            # store new domains in cache
            self._fill_cache(literals, constraints, new_lits)
            new_lits = frozenset(new_lits) | frozenset(literals) # also input counts

            return new_lits