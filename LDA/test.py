import numpy as np
import scipy.sparse as sp

from sklearn.utils.testing import assert_true
from sklearn.utils.testing import raises
from sklearn.utils.testing import assert_array_almost_equal
from sklearn.utils.testing import assert_greater
from sklearn.utils.testing import assert_equal
from sklearn.utils.testing import if_not_mac_os
from sklearn.externals.six.moves import xrange

from lda import _split_sparse, _min_batch_split, _n_fold_split
from lda import onlineLDA


def _build_sparse_mtx():
    """
    Create 3 topics and each have 3 words
    """
    n_topics = 3
    alpha0 = eta0 = 1. / n_topics
    block = n_topics * np.ones((3, 3))
    X = sp.block_diag([block] * n_topics).tocsr()
    return n_topics, alpha0, eta0, X


def test_split_sparse():
    """
    test `_split_sparse`
    """
    rng = np.random.RandomState(0)
    n_row = 18
    n_col = 3
    batch_sizes = [3, 4, 5, 6]
    X = rng.randint(5, size=(n_row, n_col))
    X = sp.csr_matrix(X)

    X_batchs = []
    for size, batch_X in zip(batch_sizes, _split_sparse(X, batch_sizes)):
        assert_true(batch_X.shape[0] == size)
        X_batchs.append(batch_X)

    # rebuild from batchs should get X
    X_2 = sp.vstack(X_batchs)
    assert_array_almost_equal(X.todense(), X_2.todense())


def test_n_fold_split():
    """
    test `_n_fold_split`
    """
    rng = np.random.RandomState(0)
    n_row = rng.randint(20, 40)
    n_col = rng.randint(3, 6)
    n_fold = rng.randint(3, 8)

    X = rng.randint(5, size=(n_row, n_col))
    X = sp.csr_matrix(X)

    max_fold_size = int(np.ceil(float(n_row) / n_fold))

    X_batchs = []
    for batch_X in _n_fold_split(X, n_fold):
        assert_true(batch_X.shape[0] <= max_fold_size)
        X_batchs.append(batch_X)

    # rebuild from batchs should get X
    X_2 = sp.vstack(X_batchs)
    assert_array_almost_equal(X.todense(), X_2.todense())


def test_min_batch_split():
    """
    test `_min_batch_split`
    """
    rng = np.random.RandomState(0)
    n_row = 30
    n_col = 3
    batch_size = 7
    n_batch = 5
    X = rng.randint(5, size=(n_row, n_col))
    X = sp.csr_matrix(X)

    X_batchs = []
    idx = 1
    for batch_X in _min_batch_split(X, batch_size):
        if idx < n_batch:
            assert_equal(batch_X.shape[0], batch_size)
        else:
            assert_equal(batch_X.shape[0], n_row % batch_size)
        idx += 1
        X_batchs.append(batch_X)

    # rebuild from batchs should get X
    X_2 = sp.vstack(X_batchs)
    assert_array_almost_equal(X.todense(), X_2.todense())


