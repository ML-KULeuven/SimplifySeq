import cpmpy as cp
from cpmpy.transformations.get_variables import get_variables as cpm_get_variables
from cpmpy.expressions.utils import flatlist

UNSAT = frozenset({cp.BoolVal(False)})
EPSILON = 0.01

def get_variables(obj):
    """
        Simple wrapper function around cpmpy's get_variables function.
        First convert any nested iterable to list, as CPMpy can only deal with lists.
    """
    return cpm_get_variables(flatlist([obj]))


def print_sequence(seq):
    for i, step in enumerate(seq):
        print(f"Step {i}:")
        print(f"  Input: {step['input']}")
        print(f"  Output: {step['output']}")
        print(f"  Constraints: {step['constraints']}")
        print()