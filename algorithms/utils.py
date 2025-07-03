import cpmpy as cp
UNSAT = frozenset({cp.BoolVal(False)})

def print_sequence(seq):
    for i, step in enumerate(seq):
        print(f"Step {i}:")
        print(f"  Input: {step['input']}")
        print(f"  Output: {step['output']}")
        print(f"  Constraints: {step['constraints']}")
        print()