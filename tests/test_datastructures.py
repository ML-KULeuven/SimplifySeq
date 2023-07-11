from unittest import TestCase

import cpmpy as cp

from cp23.algorithms.datastructures import DomainSet


class TestDomainReduction(TestCase):


    def test_construct(self):
        a,b,c = cp.intvar(0,10, shape=3)
        domains = DomainSet.from_vars([a,b,c])
        self.assertEqual(domains, DomainSet({var : frozenset(range(var.lb, var.ub+1)) for var in (a,b,c)}))

    def test_subset(self):
        a, b, c = [cp.intvar(0,10, name=n) for n in "abc"]

        assert DomainSet({a: {0, 1, 2}, b: {0}}) <= DomainSet({a: {0, 1, 2}, b: {0, 1}})
        assert DomainSet({a: {0, 1, 2}, b: {0}}) < DomainSet({a: {0, 1, 2}, b: {0, 1}})

        assert not DomainSet({a: {0, 1, 3}, b: {0}}) <= DomainSet({a: {0, 1, 2}, b: {0, 1}})
        assert not DomainSet({a: {0, 1, 2}, b: {0}}) < DomainSet({a: {0, 1, 2}, b: {0}})

    def test_literals(self):
        pass
