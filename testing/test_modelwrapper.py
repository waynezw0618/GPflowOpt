import GPflowOpt
import unittest
import GPflow
import numpy as np
from .utility import create_parabola_model

float_type = GPflow.settings.dtypes.float_type


class MethodOverride(GPflowOpt.models.ModelWrapper):

    def __init__(self, m):
        super(MethodOverride, self).__init__(m)
        self.A = GPflow.param.DataHolder(np.array([1.0]))

    @GPflow.param.AutoFlow((float_type, [None, None]))
    def predict_f(self, Xnew):
        """
        Compute the mean and variance of held-out data at the points Xnew
        """
        m, v = self.build_predict(Xnew)
        return self.A * m, v

    @property
    def X(self):
        return self.wrapped.X

    @X.setter
    def X(self, Xc):
        self.wrapped.X = Xc

    @property
    def foo(self):
        return 1

    @foo.setter
    def foo(self, val):
        self.wrapped.foo = val


class TestModelWrapper(unittest.TestCase):

    def setUp(self):
        self.m = create_parabola_model(GPflowOpt.domain.UnitCube(2))

    def test_object_integrity(self):
        w = GPflowOpt.models.ModelWrapper(self.m)
        self.assertEqual(w.wrapped, self.m)
        self.assertEqual(self.m._parent, w)
        self.assertEqual(w.optimize, self.m.optimize)

    def test_optimize(self):
        w = GPflowOpt.models.ModelWrapper(self.m)
        logL = self.m.compute_log_likelihood()
        self.assertTrue(np.allclose(logL, w.compute_log_likelihood()))

        # Check if compiled & optimized, verify attributes are set in the right object.
        w.optimize(maxiter=5)
        self.assertTrue(hasattr(self.m, '_minusF'))
        self.assertFalse('_minusF' in w.__dict__)
        self.assertGreater(self.m.compute_log_likelihood(), logL)

    def test_af_storage_detection(self):
        # Regression test for a bug with predict_f/predict_y... etc.
        x = np.random.rand(10,2)
        self.m.predict_f(x)
        self.assertTrue(hasattr(self.m, '_predict_f_AF_storage'))
        w = MethodOverride(self.m)
        self.assertFalse(hasattr(w, '_predict_f_AF_storage'))
        w.predict_f(x)
        self.assertTrue(hasattr(w, '_predict_f_AF_storage'))

    def test_set_wrapped_attributes(self):
        # Regression test for setting certain keys in the right object
        w = GPflowOpt.models.ModelWrapper(self.m)
        w._needs_recompile = False
        self.assertFalse('_needs_recompile' in w.__dict__)
        self.assertTrue('_needs_recompile' in self.m.__dict__)
        self.assertFalse(w._needs_recompile)
        self.assertFalse(self.m._needs_recompile)

    def test_double_wrap(self):
        n = GPflowOpt.models.ModelWrapper(MethodOverride(self.m))
        n.optimize(maxiter=10)
        Xt = np.random.rand(10, 2)
        n.predict_f(Xt)
        self.assertFalse('_predict_f_AF_storage' in n.__dict__)
        self.assertTrue('_predict_f_AF_storage' in n.wrapped.__dict__)
        self.assertFalse('_predict_f_AF_storage' in n.wrapped.wrapped.__dict__)

        n = MethodOverride(GPflowOpt.models.ModelWrapper(self.m))
        Xn = np.random.rand(10, 2)
        Yn = np.random.rand(10, 1)
        n.X = Xn
        n.Y = Yn
        self.assertTrue(np.allclose(Xn, n.wrapped.wrapped.X.value))
        self.assertTrue(np.allclose(Yn, n.wrapped.wrapped.Y.value))
        self.assertFalse('Y' in n.wrapped.__dict__)
        self.assertFalse('X' in n.wrapped.__dict__)

        n.foo = 5
        self.assertTrue('foo' in n.wrapped.__dict__)
        self.assertFalse('foo' in n.wrapped.wrapped.__dict__)

    def test_name(self):
        n = GPflowOpt.models.ModelWrapper(self.m)
        self.assertEqual(n.name, 'unnamed.modelwrapper')
        p = GPflow.param.Parameterized()
        p.model = n
        self.assertEqual(n.name, 'model.modelwrapper')
        n = MethodOverride(create_parabola_model(GPflowOpt.domain.UnitCube(2)))
        self.assertEqual(n.name, 'unnamed.methodoverride')



