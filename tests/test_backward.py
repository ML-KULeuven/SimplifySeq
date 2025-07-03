from unittest import TestCase
import pickle

import cpmpy as cp
from cpmpy.expressions.variables import _IntVarImpl, _BoolVarImpl, NegBoolView

from ..algorithms.backward import filter_sequence, relax_sequence
from ..algorithms.propagate import ExactPropagate, MaximalPropagateSolveAll
from ..algorithms.utils import UNSAT, print_sequence


class TestBackward(TestCase):

    def setUp(self) -> None:
        x, y, z = [cp.boolvar(name=n) for n in "xyz"]

        c1 = x
        c2 = ~z
        c3 = ~x | ~y
        c4 = ~x | y

        step1 = dict(
            input=frozenset(),
            constraints=[c1],
            output=frozenset({x != 0}),
        )

        step2 = dict(
            input=frozenset({x != 0}),
            constraints=[c2],
            output=frozenset({z != 1}),
        )

        step3 = dict(
            input=frozenset({x != 0, z != 1}),
            constraints=[c3],
            output=frozenset({y != 1}),
        )

        step4 = dict(
            input=frozenset({x != 0, z != 1, y != 1}),
            constraints=[c4],
            output=UNSAT,
        )

        self.redundant_var_seq = [step1, step2, step3, step4]

    def test_filter_redundant_var(self):

        filtered = filter_sequence(self.redundant_var_seq, goal_literals=UNSAT, time_limit=100)
        self.assertEqual(len(filtered), 3)


    def test_relax_strongly_redundant(self):
        filtered = relax_sequence(self.redundant_var_seq, time_limit=100)
        self.assertEqual(len(filtered), 3)


    def test_filter_weakly(self):
        x, y, z = [cp.boolvar(name=n) for n in "xyz"]

        step1 = dict( # this step is redundant
            input = frozenset(),
            constraints = [x],
            output = frozenset({x != 0}),
        )

        step2 = dict(
            input= frozenset({x != 0}),
            constraints = [x & y],
            output = frozenset({x != 0, y != 0}),
        )

        step3 = dict(
            input = frozenset({x != 0, y != 0}),
            constraints = [~x | ~y],
            output = UNSAT,
        )

        filtered = filter_sequence([step1, step2, step3], goal_literals=UNSAT, time_limit=100)

        self.assertEqual(len(filtered), 2)

    def test_relax(self):

        x,y,z = [cp.intvar(0,5, name=n) for n in "xyz"]

        step1 = dict(
            input = frozenset(),
            constraints = [x + y + z <= 1],
            output = set().union(*[{v != 2, v != 3, v != 4, v != 5} for v in [x,y,z]])
        )

        step2 = dict(
            input = step1['output'],
            constraints = [x >= 4],
            output = UNSAT
        )

        relaxed = relax_sequence([step1, step2])

        self.assertEqual(len(relaxed), 2)
        self.assertSetEqual(relaxed[1]['input'], {x != 4, x != 5})
        