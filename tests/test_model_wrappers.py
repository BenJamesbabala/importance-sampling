#
# Copyright (c) 2017 Idiap Research Institute, http://www.idiap.ch/
# Written by Angelos Katharopoulos <angelos.katharopoulos@idiap.ch>
#

from contextlib import contextmanager
import unittest

from blinker import signal
from keras.layers import Activation, Dense
from keras.models import Sequential
import numpy as np

from importance_sampling.model_wrappers import OracleWrapper
from importance_sampling.reweighting import BiasedReweightingPolicy


def log_signal(idx, n, success, fun):
    def inner(x):
        success[idx] = fun(idx, n)
    return inner


@contextmanager
def assert_signals(test, signal_name, fun=lambda x, n: True):
    if not isinstance(signal_name, (tuple, list)):
        signal_name = [signal_name]
    success = [False]*len(signal_name)
    loggers = [
        log_signal(i, n, success, fun)
        for i, n in
        enumerate(signal_name)
    ]
    for i, n in enumerate(signal_name):
        signal(n).connect(loggers[i])
    yield
    for n, s in zip(signal_name, success):
        test.assertTrue(s, msg=n + " signal was not received")


class TestModelWrappers(unittest.TestCase):
    def _get_model(self):
        model = Sequential([
            Dense(10, activation="relu", input_dim=2),
            Dense(10, activation="relu"),
            Dense(2),
            Activation("softmax")
        ])
        model.compile(loss="categorical_crossentropy", optimizer="adam")

        wrapped = OracleWrapper(model, BiasedReweightingPolicy(), score="loss")

        x = np.random.rand(16, 2)
        y = np.zeros((16, 2))
        y[range(16), np.random.choice(2, 16)] = 1.0

        return model, wrapped, x, y

    def test_model_methods(self):
        model, wrapped, x, y = self._get_model()

        scores = wrapped.score(x, y)
        self.assertTrue(np.all(scores == wrapped.score(x, y)))

        wl, _, sc = wrapped.train_batch(x, y, np.ones(16) * 0.5)
        self.assertTrue(np.all(wl*2 == sc))

        l = wrapped.evaluate(x, y)
        self.assertEqual(l.size, 1)
        l = wrapped.evaluate_batch(x, y)
        self.assertEqual(l.size, 16)

    def test_signals(self):
        model, wrapped, x, y = self._get_model()

        with assert_signals(self, ["is.evaluation", "is.evaluate_batch"]):
            wrapped.evaluate(x, y)
        with assert_signals(self, "is.score"):
            wrapped.score(x, y)
        with assert_signals(self, "is.training"):
            wrapped.train_batch(x, y, np.ones(len(x)))

    @unittest.skip("Not done yet")
    def test_metrics(self):
        pass

    @unittest.skip("Not done yet")
    def test_losses(self):
        pass



if __name__ == "__main__":
    unittest.main()
