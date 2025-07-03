

from unittest import TestCase

from ..algorithms.propagate import CPPropagate, MaximalPropagate, ExactPropagate, MaximalPropagateSolveAll
import cpmpy as cp

class PropagateTests(TestCase):

    def setUp(self):
        self.PROP = MaximalPropagate # default propagator

    def test_unit(self):
        
        x = cp.intvar(0,5, shape=3, name="x")

        c1 = cp.sum(x) <= 2
        propagator = self.PROP([c1], caching=False)

        literals = frozenset()
        literals_should = literals | set().union(*[{v != 3, v != 4, v != 5} for v in x])
        new_literals = propagator.propagate(literals, c1,time_limit=10)

        self.assertSetEqual(literals_should, new_literals)

        # now try with caching
        propagator = self.PROP([c1], caching=True)
        new_literals = propagator.propagate(literals, c1, time_limit=10)
        self.assertSetEqual(literals_should, new_literals)

    def test_bools(self):

        a = cp.boolvar(name="a")
        b = cp.boolvar(name="b")

        literals = frozenset()
        literals_should = frozenset({a != 0, b != 0})

        propagator = self.PROP(constraints=[a & b])
        new_literals = propagator.propagate(literals, a & b, time_limit=10)

        self.assertSetEqual(literals_should, new_literals)

    def test_advanced(self):

        if self.PROP == CPPropagate:
            return # not a maximal propagator, skip test
        
        x,y,z = [cp.boolvar(name=n) for n in "xyz"]

        c1 = x + y + z <= 1
        c2 = x + y >= 1
        c3 = x + z >= 1
        c4 = y + z >= 1

        domains = frozenset()
        propagator = MaximalPropagate([c1,c2,c3,c4])

        new_literals = propagator.propagate(domains, [c1,c2], time_limit=10)
        literals_should = frozenset({z != 1})
        self.assertEqual(new_literals, literals_should)

        new_literals = propagator.propagate(domains, [c1, c3], time_limit=10)
        literals_should = frozenset({y != 1})
        self.assertEqual(new_literals, literals_should)

        new_literals = propagator.propagate(domains, [c1,c2,c3], time_limit=10)
        literals_should = frozenset({x != 0, y != 1, z != 1})
        self.assertEqual(new_literals, literals_should)

    def test_alldiff(self):

        x = cp.intvar(1,4,shape=4, name="x")
        
        cons = cp.AllDifferent(x)
        propagator = self.PROP([cons])
        
        literals = frozenset()
        new_literals = propagator.propagate(literals, [cons], time_limit=10)
        self.assertSetEqual(literals, new_literals) # cannot propagate anything here

        literals = frozenset({x[0] != 2, x[0] != 3, x[0] != 4})
        new_literals = propagator.propagate(literals, [cons], time_limit=10)
        literals_should = literals | frozenset({var != 1 for var in x[1:]})

        self.assertSetEqual(new_literals, literals_should)

class TestCPPropagate(PropagateTests):

    def setUp(self):
        self.PROP = CPPropagate


class TestMaximalPropagate(PropagateTests):

    def setUp(self):
        self.PROP = MaximalPropagate

class TestMaximalPropagateSolveAll(PropagateTests):

    def setUp(self):
        self.PROP = MaximalPropagateSolveAll

