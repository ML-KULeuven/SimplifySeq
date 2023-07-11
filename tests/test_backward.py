from unittest import TestCase
import pickle

import cpmpy as cp
from cpmpy.expressions.variables import _IntVarImpl, _BoolVarImpl, NegBoolView
from cpmpy.expressions.utils import is_num

from ..algorithms.datastructures import DomainSet, Step
from ..algorithms.backward import filter_sequence, relax_sequence, filter_simple
from ..algorithms.propagate import ExactPropagate, MaximalPropagateSolveAll


class TestBackward(TestCase):

    def setUp(self) -> None:
        x, y, z = [cp.boolvar(name=n) for n in "xyz"]

        c1 = x
        c2 = ~z
        c3 = ~x | ~y
        c4 = ~x | y

        step1 = Step(
            DomainSet({x: frozenset({0, 1}), y: frozenset({0, 1}), z: frozenset({0, 1})}),
            [c1],
            DomainSet({x: frozenset({1}), y: frozenset({0, 1}), z: frozenset({0, 1})}),
            "max"
        )
        step2 = Step(
            DomainSet({x: frozenset({1}), y: frozenset({0, 1}), z: frozenset({0, 1})}),
            [c2],
            DomainSet({x: frozenset({1}), y: frozenset({0, 1}), z: frozenset({0})}),
            "max"
        )
        step3 = Step(
            DomainSet({x: frozenset({1}), y: frozenset({0,1}), z: frozenset({0})}),
            [c3],
            DomainSet({x: frozenset({1}), y: frozenset({0}), z: frozenset({0})}),
            "max"
        )
        step4 = Step(
            DomainSet({x: frozenset({1}), y: frozenset({0}), z: frozenset({0})}),
            [c4],
            DomainSet({x: frozenset(), y: frozenset(), z: frozenset()}),
            "max"
        )

        self.redundant_var_seq = [step1, step2, step3, step4]


    def test_filter_redundant_var(self):

        unsat = DomainSet({var : frozenset() for var in self.redundant_var_seq[0].Rin})
        filtered = filter_sequence(self.redundant_var_seq, goal_reduction=unsat, time_limit=100)
        self.assertEqual(len(filtered), 3)

    def test_filter_strongly_redundant(self):
        filtered = filter_simple(self.redundant_var_seq)
        self.assertEqual(len(filtered), 3)

    def test_relax_strongly_redundant(self):
        filtered = relax_sequence(self.redundant_var_seq)
        self.assertEqual(len(filtered), 3)


    def test_filter_weakly(self):
        x, y, z = [cp.boolvar(name=n) for n in "xyz"]

        step1 = Step(
            DomainSet({x: frozenset({0, 1}), y: frozenset({0, 1})}),
            [x], # this step is redundant
            DomainSet({x: frozenset({1}), y: frozenset({0, 1})}),
            "max"
        )
        step2 = Step(
            DomainSet({x: frozenset({1}), y: frozenset({0, 1})}),
            [x & y],
            DomainSet({x: frozenset({1}), y: frozenset({1})}),
            "max"
        )
        step3 = Step(
            DomainSet({x: frozenset({1}), y: frozenset({1})}),
            [~x | ~y],
            DomainSet({x: frozenset(), y: frozenset()}),
            "max"
        )

        unsat = DomainSet({var : frozenset({}) for var in [x,y]})
        filtered = filter_sequence([step1, step2, step3], goal_reduction=unsat, time_limit=100)

        self.assertEqual(len(filtered), 2)

    def test_relax(self):

        x,y,z = [cp.intvar(0,5, name=n) for n in "xyz"]

        step1 = Step(
            DomainSet.from_vars([x,y,z]),
            [x + y + z <= 1],
            DomainSet({x : frozenset({0,1}), y : frozenset({0,1}), z : frozenset({0,1})}),
            "max"
        )
        step2 = Step(
            DomainSet({x: frozenset({0, 1}), y: frozenset({0, 1}), z: frozenset({0, 1})}),
            [x >= 4],
            DomainSet({x : frozenset(), y : frozenset(), z : frozenset()}),
            "max"
        )

        relaxed = relax_sequence([step1, step2])

        self.assertEqual(len(relaxed), 2)
        self.assertSetEqual(step2.Rin[x], {0,1,2,3})
        self.assertSetEqual(step2.Rin[y], {0,1,2,3,4,5})
        self.assertSetEqual(step2.Rin[z], {0,1,2,3,4,5})

        self.assertSetEqual(set(), set().intersection(*[step.Rout[x] for step in relaxed]))

    def test_element(self):

        x = cp.intvar(0,4, shape=3)
        idx = cp.intvar(0,3)

        cons = 2 <= x[idx+1]

        all_cons = [cons]

        prop = MaximalPropagateSolveAll(all_cons)

        from cpmpy.transformations.get_variables import get_variables
        dom = DomainSet.from_literals(get_variables(all_cons), {})

        out = prop.propagate(dom, all_cons, time_limit=100)

        print(Step(dom, all_cons, out, type="max"))
