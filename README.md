# SimplifySeq

This repostitory accompanies the following paper published at CP23:
> Bleukx, Ignace, et al. "Simplifying Step-wise Explanation Sequences." 29th International Conference on Principles and Practice of Constraint Programming (CP 2023). Schloss Dagstuhl-Leibniz-Zentrum für Informatik, 2023.

And provides algorithms to generate and post-process step-wise explanations sequences.
An explanation sequence explains a target set of literals by propagating small subsets of constraints. 
Each step in such a sequence takes as input literals derived in previous steps, and the constraints to be propagated.
The output of a step is a new set of literals.


The repository is organised as follows:
```bash
.
├── __init__.py                 
├── algorithms
|   ├── backward.py         # Algorithms for post-processing sequences
|   ├── datastructurs.py    # Datastructures used in algorithms and propagators
|   ├── forward.py          # Algorithms for sequence construction
|   ├── propagate.py        # Algorithms for (fully) propagating constraints
|   ├── subset.py           # Algortihms for finding unsatisfiable subsets of constraints
├── datasets.py   
|   ├── debug                # Unsatisfiable CSP's by introducing a modelling mistake in a CSP
|   ├── jobshop              # Jobshop-instances based on Trailmark
|   ├── sudoku               # Unsatisfiable Sudoku instances based on QQWING tool
├── tests                         # Unit tests to test all implemented algorithms
```

By creating and post-processing sequences with algorithms in the following order, resulting sequences will satisfy desirable properties such as Atomicity, Sparsity, Pertinence and Non-redundancy. More information about these properties can be found in the paper.

1) Greedy construct
2) Deletion-based filtering
3) Relaxation-based filtering

To use this repository, you need the following packages:
- CPMpy: a constraint modelling languages in which all of the algorithms are implemented
- Exact: a ILP-like solver which provides statefull propagation. This allows for efficient repeated propagation of (sets of) constraints.

```bash
pip install cpmpy exact
```
