from .utils import UNSAT
from .forward import construct_greedy
from .backward import relax_sequence, filter_sequence
from .propagate import ExactPropagate

def find_sequence(constraints, goal_literals=UNSAT, propagator=ExactPropagate, seed=0,time_limit=3600):
    """
        Find a sequence of constraints that explains the goal literals.
        :param constraints: a list of CPMpy constraints
        :param goal_literals: a set of literals that the sequence should explain, defaults to {False}
        :param PROP: the propagator to use, defaults to ExactPropagate
        :param time_limit: the time limit for the search
    """

    # construct initial sequence
    seq = construct_greedy(constraints, goal_literals, time_limit, seed, PROP=propagator)
    print("Found initial sequence of length", len(seq))

    # filter sequence
    seq = filter_sequence(seq, time_limit=time_limit, propagator_class=propagator)
    print("Filtered sequence of length", len(seq))

    # relax sequence
    seq = relax_sequence(seq, time_limit=time_limit)
    print("Relaxed sequence of length", len(seq))

    return seq