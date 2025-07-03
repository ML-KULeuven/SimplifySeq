import copy
from time import time
import logging

import cpmpy as cp
from cpmpy.tools.explain import mus, smus
from cpmpy.transformations.get_variables import get_variables

from .propagate import ExactPropagate, CPPropagate, filter_lits_to_vars
from .utils import EPSILON


def filter_sequence(seq, goal_literals, time_limit, propagator_class=ExactPropagate):
    """
    Filter sequence from redundant steps.
        loops over sequence from back to front and attempts to leave out a step
        if the remaining sequence is still valid, it is removed, otherwise the step is kept in the sequence
    """
    seq = copy.deepcopy(seq)
    goal_literals = frozenset(goal_literals)

    start_time = time()

    constraints = set().union(*[set(step['constraints']) for step in seq])
    propagator = propagator_class(list(constraints), caching=True)
    cp_propagator = CPPropagate(list(constraints), caching=False)

    def _has_conflict(literals, seq):
        # check if there is a conflict in the remainding constaints and given input literals
        cons = set().union(*[step['constraints'] for step in seq])
        return cp.Model(list(literals) + list(cons)).solve() is False

    unsat_sequences = dict() # cache unsat subsequences, mapping seq of constraints to set of literals
    sat_sequences = dict() # cache sat subsequences, mapping seq of constraints to set of literals

    def _try_deletion(lits_in, seq):
        # test if remaining sequence is still valid
        subsequences = dict()  # will encounter every subsequence maximum once, save whether it is sat or unsat

        current_lits = lits_in
        unsat = None
        for j, step in enumerate(seq):
            if time_limit - (time() - start_time) <= EPSILON:
                raise TimeoutError("Filtering timed out")
            
            current_lits = frozenset(current_lits)
            
            str_constraints = str([x['constraints'].__repr__() for x in seq[j:]]) # string representation of constraints, used in cache
            seq_vars = frozenset(get_variables([x['constraints'] for x in seq[j:]]))
            seq_lits = frozenset(filter_lits_to_vars(current_lits, seq_vars))
            
            step_vars = frozenset(get_variables(step['constraints']))
            step_lits = frozenset(filter_lits_to_vars(current_lits, step_vars))

            assert str_constraints not in subsequences, "We encountered this sequence already, should not happen!"
            subsequences[str_constraints] = seq_lits

            if goal_literals <= current_lits:
                # found the target, we can definitely stop
                unsat = True
                break
            elif step['input'] <= current_lits:
                # we know we can deduce Rout from Rin and S, so definitely from D and S
                # This holds for all remaining steps in the sequence assuming it was valid in the first place.
                # So the sequence is valid
                unsat = True
                break
            elif str_constraints in unsat_sequences and any(unsat_lits <= seq_lits for unsat_lits in unsat_sequences[str_constraints]):
                # we decided this sequence ends in UNSAT with less literals, so this one definitely
                unsat = True  # should never happen as input is maximal
                break
            elif str_constraints in sat_sequences and any(sat_lits >= seq_lits for sat_lits in sat_sequences[str_constraints]):
                # we decided this sequence ends in SAT with more literals, so this one definitely
                unsat = False
                break
            elif step_lits == frozenset(filter_lits_to_vars(step['input'], step_vars)):
                # relevant literals are the same as original input, so no need to propagate
                # output will be current input + original output of step
                step['output'] = current_lits | step['output']
                current_lits = step['output']
                continue
            elif _has_conflict(current_lits, seq[j:]):
                # there is still a conflict left based on constraints
                # can we get there using CP-propagation?
                lits_CP = copy.deepcopy(current_lits)
                for x in seq[j:]:
                    lits_CP = cp_propagator.propagate(list(lits_CP), list(x['constraints']), time_limit=time_limit - (time() - start_time))
                    # we can get the goal reduction using only CP-steps, so definitely using maxprop steps
                    if goal_literals <= lits_CP:
                        unsat = True
                        break
                if unsat is True: # reached goal using CP-propagation
                    break
                else: # could not get goal reduction using CP-propagationg CP-propagation
                    # go to default, re-compute step using maxprop
                    current_lits = propagator.propagate(current_lits, step['constraints'], time_limit=time_limit - (time() - start_time))       
            else:
                # no conflict left in constraints, definitely not in stepwise manner either
                unsat = False
                break

        if unsat is None:
            unsat = goal_literals <= current_lits

        dict_to_add = unsat_sequences if unsat else sat_sequences
        # store all subsequences we encountered along the way with their initial domain
        for seq, dom in subsequences.items():
            if seq in dict_to_add:
                dict_to_add[seq].add(dom)
            else:
                dict_to_add[seq] = {dom}

        return unsat

    # iterate over sequence from back to front
    i = len(seq)-1
    while i >= 0:
        # try deleting step i and check if still valid sequence
        if _try_deletion(seq[i]['input'], seq[i+1:]):
            seq.pop(i)
        i -= 1

    # now fixup all domains in the sequence
    # set input domain to given set

    current_literals = list()
    for i, step in enumerate(seq):
        step["input"] = frozenset(current_literals)
        
        new_literals = propagator.propagate(current_literals, step['constraints'], time_limit=time_limit-(time() - start_time))
        step["output"] = frozenset(set(new_literals) - step["input"])
        
        current_literals = list(new_literals)

        if goal_literals <= step['output']:
            return seq[:i+1] # can stop here

    return seq

