import copy
import random
from time import time

import cpmpy as cp
print(cp.__path__)

from cpmpy.transformations.get_variables import get_variables
from cpmpy.expressions.core import Operator, Comparison
from cpmpy.expressions.variables import _BoolVarImpl, NegBoolView
from cpmpy.expressions.globalconstraints import *
from cpmpy.expressions.utils import is_any_list, flatlist, is_bool, is_int, is_num, eval_comparison
from cpmpy.solvers.solver_interface import ExitStatus

TIME_LIMIT = 60


def make_model_unsat(constraints, p_change=0.1, seed=0):
    random.seed(seed)

    start_time = time()
    callback = callback_factory(constraints)

    it = 0
    while callback(TIME_LIMIT - (time() - start_time)):
        print(f"\rAt iteration {it}", end="\t\t\t")
        icons = [(i,c) for i,c in enumerate(constraints)]
        random.shuffle(icons)
        for i, cons in icons:
            if time() - start_time >= TIME_LIMIT:
                print()
                raise TimeoutError("Make model unsat timed out")
            if callback(TIME_LIMIT - (time() - start_time)):
                changed_cons = change_constraint_with_prob(cons,
                                                            p_change,
                                                            should_continue=callback,
                                                            time_limit=TIME_LIMIT - (time() - start_time))
                constraints[i] = changed_cons

        it += 1
    print()
    return constraints

def callback_factory(constraints):

    history = dict()
    def callback(time_limit):
        # print(constraints)
        if str(constraints) not in history:
            # solving model
            model = cp.Model(constraints)
            res = model.solve(time_limit=int(time_limit))
            if model.status().exitstatus == ExitStatus.UNKNOWN:
                raise TimeoutError("Callback timed out")
            history[str(constraints)] = res
        return history[str(constraints)]

    return callback


def change_constraint_with_prob(cpm_expr_orig, p_change=0.1, should_continue=lambda:False, time_limit=60):

    start_time = time()
    cpm_expr = copy.deepcopy(cpm_expr_orig)
    try:
        # sample action
        if not should_continue(time_limit - (time() - start_time)):
            return cpm_expr
        action = random.choice([swap_variables, replace_constraint, modify_constant])
        if random.random() <= p_change:
            cpm_expr = action(cpm_expr)
    except RuleNotApplicableError:
        # chosen rule was not applicable, continue
        pass

    if hasattr(cpm_expr, "args"):
        iargs = [(i,e) for i,e in enumerate(cpm_expr.args)]
        random.shuffle(iargs)
        for i, arg in iargs:
            if time() - start_time >= TIME_LIMIT:
                raise TimeoutError("change constraint timed out")
            cpm_expr.args[i] = change_constraint_with_prob(arg, p_change, should_continue, time_limit=time_limit - (time() - start_time))

    if str(cpm_expr) != str(cpm_expr_orig) and isinstance(cpm_expr, Expression) and cpm_expr.is_bool() and not cp.Model(cpm_expr).solve():
        # we do not want a trivial unsatisfiable constraints as this does not make for good explanation sequences
        return cpm_expr_orig

    return cpm_expr


def swap_variables(cpm_expr, var1=None, var2=None):
    """
        Swaps two variables in constraint
        Changes constraint inplace
    """
    if var1 is None or var2 is None:
        vars = get_variables(cpm_expr)
        if len(vars) <= 1:
            raise RuleNotApplicableError()
        var1 = random.choice(vars)
        vars = [var for var in vars if str(var) != str(var1) and var.is_bool() == var1.is_bool()]
        if len(vars) <= 0:
            raise RuleNotApplicableError()
        var2 = random.choice(vars)

    assert (isinstance(var1, _BoolVarImpl) and isinstance(var2, _BoolVarImpl)) or \
           (not isinstance(var1, _BoolVarImpl) and not isinstance(var2, _BoolVarImpl))

    # if we change the names of variables inplace, it will also change in other constraints...
    #   this might actually undo previous swaps... so lets replace the variables in this constraint only
    #   requires to walk through the expression tree and change variables everywhere in the arguments
    if hasattr(cpm_expr, "args"):
        for i, arg in enumerate(list(cpm_expr.args)):
            if str(arg) == str(var1):
                cpm_expr.args[i] = var2
            elif str(arg) == str(var2):
                cpm_expr.args[i] = var1
            else:
                cpm_expr.args[i] = swap_variables(arg, var1, var2)

    return cpm_expr


def replace_constraint(cpm_expr):
    if isinstance(cpm_expr, NegBoolView):
        return remove_negation(cpm_expr)
    if isinstance(cpm_expr, Operator):
        return replace_operator(cpm_expr)
    if isinstance(cpm_expr, Comparison):
        return replace_comparison(cpm_expr)
    if isinstance(cpm_expr, GlobalConstraint):
        return replace_global(cpm_expr)
    return cpm_expr