def test_lda_batch():
    """
    Test LDA batch training(`fit` method)
    """
    rng = np.random.RandomState(0)
    n_topics, alpha, eta, X = _build_sparse_mtx()
    lda = onlineLDA(n_topics=n_topics, alpha=alpha, eta=eta,
                    random_state=rng)
    lda.fit(X)

    correct_idx_grps = [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
    for c in lda.components_:
        top_idx = set(c.argsort()[-3:][::-1])
        assert_true(tuple(sorted(top_idx)) in correct_idx_grps)


def test_lda_online():
    """
    Test LDA online training(`partial_fit` method)
    (same as test_lda_batch)
    """
    rng = np.random.RandomState(0)
    n_topics, alpha, eta, X = _build_sparse_mtx()
    lda = onlineLDA(n_topics=n_topics, alpha=alpha, eta=eta,
                    tau=30., random_state=rng)

    for i in xrange(3):
        lda.partial_fit(X)

    correct_idx_grps = [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
    for c in lda.components_:
        top_idx = set(c.argsort()[-3:][::-1])
        assert_true(tuple(sorted(top_idx)) in correct_idx_grps)


def test_lda_dense_input():
    """
    Test LDA with dense input.
    Similar to test_lda()
    """
    rng = np.random.RandomState(0)
    X = rng.randint(5, size=(20, 10))
    n_topics = 3
    alpha0 = eta0 = 1. / n_topics
    lda = onlineLDA(n_topics=n_topics, alpha=alpha0, eta=eta0,
                    random_state=rng)

    X_trans = lda.fit_transform(X)
    assert_true((X_trans > 0.0).any())


def test_lda_fit_transform():
    """
    Test LDA fit_transform & transform
    fit_transform and transform result should be the same
    """
    rng = np.random.RandomState(0)
    n_topics, alpha, eta, X = _build_sparse_mtx()
    lda = onlineLDA(n_topics=n_topics, alpha=alpha, eta=eta,
                    random_state=rng)
    X_fit = lda.fit_transform(X)
    X_trans = lda.transform(X)
    assert_array_almost_equal(X_fit, X_trans, 4)


def test_lda_normalize_docs():
    """
    test sum of topic distribution equals to 1 for each doc
    """
    rng = np.random.RandomState(0)
    n_topics, alpha, eta, X = _build_sparse_mtx()
    lda = onlineLDA(n_topics=n_topics, alpha=alpha, eta=eta,
                    random_state=rng)
    X_fit = lda.fit_transform(X)
    assert_array_almost_equal(X_fit.sum(axis=1), np.ones(X.shape[0]))


@raises(ValueError)
def test_lda_partial_fit_dim_mismatch():
    """
    test n_vocab mismatch in partial_fit
    """
    rng = np.random.RandomState(0)
    n_topics = rng.randint(3, 6)
    alpha0 = eta0 = 1. / n_topics

    n_col = rng.randint(6, 10)
    X_1 = np.random.randint(4, size=(10, n_col))
    X_2 = np.random.randint(4, size=(10, n_col + 1))
    lda = onlineLDA(n_topics=n_topics, alpha=alpha0, eta=eta0,
                    tau=5., n_docs=20, random_state=rng)
    for X in [X_1, X_2]:
        lda.partial_fit(X)


@raises(AttributeError)
def test_lda_transform_before_fit():
    """
    test `transform` before `fit`
    """
    rng = np.random.RandomState(0)
    X = rng.randint(4, size=(20, 10))
    lda = onlineLDA()
    lda.transform(X)


@raises(ValueError)
def test_lda_transform_mismatch():
    """
    test n_vocab mismatch in fit and transform
    """
    rng = np.random.RandomState(0)
    X = rng.randint(4, size=(20, 10))
    X_2 = rng.randint(4, size=(10, 8))

    n_topics = rng.randint(3, 6)
    alpha0 = eta0 = 1. / n_topics
    lda = onlineLDA(n_topics=n_topics, alpha=alpha0,
                    eta=eta0, random_state=rng)
    lda.partial_fit(X)
    lda.transform(X_2)


@if_not_mac_os()
def test_lda_multi_jobs():
    """
    Test LDA batch training with multi CPU
    """
    rng = np.random.RandomState(0)
    n_topics, alpha, eta, X = _build_sparse_mtx()
    lda = onlineLDA(n_topics=n_topics, alpha=alpha, eta=eta,
                    n_jobs=3, random_state=rng)
    lda.fit(X)

    correct_idx_grps = [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
    for c in lda.components_:
        top_idx = set(c.argsort()[-3:][::-1])
        assert_true(tuple(sorted(top_idx)) in correct_idx_grps)


@if_not_mac_os()
def test_lda_online_multi_jobs():
    """
    Test LDA online training with multi CPU
    """
    rng = np.random.RandomState(0)
    n_topics, alpha, eta, X = _build_sparse_mtx()
    lda = onlineLDA(n_topics=n_topics, alpha=alpha, eta=eta,
                    n_jobs=2, tau=5., n_docs=30, random_state=rng)

    for i in xrange(3):
        lda.partial_fit(X)

    correct_idx_grps = [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
    for c in lda.components_:
        top_idx = set(c.argsort()[-3:][::-1])
        assert_true(tuple(sorted(top_idx)) in correct_idx_grps)


def test_lda_preplexity():
    """
    Test LDA preplexity for batch training
    preplexity should be lower after each iteration
    """
    n_topics, alpha, eta, X = _build_sparse_mtx()
    lda_1 = onlineLDA(n_topics=n_topics, alpha=alpha, eta=eta,
                      random_state=0)
    lda_2 = onlineLDA(n_topics=n_topics, alpha=alpha, eta=eta,
                      random_state=0)

    distr_1 = lda_1.fit_transform(X, max_iters=1)
    prep_1 = lda_1.preplexity(X, distr_1, subsampling=False)

    distr_2 = lda_2.fit_transform(X, max_iters=10)
    prep_2 = lda_2.preplexity(X, distr_2, subsampling=False)
    assert_greater(prep_1, prep_2)


if __name__ == '__main__':
    import nose
    nose.run(argv=['', __file__])