def relax_sequence(seq, mus_solver="ortools", time_limit=3600):
    """
    Minimizes input literals for each step.
    Keeps a set of literals that need to be derived, only derive those in previous steps.
    """
    seq = copy.deepcopy(seq)

    start_time = time()

    all_constraints = set().union(*[set(step['constraints']) for step in seq])
    propagator = ExactPropagate(constraints = list(all_constraints))

    if len(seq) == 1:
        return seq

    required = mus(soft=list(seq[-1]['input']),
                   hard=list(seq[-1]['constraints']) + [~cp.all(list(seq[-1]['output']))],
                   solver=mus_solver)
    required = frozenset(required)
    seq[-1]['input'] = required
    i = len(seq)-2

    while i >= 0:
        if time_limit - (time() - start_time) <= EPSILON:
            raise TimeoutError("Relaxing sequence timed out")
        step = seq[i]
        # find the set of literals derived in this step we actually need later in the sequence
        newlits = step['output'] - step['input']
        new_required_lits = required & newlits
        step['output'] = new_required_lits
        if len(new_required_lits) == 0:
            # step can be removed from sequence as no newly derived literal is required
            # Note: this case should never occur when running on non-redundant sequences!
            seq.pop(i)
        else:
            # this step derives at least one new literal needed later on in the sequence, so we have to keep it
            # we have a preference over literals that we already need anyway
            already_needed = step['input'] & required
            maybe_needed = step['input'] - required

            extra_required_lits = mus(soft=list(maybe_needed),
                                      hard=list(already_needed) + list(step['constraints']) + [~cp.all(list(step['output']))],
                                      solver=mus_solver)
            
            already_required_lits = mus(soft=list(already_needed),
                                        hard=list(extra_required_lits) + list(step['constraints']) + [~cp.all(list(step['output']))],
                                        solver=mus_solver)
            
            step['input'] = frozenset(already_required_lits + extra_required_lits)

            # actually, we might be able to derive more than was originally "new"!
            new_output = propagator.propagate(step['input'], step['constraints'], time_limit=time_limit - (time() - start_time))
            step['output'] = (frozenset(new_output) - step['input']) & required

            required = (required - step['output']) | step['input']
            
        i -= 1
    return make_pertinent(seq)


def make_pertinent(seq):
    """
        Make sequence pertinent. i.e., remove literals that are already derived
    """
    derived_already = set()
    need_lits = set().union(*[step['input'] for step in seq] + [seq[-1]['output']])

    for step in seq:
        outlits = ((step['output'] - step['input']) & need_lits) - derived_already
        step['output'] = outlits
        derived_already |= outlits
    return seq


def seq_is_pertinent(seq):
    """
        Check if a sequence is pertinent.
        i.e., no literals are derived in a step that are already derived in a previous step.
    """
    derived_already = set()
    for step in seq:
        if len(step['output'] & derived_already) or len(step['input'] & step['output']):
            return False
        derived_already |= set(step['output'])
    return True
