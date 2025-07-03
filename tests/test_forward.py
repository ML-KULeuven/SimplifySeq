import os
from unittest import TestCase

import cpmpy as cp

from ..algorithms.forward import construct_greedy
from ..algorithms.utils import UNSAT, print_sequence


class TestFoward(TestCase):


    def test_full(self):

        x, y, z = [cp.boolvar(name=n) for n in "xyz"]

        c1 = x + y + z <= 1
        c2 = x + y >= 1
        c3 = x + z >= 1
        c4 = y + z >= 1

        assert not cp.Model([c1, c2, c3, c4]).solve()
        seq = construct_greedy(constraints=[c1, c2, c3, c4],
                                 goal_literals= UNSAT,
                                 time_limit=120,
                                 seed=0)

        print_sequence(seq)

        self.assertEqual(len(seq),4)

