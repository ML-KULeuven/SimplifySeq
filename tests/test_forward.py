import os
from unittest import TestCase

import cpmpy as cp

from ..algorithms.forward import construct_greedy
from ..algorithms.datastructures import DomainSet
from ..algorithms.propagate import CPPropagate, MaximalPropagate, ExactPropagate
from ..experiments.models import _replace_varnames_constraint


class TestFoward(TestCase):


    def test_full(self):

        x, y, z = [cp.boolvar(name=n) for n in "xyz"]

        c1 = x + y + z <= 1
        c2 = x + y >= 1
        c3 = x + z >= 1
        c4 = y + z >= 1

        assert not cp.Model([c1, c2, c3, c4]).solve()
        seq = construct_greedy(constraints=[c1, c2, c3, c4],
                                 goal_reduction= DomainSet({v : frozenset() for v in [x,y,z]}),
                                 time_limit=900,
                                 seed=0)

        for step in seq:
            print(step)

        self.assertEqual(len(seq),4)

