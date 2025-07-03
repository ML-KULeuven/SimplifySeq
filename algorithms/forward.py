from time import time
import logging
from itertools import combinations

import random
import numpy as np

from cpmpy.transformations.get_variables import get_variables
from cpmpy.transformations.normalize import toplevel_list

from .utils import EPSILON
from .propagate import MaximalPropagate, ExactPropagate
import cpmpy as cp


def connected_network(constraints):
    """
    Returns if the constraint network is connected or not
    """
    if len(constraints) == 1:
        return True # shortcut
    scopes = {cons : set(get_variables(cons)) for cons in constraints}
    occurs_in = {var : {c for c in constraints if var in scopes[c]} for var in set().union(*scopes.values())}
    # start at a random constraint and a random variable
    to_visit = {next(iter(scopes[constraints[0]]))}
    visited = set()
    while len(to_visit):
        # try constructing path over constraint graph that visits all
        to_visit -= visited
        var = to_visit.pop()
        # else, var not visisted, add all new vars to frontier reachable from this one using any constraint
        visited.add(var)
        for cons in occurs_in[var]:
            to_visit |= scopes[cons] - visited
    return len(visited) == len(set().union(*scopes.values()))



def smallest_next_step(current_literals, constraints, propagator, time_limit=3600):
    """
    Computes the smallest next step given input domains and a list of constraints.
    Iterate over all subsets of constraints and check if anything can be propagated
    :param domains: a set of literals that describes the current domains
    :param constraints: a list of CPMpy constraints
    :param propagator: a propagator, can be maximal but not required
    :return: a tuple of constraints and the new literals implied by it, given the input literals
    """

    start_time = time()
    literals_set = frozenset(current_literals)

    sorted(constraints, key=lambda x: str(x))
    candidates = []
    for size in range(1,len(constraints)+1):
        logging.info(f"Propagating constraint sets of size {size}")
        #print(f"Propagating constraint sets of size {size}")

        for i, cons in enumerate(combinations(constraints,size)):
            if time_limit - (time() - start_time) <= EPSILON:
                raise TimeoutError(f"'smallest_next_step' timed out after {time() - start_time} seconds")
            if size == 2:               
                if set(get_variables(cons[0])).isdisjoint(set(get_variables(cons[1]))):
                    # quick check if scopes are disjoint
                    continue # will never propagate anything new compared to single constraints
            elif not connected_network(cons):
                continue # will never propagate anything new compared to its strict subsets (which are already checked in previous iteration)

            propagated_lits = frozenset(propagator.propagate(current_literals, list(cons), time_limit=time_limit -(time() - start_time)))
            if propagated_lits == literals_set:
                # nothing propagated, skip
                continue                
            elif literals_set < propagated_lits or propagated_lits == frozenset([cp.BoolVal(False)]): # found some new literals
                # propagated something new, keep step
                return list(cons), list(propagated_lits)
            else:
                raise ValueError("The propagated domains are not a subset of the original domains, this should not happen!")
        if len(candidates):
            break # found all steps of smallest size, no need to test bigger steps!
    raise ValueError("Exhausted all subsets of constraints without sucessfull propagation, is the propagator maximal?")


def construct_greedy(constraints, goal_literals, time_limit, seed, PROP=ExactPropagate):

    # normalize constraints
    constraints = toplevel_list(constraints, merge_and=False)

    start_time = time()
    random.seed(seed)
    np.random.seed(seed)

    max_propagator = PROP(constraints=constraints, caching=True)
    seq = []

    literals = set()
    while 1:
        if time_limit - (time() - start_time) <= EPSILON:
            raise TimeoutError(f"'construct_greedy' timed out after {time() - start_time} seconds")

        # find next smallest step
        cons, new_literals = smallest_next_step(list(literals), 
                                                constraints, 
                                                max_propagator, 
                                                time_limit=time_limit - (time() - start_time))

        # construct new step        
        new_step = dict(type="step", 
                        input=frozenset(literals), 
                        constraints=frozenset(cons), 
                        output=frozenset(set(new_literals) - literals))
        
        literals = set(new_literals)

        seq.append(new_step)
        if set(goal_literals) <= set(literals): # found a sequence that explains the goal
            break

    return seq