class TestExactPropagate(PropagateTests):

    def setUp(self):
        self.PROP = ExactPropagate

   

    # def test_MaxPropagate(self):
    #     x,y,z = [cp.boolvar(name=n) for n in "xyz"]

    #     c1 = x + y + z <= 1
    #     c2 = x + y >= 1
    #     c3 = x + z >= 1
    #     c4 = y + z >= 1

    #     domains = DomainSet({var: frozenset(range(var.lb, var.ub + 1)) for var in [x,y,z]})
    #     propagator = MaximalPropagate([c1,c2,c3,c4])

    #     new_domains = propagator.propagate(domains, [c1,c2], time_limit=10)
    #     domains_should = DomainSet({x: frozenset({0, 1}), y: frozenset({0, 1}), z: frozenset({0})})
    #     self.assertEqual(new_domains, domains_should)

    #     new_domains = propagator.propagate(domains, [c1, c3], time_limit=10)
    #     domains_should = DomainSet({x: frozenset({0, 1}), y: frozenset({0}), z: frozenset({0,1})})
    #     self.assertEqual(new_domains, domains_should)

    #     new_domains = propagator.propagate(domains, [c1, c2,c3], time_limit=10)
    #     domains_should = DomainSet({x: frozenset({1}), y: frozenset({0}), z: frozenset({0})})
    #     self.assertEqual(new_domains, domains_should)


    # def test_MaxPropagateAll_unit(self):

    #     x = cp.intvar(0,5, shape=3, name="x")

    #     c1 = cp.sum(x) <= 2
    #     propagator = MaximalPropagateSolveAll([c1], caching=False)

    #     literals = frozenset()
    #     literals_should = literals | set().union(*[{v != 3, v != 4, v != 5} for v in x])
    #     new_literals = propagator.propagate(literals, c1,time_limit=10)

    #     self.assertSetEqual(literals_should, new_literals)

    #     # now try with caching
    #     propagator = MaximalPropagateSolveAll([c1], caching=True)
    #     new_literals = propagator.propagate(literals, c1, time_limit=10)
    #     self.assertSetEqual(literals_should, new_literals)


    # def test_MaxpropagateAll_bools(self):

    #     a = cp.boolvar(name="a")
    #     b = cp.boolvar(name="b")

    #     domains = DomainSet({a : frozenset({0,1}), b : frozenset({0,1})})
    #     domains_should = DomainSet({a : frozenset({1}), b : frozenset({1})})

    #     propagator = MaximalPropagateSolveAll([a & b])
    #     new_domains = propagator.propagate(domains, [a & b], time_limit=10)

    #     self.assertEqual(domains_should, new_domains)


    # def test_MaxPropagateAll(self):
    #     x,y,z = [cp.boolvar(name=n) for n in "xyz"]

    #     c1 = x + y + z <= 1
    #     c2 = x + y >= 1
    #     c3 = x + z >= 1
    #     c4 = y + z >= 1

    #     domains = DomainSet({var: frozenset(range(var.lb, var.ub + 1)) for var in [x,y,z]})
    #     propagator = MaximalPropagateSolveAll([c1,c2,c3,c4])

    #     new_domains = propagator.propagate(domains, [c1,c2], time_limit=10)
    #     domains_should = DomainSet({x: frozenset({0, 1}), y: frozenset({0, 1}), z: frozenset({0})})
    #     self.assertEqual(new_domains, domains_should)

    #     new_domains = propagator.propagate(domains, [c1, c3], time_limit=10)
    #     domains_should = DomainSet({x: frozenset({0, 1}), y: frozenset({0}), z: frozenset({0,1})})
    #     self.assertEqual(new_domains, domains_should)

    #     new_domains = propagator.propagate(domains, [c1, c2,c3], time_limit=10)
    #     domains_should = DomainSet({x: frozenset({1}), y: frozenset({0}), z: frozenset({0})})
    #     self.assertEqual(new_domains, domains_should)

    # def test_ExactPropagate_unit(self):
    #     x = cp.intvar(0, 5, shape=3, name="x")
    #     y = cp.intvar(0, 3, shape=3, name="y")
    #     vars = [v for v in x] + [v for v in y]

    #     c1 = cp.sum(x) <= 2
    #     propagator = ExactPropagate([c1], caching=False)

    #     domains = DomainSet({var: frozenset(range(var.lb, var.ub + 1)) for var in vars})
    #     domains_should = domains | DomainSet({var: frozenset(range(0, 3)) for var in x})
    #     new_domains = propagator.propagate(domains, c1, time_limit=10)

    #     self.assertEqual(domains_should, new_domains)

    #     # now try with caching
    #     propagator = ExactPropagate([c1], caching=True)
    #     new_domains = propagator.propagate(domains, c1, time_limit=10)
    #     self.assertEqual(domains_should, new_domains)
    #     new_domains = propagator.propagate(domains, c1, time_limit=10)
    #     self.assertEqual(domains_should, new_domains)


    # def test_Exactpropagate_bools(self):

    #     a = cp.boolvar(name="a")
    #     b = cp.boolvar(name="b")

    #     domains = DomainSet({a : frozenset({0,1}), b : frozenset({0,1})})
    #     domains_should = DomainSet({a : frozenset({1}), b : frozenset({1})})

    #     propagator = ExactPropagate([a & b])
    #     new_domains = propagator.propagate(domains, [a & b], time_limit=10)

    #     self.assertEqual(domains_should, new_domains)


    # def test_ExactPropagate(self):
    #     x,y,z = [cp.boolvar(name=n) for n in "xyz"]

    #     c1 = x + y + z <= 1
    #     c2 = x + y >= 1
    #     c3 = x + z >= 1
    #     c4 = y + z >= 1

    #     domains = DomainSet({var: frozenset(range(var.lb, var.ub + 1)) for var in [x,y,z]})
    #     propagator = ExactPropagate([c1,c2,c3,c4])

    #     new_domains = propagator.propagate(domains, [c1,c2], time_limit=10)
    #     domains_should = DomainSet({x: frozenset({0, 1}), y: frozenset({0, 1}), z: frozenset({0})})
    #     self.assertEqual(new_domains, domains_should)

    #     new_domains = propagator.propagate(domains, [c1, c3], time_limit=10)
    #     domains_should = DomainSet({x: frozenset({0, 1}), y: frozenset({0}), z: frozenset({0,1})})
    #     self.assertEqual(new_domains, domains_should)

    #     new_domains = propagator.propagate(domains, [c1, c2,c3], time_limit=10)
    #     domains_should = DomainSet({x: frozenset({1}), y: frozenset({0}), z: frozenset({0})})
    #     self.assertEqual(new_domains, domains_should)

    # def test_ExactAlldifferent(self):
    #     x = cp.intvar(1,4,shape=4)
        
    #     cons = cp.AllDifferent(x)
    #     propagator = ExactPropagate([cons])
        
    #     domains = DomainSet({var : frozenset(range(1,5)) for var in x})
    #     new_domains = propagator.propagate(domains, [cons], time_limit=10)
    #     self.assertEqual(domains, new_domains) # cannot propagate anything here

    #     domains |= DomainSet({x[0] : frozenset({1})})
    #     new_domains = propagator.propagate(domains, [cons], time_limit=10)
    #     domains_should = DomainSet({var : frozenset({2,3,4}) for var in x})
    #     domains_should |= DomainSet({x[0] : frozenset({1})})

    #     print("new domains")
    #     print(new_domains)

    #     print("domains_should")
    #     print(domains_should)

    #     self.assertEqual(new_domains, domains_should)

    # def test_ExactTimeOut(self):
    #     x = cp.intvar(0,100, shape=20)

    #     cons = 100 == cp.max(x)

    #     propagator = ExactPropagate([cons])

    #     domains = {var : frozenset(range(var.lb, var.ub+1)) for var in x}
    #     do_propagate = lambda: propagator.propagate(domains, [cons], time_limit=0.1)
    #     self.assertRaises(TimeoutError, do_propagate)