def modify_constant(cpm_expr):
    """
        Changing constants in place.
        Negates numeric constants
    """
    if is_bool(cpm_expr):
        cpm_expr = not cpm_expr
    elif is_num(cpm_expr):
        if random.choice([True, False]):
            cpm_expr = -cpm_expr
        else:
            cpm_expr = cpm_expr + 1
    return cpm_expr


def remove_negation(cpm_expr):
    """
        Remove boolvar negations in place
    """
    return ~cpm_expr


def replace_operator(cpm_expr):
    """
        Replace (numerical) operator with another one
        Ensures arity is correct so no obvious error
    """
    if not isinstance(cpm_expr, Operator):
        raise RuleNotApplicableError()

    arity, is_bool = Operator.allowed[cpm_expr.name]
    if cpm_expr.name == "wsum":
        arity = 0

    options = []
    for n, (a,ib) in Operator.allowed.items():
        arity_matches = a == arity or a == 0 or n == "wsum"
        excl_opertors = n != "mod" and n != "pow" and n != "div" and n != cpm_expr.name
        if (arity_matches and excl_opertors and ib == is_bool):
            options += [n]

    new_op = random.choice(options)
    if new_op == "wsum":
        weights = [random.randint(0,100) for _ in cpm_expr.args]
        args = [weights, cpm_expr.args]
    elif cpm_expr.name == "wsum":
        args = cpm_expr.args[1] # drop weights
    else:
        args = cpm_expr.args

    return Operator(name=new_op, arg_list=args)


def replace_comparison(cpm_expr):
    """
        Replace comparison with another comparison
    """
    if not isinstance(cpm_expr, Comparison):
        raise RuleNotApplicableError()

    options = [n for n in Comparison.allowed if n != cpm_expr.name]
    new_name = random.choice(options)
    lhs, rhs = cpm_expr.args
    return eval_comparison(new_name, lhs, rhs)

def replace_global(cpm_expr):
    """
        Replace global constraint with another one
    """

    if not isinstance(cpm_expr, GlobalConstraint):
        raise RuleNotApplicableError()

    # element constraint, introduce off-by-1 error
    if cpm_expr.name == "element":
        return Element(cpm_expr.args[0], cpm_expr.args[1]+1)

    # boolean globals
    bool_options = [
        AllDifferent,
        AllDifferentExcept0,
        AllEqual,
        Circuit
    ]
    if any(isinstance(cpm_expr, t) for t in bool_options):
        # arity will match, make new global constraint
        options = [t for t in bool_options if not isinstance(cpm_expr, t)]
        new_op = random.choice(options)
        return new_op(cpm_expr.args)

    # numerical globals
    num_options = [Maximum, Minimum]
    if any(isinstance(cpm_expr, t) for t in num_options):
        # arity will match, make new global constraint
        options = [t for t in num_options if not isinstance(cpm_expr, t)]
        new_op = random.choice(options)
        return new_op(cpm_expr.args)

    return cpm_expr

class RuleNotApplicableError(Exception):
    pass


if __name__ == "__main__":
    import os

    dirname = "pickled"
    outdir = "pickled_unsat_new"
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    fnames = os.listdir(dirname)
    already_done = set(os.listdir(outdir))

    skip = { # all of these timed out
        "a_17b2023_01_11.pkl",
        "a_2012_CMO_problem2023_01_11.pkl",
        "averbach_1_22023_01_11.pkl",
        "bananas2023_01_11.pkl",
        "building_a_house2023_01_11.pkl",
        "bus_scheduling_csplib2023_01_11.pkl",
        "candies2023_01_11.pkl",
        "calvin_puzzle2023_01_11.pkl",
        "clique2023_01_11.pkl",
        "equal_sized_groups2023_01_11.pkl",
        "euler12023_01_11.pkl",
        "frog_circle2023_01_11.pkl",
        "generating_numbers22023_01_11.pkl",
        "knights_path2023_01_11.pkl",
        "langford2023_01_11.pkl",
        "polydivisible_numbers2023_01_11.pkl"
    }

    already_done |= skip

    for fname in sorted(set(fnames) - already_done):
        model = cp.Model.from_file(os.path.join(dirname, fname))
        cons = flatlist(model.constraints)
        if 1 < len(cons) <= 1000:
            print(f"Making model {fname} unsat. Model has {len(cons)} constraints")
        else:
            print(f"Skipping model {fname} as it has too many or too little constraints ({len(cons)})")
            continue

        try:
            unsat_cons = make_model_unsat(cons, p_change=0.1,seed=0)
            unsat_model = cp.Model(unsat_cons)
            assert unsat_model.solve() is False
            unsat_model.to_file(os.path.join(outdir, fname))
        except TimeoutError as e:
            print(e)




