import random

import cpmpy as cp
import numpy as np
import csv

def make_sudoku_unsat(givens, seed):
    givens = np.array(givens)
    dim,_ = givens.shape
    random.seed(seed)

    cells = cp.intvar(1,9, givens.shape, name="cells")
    idxes = [(i,j) for i in range(dim) for j in range(dim) if givens[i,j] == 0]

    m = cp.Model(cells[givens != 0] == givens[givens != 0])
    m += [cp.AllDifferent(row) for row in cells]
    m += [cp.AllDifferent(col) for col in cells.T]
    bs = int(dim ** 0.5)
    for i in range(0,dim, bs):
        for j in range(0,dim, bs):
            m += cp.AllDifferent(cells[i:i+bs, j:j+bs])

    assert m.solveAll() == 1
    while 1:
        # make 1 error
        i,j = random.choice(idxes)
        options = set(range(1,10))
        # delete correct value
        options.remove(cells[i,j].value())
        # delete row options
        options -= set(givens[i])
        # delete col options
        options -= set(givens[:,j])
        # delete block options, (i,j) lies in block (bv,bh)
        bv, bh = i // bs, j // bs
        options -= set(givens[bv * bs:(bv+1)*bs, bh*bs:(bh+1)*bs].flatten())
        if len(options): # could be no options are left (unlikely, but still it can happen)
            givens[i,j] = random.choice(list(options))
            m += cells[i,j] == givens[i,j]
            assert not m.solve()
            return {"givens": givens}


def load_and_make_unsat_sudoku(fname, seed=0):
    random.seed(seed)

    inst = load_csv_instance(fname)
    return make_sudoku_unsat(random.choice(inst), seed)


def load_csv_instance(fname):
    all_instances = []
    with open(fname) as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        for row in csv_reader:
            dim = int(len(row["Puzzle"]) ** (0.5))
            all_instances.append(np.array(
                [[int(row["Puzzle"][i * 9 + j]) for j in range(dim)] for i in range(dim)]
            ))
    return all_instances



def load_sudoku_csv_instances():
    """Load CSV instances in np.array format

    Returns:
        _type_: _description_
    """
    import os
    base_path = os.path.realpath(__file__).replace('sudoku.py', '')
    all_files = [
        "easy_sudokus.csv",
        "simple_sudokus.csv",
        "intermediate_sudokus.csv",
        "expert_sudokus.csv",
    ]
    all_instances = []
    for fname in all_files:
        all_instances += load_csv_instance(base_path + fname)
    return np.array(all_instances)

if __name__ == "__main__":
    instances = load_csv_instance("intermediate_sudokus.csv")
    inst = instances[0]

    print(make_sudoku_unsat(givens=inst, seed=0))