"""Rank 1 baseline model."""

import numpy as np
from jax import vmap, jit

from beartype import beartype
from beartype.typing import NamedTuple, Union

from jaxtyping import Float, Bool, Integer
from jaxtyping import Array as _jax_Array


Array = Union[_jax_Array, np.ndarray]


@beartype
class Rank1Problem(NamedTuple):
    """Rank 1 baseline problem state.

    Attributes
    ----------
    mask: occupancy mask of which samples to use.
    n: number of samples in each row.
    m: number of samples in each column.
    """

    mask: Bool[Array, "nx ny"]
    n: Integer[Array, "nx"]
    m: Integer[Array, "ny"]


@beartype
class Rank1Solution(NamedTuple):
    """Rank 1 baseline problem solution.

    Attributes
    ----------
    x: row features.
    y: column features.
    """

    x: Float[Array, "nx"]
    y: Float[Array, "ny"]


@beartype
class Rank1:
    """Rank 1 baseline matrix factorization model Y_ij = x[i] + j[j].

    NOTE: Since jax uses 32-bit float by default, if the dataset magnitude is
    around ~1e-1 - 1e1, the best precision for the delta will be ~1e-7, so
    tol should be >>1e-7.

    Parameters
    ----------
    data : dataset matrix.
    init_val : Initial x and y values; should be set to 0.5 * E[A].
    max_iter : Max number of iterations.
    tol : Convergence criteria on l2 norm; stops when all replicates converge.
    """

    def __init__(
        self, data: Float[Array, "nx ny"], init_val: float = 0.,
        max_iter: int = 10, tol: float = 1e-5, backend=np
    ) -> None:
        self.data = data
        self.init_val = init_val
        self.max_iter = max_iter
        self.tol = tol
        self.np = np

    def init(
        self, mask: Bool[Array, "nx ny"]
    ) -> tuple[Rank1Problem, Rank1Solution]:
        """Create problem.

        Parameters
        ----------
        mask: mask indicating which entries are in the training set.

        Returns
        -------
        problem: created problem with pre-computed row/column counts.
        init: initial state.
        """
        problem = Rank1Problem(
            mask=mask,
            n=self.np.maximum(self.np.sum(mask, axis=1), 1),
            m=self.np.maximum(self.np.sum(mask, axis=0), 1))
        init = Rank1Solution(
            x=self.np.ones(self.data.shape[0]) * self.init_val,
            y=self.np.ones(self.data.shape[1]) * self.init_val)
        return problem, init

    def iter(
        self, problem: Rank1Problem, state: Rank1Solution
    ) -> tuple[Rank1Solution, float]:
        """Run single iteration."""
        x_new = self.np.sum(
            problem.mask * (self.data - state.y.reshape(1, -1)),
            axis=1) / problem.n
        y_new = self.np.sum(
            problem.mask * (self.data - x_new.reshape(-1, 1)),
            axis=0) / problem.m

        delta = (
            self.np.sum(self.np.abs(x_new - state.x))
            + self.np.sum(self.np.abs(y_new - state.y)))

        return Rank1Solution(x=x_new, y=y_new), delta

    def fit(self, mask: Bool[Array, "nx ny"]) -> Rank1Solution:
        """Fit in single-data mode."""
        problem, soln = self.init(mask)

        for _ in range(self.max_iter):
            soln, delta = self.iter(problem, soln)
            if delta < self.tol:
                return soln
        print(
            "Convergence warning: l1_delta={} after {} iterations; "
            "Increase tol or max_iter.".format(delta, self.max_iter))
        return soln

    def predict(self, soln: Rank1Solution) -> Float[Array, "nx ny"]:
        """Generate prediction."""
        return soln.x.reshape(-1, 1) + soln.y.reshape(1, -1)

    def vfit(self, mask: Bool[Array, "batch nx ny"]) -> Rank1Solution:
        """Run vectorized fit.

        NOTE: This method MUST be performed at the highest level, i.e. cannot
        be vmapped, since it contains a break for the convergence criteria.
        """
        problem, soln = vmap(self.init)(mask)
        _iter = jit(vmap(self.iter))

        for _ in range(self.max_iter):
            soln, delta = _iter(problem, soln)
            if self.np.all(delta < self.tol):
                return soln
        print(
            "Convergence warning: max(l1_delta)={} after {} iterations; "
            "Increase tol or max_iter.".format(
                delta[delta > self.tol], self.max_iter))

        return soln
