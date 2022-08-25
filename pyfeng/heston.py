import abc
import numpy as np
import scipy.stats as spst
from . import sv_abc as sv
from . import bsm


class HestonABC(sv.SvABC, abc.ABC):
    model_type = "Heston"

    def var_mv(self, var0, dt):
        """
        Mean and variance of the variance V(t+dt) given V(0) = var_0

        Args:
            var0: initial variance
            dt: time step

        Returns:
            mean, variance
        """

        expo = np.exp(-self.mr*dt)
        m = self.theta + (var0 - self.theta)*expo
        s2 = var0*expo + self.theta*(1 - expo)/2
        s2 *= self.vov**2*(1 - expo)/self.mr
        return m, s2

    def avgvar_mv(self, var0, texp):
        """
        Mean and variance of the average variance given V(0) = var_0.
        Appnedix B in Ball & Roma (1994)

        Args:
            var0: initial variance
            texp: time step

        Returns:
            mean, variance
        """

        mr_t = self.mr*texp
        e_mr = np.exp(-mr_t)
        x0 = var0 - self.theta
        mean = self.theta + x0*(1 - e_mr)/mr_t
        var = (self.theta - 2*x0*e_mr) + (1 - e_mr)*(var0 - 2.5*self.theta + (var0 - self.theta/2)*e_mr)/mr_t
        var *= (self.vov/mr_t)**2 * texp
        return mean, var

    def fair_strike_var(self, texp, aa):
        """
        Analytic fair strike of variance swap

        Args:
            texp: time to expiry
            aa: number of observation per year

        Returns:
            Fair strike
        """

        var0 = self.sigma

        ### continuously monitored fair strike (same as mean of avgvar)
        mr_t = self.mr*texp
        e_mr = np.exp(-mr_t)
        x0 = var0 - self.theta
        strike = self.theta + x0*(1 - e_mr)/mr_t

        if aa is not None:
            ### adjustment for discrete monitoring
            mr_a = self.mr/aa
            e_mr_a = np.exp(-mr_a)

            tmp = self.theta - 2*self.intr
            strike += tmp / (4*aa) * (tmp + 2*x0*(1 - e_mr)/mr_t)

            tmp = self.vov / self.mr
            strike += self.theta*tmp * (tmp/4 - self.rho) * (1 - (1-e_mr_a)/mr_a)
            strike += x0 * tmp * (tmp/2 - self.rho) * (1 - e_mr)/mr_t * (1 + mr_a/(1-e_mr_a))
            strike -= (tmp**2*(self.mr - 2*var0) + 2*x0**2/self.mr) * (1 - e_mr**2)/(8*mr_t) * (1-e_mr_a)/(1+e_mr_a)

        return strike


class HestonUncorrBallRoma1994(HestonABC):
    """
    Ball & Roma (1994)'s approximation pricing formula for European options under uncorrelated (rho=0) Heston model.
    Up to 2nd order is implemented.

    See Also: OusvUncorrBallRoma1994, GarchUncorrBaroneAdesi2004
    """

    order = 2

    def price(self, strike, spot, texp, cp=1):

        if not np.isclose(self.rho, 0.0):
            print(f"Pricing ignores rho = {self.rho}.")

        avgvar, var = self.avgvar_mv(self.sigma, texp)

        m_bs = bsm.Bsm(np.sqrt(avgvar), intr=self.intr, divr=self.divr)
        price = m_bs.price(strike, spot, texp, cp)

        if self.order == 2:
            price += 0.5*var*m_bs.d2_var(strike, spot, texp, cp)
        elif self.order > 2:
            raise ValueError(f"Not implemented for approx order: {self.order}")

        return price
