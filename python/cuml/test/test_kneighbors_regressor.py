
# Copyright (c) 2019, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import numpy as np
import pytest

from cuml.neighbors import KNeighborsRegressor as cuKNN

from cuml.metrics import r2_score

from sklearn.datasets import make_regression

from sklearn.utils.validation import check_random_state
from sklearn.model_selection import train_test_split
from numpy.testing import assert_array_almost_equal


import cudf
import pandas as pd
import numpy as np
from cuml.test.utils import array_equal

import scipy.stats as stats


def unit_param(*args, **kwargs):
    return pytest.param(*args, **kwargs, marks=pytest.mark.unit)


def quality_param(*args, **kwargs):
    return pytest.param(*args, **kwargs, marks=pytest.mark.quality)


def stress_param(*args, **kwargs):
    return pytest.param(*args, **kwargs, marks=pytest.mark.stress)


def predict(neigh_ind, _y, n_neighbors):

    neigh_ind = neigh_ind.astype(np.int32)

    ypred, count = stats.mode(_y[neigh_ind], axis=1)
    return ypred.ravel(), count.ravel() * 1.0 / n_neighbors


def test_kneighbors_regressor(n_samples=40,
                              n_features=5,
                              n_test_pts=10,
                              n_neighbors=3,
                              random_state=0):
    # Test k-neighbors regression
    rng = np.random.RandomState(random_state)
    X = 2 * rng.rand(n_samples, n_features) - 1
    y = np.sqrt((X ** 2).sum(1))
    y /= y.max()

    y_target = y[:n_test_pts]

    knn = cuKNN(n_neighbors=n_neighbors)
    knn.fit(X, y)
    epsilon = 1E-5 * (2 * rng.rand(1, n_features) - 1)
    y_pred = knn.predict(X[:n_test_pts] + epsilon)
    assert np.all(abs(y_pred - y_target) < 0.3)


def test_KNeighborsRegressor_multioutput_uniform_weight():
    # Test k-neighbors in multi-output regression with uniform weight
    rng = check_random_state(0)
    n_features = 5
    n_samples = 40
    n_output = 4

    X = rng.rand(n_samples, n_features)
    y = rng.rand(n_samples, n_output)

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
    knn = cuKNN()
    knn.fit(X_train, y_train)

    neigh_idx = knn.kneighbors(X_test, return_distance=False).astype(np.int32)

    y_pred_idx = np.array([np.mean(y_train[idx], axis=0)
                           for idx in neigh_idx])

    y_pred = knn.predict(X_test)

    assert y_pred.shape[0] == y_test.shape[0]
    assert y_pred_idx.shape == y_test.shape
    assert_array_almost_equal(y_pred, y_pred_idx)


@pytest.mark.parametrize("nrows", [1000, 10000])
@pytest.mark.parametrize("ncols", [50, 100])
@pytest.mark.parametrize("n_neighbors", [1])
@pytest.mark.parametrize("n_informative", [2, 10])
def test_score(nrows, ncols, n_neighbors, n_informative):

    X, y = make_regression(n_samples=nrows, n_informative=n_informative,
                      n_features=ncols, random_state=0)

    X = X.astype(np.float32)

    knn_cu = cuKNN(n_neighbors=n_neighbors)
    knn_cu.fit(X, y)

    assert knn_cu.score(X, y) >= 0.9999
