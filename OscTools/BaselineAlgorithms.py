from abc import abstractmethod

import numpy as np
from scipy.optimize import curve_fit

import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from matplotlib.ticker import AutoMinorLocator

class FittingAlgorithms:
    """
    Good practice to have a parent class that all children must follow (defines a common interface)
    """

    def __init__(self, offset=False):
        self.params = []
        self.param_errors = []
        self.param_cov = []

        self.time_fit = np.array([])
        self.current_fit = np.array([])
        self.current_fit_errs = np.array([])
        self.time_full = np.array([])

        self.current_pred = np.array([])
        self.current_pred_errs = np.array([])

        self.current_noise = None

        self.offset = offset

    def initialise_data(self, time_fit, current_fit, current_fit_errs, time_full, offset=None):

        if offset is not None:
            self.offset = offset

        self.time_fit = time_fit
        self.current_fit = current_fit
        self.current_fit_errs = current_fit_errs
        self.time_full = time_full

        if self.offset:
            self.time_fit = self.time_fit.copy() - np.min(self.time_fit)
            self.time_full = self.time_full.copy() - np.min(self.time_full)

    def fit(self, omit_errors=False):
        """
        Mandatory method : Making sure all algorithms are callable
        """
        raise NotImplementedError

    def _get_noise_helper(self, current_pred):

        res = self.current_fit - current_pred
        weights = 1 / np.power(self.current_fit_errs, 2)
        var_int = np.sum(weights * (res ** 2 - np.power(self.current_fit_errs, 2))) / np.sum(weights)
        var_int = max(0, var_int)
        self.current_noise = np.sqrt(var_int)

        return self.current_noise

    def get_noise(self):
        return self.current_noise

    def get_fit_pred(self):
        pass

    def plot(self, show_plateau=False):

        fig = plt.figure()
        ax = fig.add_subplot(111)

        # Set formatting style
        formatter = ScalarFormatter()
        formatter.set_scientific(False)

        ax.ticklabel_format(axis='y', style='plain', useOffset=False)

        # Style and formatting
        ax.tick_params(left=True, bottom=True, direction='out', length=3, which='both')
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))

        # Set axis labels
        ax.xaxis.set_major_formatter(formatter)
        ax.yaxis.set_major_formatter(formatter)
        # ax.xaxis.set_major_formatter(FormatStrFormatter('%2.0f'))
        # ax.xaxis.set_minor_formatter(formatter)
        # ax.yaxis.set_minor_formatter(formatter)

        ax.set_xlabel('Time [s]', loc='right', labelpad=10)
        ax.set_ylabel('Current [pA]', loc='top', labelpad=10)

        if self.current_fit_errs.any():
            ax.errorbar(self.time_fit, self.current_fit * 1e12, self.current_fit_errs * 1e12, c='k',
                        markersize=10, capsize=5, fmt='.', elinewidth=2)
        else:
            ax.scatter(self.time_fit, self.current_fit * 1e12, c='k', marker='.', s=3, label='Data')

        if not self.current_pred.any():
            _, _ = self.get_fit_pred()

        _ = self.get_noise()

        ax.plot(self.time_full, self.current_pred * 1e12, c='red', linestyle='--', label='Model')
        if self.current_pred_errs.any():
            # current_pred_errs_full = np.sqrt(self.current_pred_errs**2 + self.current_noise**2)
            ax.fill_between(self.time_full,
                            (self.current_pred - self.current_pred_errs) * 1e12,
                            (self.current_pred + self.current_pred_errs) * 1e12,
                            alpha=0.3, color='red', label=r'Model 1$\sigma$ (Fit)')
            ax.fill_between(self.time_full,
                            (self.current_pred - self.current_pred_errs) * 1e12,
                            (self.current_pred - self.current_pred_errs - self.current_noise) * 1e12,
                            alpha=0.3, color='tab:blue', label=r'Model 1$\sigma$ (Noise)')
            ax.fill_between(self.time_full,
                            (self.current_pred + self.current_pred_errs) * 1e12,
                            (self.current_pred + self.current_pred_errs + self.current_noise) * 1e12,
                            alpha=0.3, color='tab:blue')

        if show_plateau:
            val, err = self.get_plateau()
            val, err = val * 1e12, err * 1e12
            noise = self.current_noise * 1e12
            time_start, time_end = np.min(self.time_full), np.max(self.time_full)
            ax.plot([time_start, time_end], [val, val], c='green', linestyle='--', label='Plat')
            ax.fill_between([time_start, time_end], [val - err, val - err], [val + err, val + err],
                            alpha=0.3, color='green', label=r'Plat 1$\sigma$ (Fit)')
            ax.fill_between([time_start, time_end], [val - err, val - err],
                            [val - err - noise, val - err - noise],
                            alpha=0.3, color='tab:blue', label=r'Plat 1$\sigma$ (Noise)')
            ax.fill_between([time_start, time_end], [val + err, val + err],
                            [val + err + noise, val + err + noise],
                            alpha=0.3, color='tab:blue')

        chi2 = np.sum((self.current_pred[np.isin(self.time_full, self.time_fit)] - self.current_fit)**2 / self.current_fit_errs**2)
        try:
            dof = len(self.current_fit) - len(self.params)
        except TypeError:
            dof = len(self.current_fit) - 1

        plt.legend(loc='upper right', borderpad=0.4, labelspacing=0.6, edgecolor="white", facecolor="white", fancybox=True,
                   ncol=2, columnspacing=0.9, handletextpad=0.4, markerscale=2, bbox_to_anchor=(1.0, 1.0))
        plt.tight_layout()
        plt.show()

        self.show_params()
        print(f"Chi2 = {chi2} (dof = {dof})")

    def get_params(self):

        return self.params, self.param_errors

    def show_params(self):
        """
        Optional method : If parameters want to be seen
        """

        print(f"Best fit parameters : {self.params}\n"
              f"Best fit parameters error : {self.param_errors}")

    def get_plateau(self):

        print("Not possible to get deltaI using this fitting procedure")

        raise KeyboardInterrupt


# class GaussianProcessRegressor(FittingAlgorithms):
#     """
#     Uses a Gaussian Process Regressor to fill in the blanks when fitting the data
#
#     (code developed by Taifakou F.E. in "timeseries.py and adapted into a class)
#     """
#
#     def __init__(self, kernel, random_state=0):
#         """
#         Initialise with all relevant parameters
#         """
#
#         super().__init__()
#         self.kernel = kernel
#         self.random_state = random_state
#         self.gpr = None
#
#     def fit(self):
#         """
#         Perform the fitting algorithm when called and return the baseline data with all gaps filled
#         """
#
#         # (Not entirely sure why this is needed)
#         x, y = self.time_fit[:, np.newaxis], self.current_fit
#
#         # Fits to the data
#         self.gpr = GaussianProcessRegressor(kernel=self.kernel, random_state=self.random_state).fit(x, y)
#         self.params = gpr.get_params()
#
#     def get_best_fit(self):
#
#         # Scores the fit
#         fitting_score = self.gpr.score(x, y)
#
#         # Fills in the gaps to the OFF data
#         self.current_pred = gpr.predict(self.time_full[:, np.newaxis], return_std=False)
#
#         return self.current_pred


class Polyfit(FittingAlgorithms):
    """
    Performs a n'th degree polynomial fit based on what the user wishes

    (code developed by Gashi A. in osctools.py and adapted into a class))
    """

    def __init__(self, deg):

        super().__init__()
        self.deg = deg
        self.exp_obj = None

    def fit(self, omit_errors=False):

        # time_fit = self.time_fit.copy() - np.min(self.time_fit)

        if omit_errors:
            weights = None
        else:
            weights = 1 / self.current_fit_errs

        self.params, self.param_cov = np.polyfit(self.time_fit, self.current_fit, self.deg, w=weights, cov='unscaled')
        self.param_errors = np.sqrt(np.diag(self.param_cov))

    def get_noise(self):

        current_pred = np.polyval(self.params, self.time_fit)
        super()._get_noise_helper(current_pred)
        return self.current_noise

    def get_fit_pred(self):

        self.current_pred = np.polyval(self.params, self.time_full)

        # J = np.vstack([self.time_full**i for i in range(len(self.params)-1, -1, -1)]).T
        # y_err = np.sqrt(np.sum(J @ self.param_cov * J, axis=1))

        # Build Vandermonde matrix (Jacobian)
        J = np.vander(self.time_full, N=len(self.params))

        # Variance propagation: diag(J Σ J^T)
        current_pred_errs_sq  = np.einsum('ij,jk,ik->i', J, self.param_cov, J)
        self.current_pred_errs  = np.sqrt(current_pred_errs_sq)

        return self.current_pred, self.current_pred_errs

    def _do_exp_fit(self):

        self.exp_obj = Exponential()
        self.exp_obj.initialise_data(self.time_fit, self.current_fit, self.current_fit_errs, self.time_full)
        self.exp_obj.fit()

    def get_plateau(self):

        if self.exp_obj is None:
            self._do_exp_fit()

        return self.exp_obj.get_plateau()

    def get_time_const(self):

        if self.exp_obj is None:
            self._do_exp_fit()

        return self.exp_obj.get_time_const()

class Exponential(FittingAlgorithms):
    """
    """

    @staticmethod
    def exponential(x, a, b, c):
        with np.errstate(divide='ignore'):
            return a * np.exp(- x / b) + c

    def fit(self, omit_errors=False):

        sigma = None
        absolute_sigma = False

        if not omit_errors and self.current_fit_errs.any():
            sigma = self.current_fit_errs
            absolute_sigma = True

        self.params, self.param_cov = curve_fit(self.exponential, self.time_fit, self.current_fit,
                                                sigma=sigma, absolute_sigma=absolute_sigma, maxfev=100000,
                                                bounds=([-np.inf, 1e-12, -np.inf], [np.inf, np.inf, np.inf]),
                                                p0=[np.max(self.current_fit) - np.min(self.current_fit),
                                                    np.median(self.time_fit), np.mean(self.current_fit[-20:])])
        self.param_errors = np.sqrt(np.diag(self.param_cov))

    def get_noise(self):

        current_pred = self.exponential(self.time_fit, self.params[0], self.params[1], self.params[2])
        super()._get_noise_helper(current_pred)
        return self.current_noise

    def get_fit_pred(self):

        self.current_pred = self.exponential(self.time_full, self.params[0], self.params[1], self.params[2])

        # self.current_pred_errs = np.sqrt(np.exp(-2*self.params[1]*time_full) *
        #                             (self.param_errors[0]**2 + (self.params[0] * time_full * self.param_errors[1])**2)+
        #                             self.param_errors[2]**2)

        # Partial derivatives (gradient vector)
        exp_term = np.exp(-self.time_full / self.params[1])
        dy_da = exp_term
        dy_db = self.params[0] * self.time_full / self.params[1] ** 2 * exp_term
        dy_dc = np.ones_like(self.time_full)

        grad = np.stack([dy_da, dy_db, dy_dc], axis=1)  # shape (3, N) if x is an array

        # sigma_y^2 = grad^T @ cov @ grad, do this element-wise across x
        current_pred_errs_sq = np.einsum('ij,jk,ik->i', grad, self.param_cov, grad)
        self.current_pred_errs = np.sqrt(current_pred_errs_sq)

        return self.current_pred, self.current_pred_errs

    def get_plateau(self):

        return self.params[2], self.param_errors[2]

    def get_time_const(self):

        return self.params[1], self.param_errors[1]

class StretchedExponential(FittingAlgorithms):
    """
    """

    @staticmethod
    def stretched_exponential(x, a, b, c, d):
        with np.errstate(divide='ignore'):
            return a * np.exp(-np.power(x / b, d)) + c

    def fit(self, omit_errors=False):

        sigma = None
        absolute_sigma = False

        if not omit_errors and self.current_fit_errs.any():
            sigma = self.current_fit_errs
            absolute_sigma = True

        self.params, self.param_cov = curve_fit(self.stretched_exponential, self.time_fit, self.current_fit,
                                                sigma=sigma, absolute_sigma=absolute_sigma, maxfev=100000,
                                                bounds=([-np.inf, 1e-12, -np.inf, 0.1],[np.inf, np.inf, np.inf, 3]),
                                                p0=[np.max(self.current_fit) - np.min(self.current_fit),
                                                    np.median(self.time_fit), np.mean(self.current_fit[-20:]), 1.0])
        self.param_errors = np.sqrt(np.diag(self.param_cov))

        # [2.702621018317703e-12, 86.5132, 3.61171526990362e-12, 1.0]
        # [2.6334762638901966e-12, 86.5132, 3.547275411433637e-12, 1.0]

        # [6.636633242387488e-11, 22.11112833491001, 1.0106883202235335e-11, 2.1477941515800736]
        # [2.7566161799647233e-12, 5.1088121785254526, 1.0078848635255897e-11, 1.0300434867154067]

    def get_noise(self):

        current_pred = self.stretched_exponential(self.time_fit, self.params[0], self.params[1], self.params[2], self.params[3])
        super()._get_noise_helper(current_pred)
        return self.current_noise

    def get_fit_pred(self):

        self.current_pred = self.stretched_exponential(self.time_full, self.params[0], self.params[1],
                                                       self.params[2], self.params[3])

        # self.current_pred_errs = np.sqrt(np.exp(-2*self.params[1]*time_full) *
        #                             (self.param_errors[0]**2 + (self.params[0] * time_full * self.param_errors[1])**2)+
        #                             self.param_errors[2]**2)

        z = self.time_full / self.params[1]
        exp_term = np.exp(-z ** self.params[3])

        dy_da = exp_term
        dy_db = self.params[0] * self.params[3] * self.time_full ** self.params[3] / self.params[1] ** (self.params[3] + 1) * exp_term
        dy_dc = np.ones_like(self.time_full)

        dy_dd_mask = z != 0
        dy_dd = np.zeros_like(z)
        dy_dd_sign = np.where(z[dy_dd_mask] > 0, -1, 1)
        dy_dd[dy_dd_mask] = (dy_dd_sign * self.params[0] *
                             (z[dy_dd_mask] ** self.params[3]) * np.log(np.abs(z[dy_dd_mask])) * exp_term[dy_dd_mask])

        grad = np.array([dy_da, dy_db, dy_dc, dy_dd])  # shape (3, N) if x is an array

        # sigma_y^2 = grad^T @ cov @ grad, do this element-wise across x
        current_pred_errs_sq = np.einsum('ij,jk,ki->i', grad.T, self.param_cov, grad)
        self.current_pred_errs = np.sqrt(current_pred_errs_sq)

        # if self.twice:
        #     mask = np.isin(self.time_full, self.time_fit)
        #     exp2_obj = StretchedExponential()
        #     exp2_obj.initialise_data(self.time_fit, self.current_pred[mask], self.current_pred_errs[mask], self.time_full)

        return self.current_pred, self.current_pred_errs

    def get_plateau(self):

        return self.params[2], self.param_errors[2]

    def get_time_const(self):

        return self.params[1], self.param_errors[1]


class Constant(FittingAlgorithms):

    def fit(self, omit_errors=False):
        """Performs weighted mean (equivalent to LS fit)"""

        # 2.4454245524060673e-11

        if omit_errors:
            weights = None
        else:
            weights = 1 / np.power(self.current_fit_errs, 2)

        self.params = np.average(self.current_fit, weights=weights)

        if omit_errors:
            self.param_errors = np.std(self.current_fit, ddof=1) / len(self.current_fit)
        else:
            self.param_errors = np.sqrt(1 / np.sum(weights))

            # cov_inv = np.diag(weights)
            # A = np.ones(len(self.current_fit)).T
            # err = np.linalg.inv(np.dot(A.T, np.dot(cov_inv, A)))
            # val = np.dot(err, np.dot(A.T, np.dot(cov_inv, self.current_fit)))

    def get_noise(self):

        current_pred = np.ones(len(self.time_fit)) * self.params
        super()._get_noise_helper(current_pred)
        return self.current_noise

    # def get_std(self, omit_errors=False):
    #
    #     if omit_errors:
    #         self.param_errors = np.std(self.current_fit, ddof=1)
    #     else:
    #         weights = 1 / np.power(self.current_fit_errs, 2)
    #         self.param_errors = np.sqrt(np.sum(weights * np.power(self.current_fit - self.params, 2)) / np.sum(weights))

    def get_fit_pred(self):

        self.current_pred = np.ones(len(self.time_full)) * self.params
        self.current_pred_errs = np.ones(len(self.time_full)) * self.param_errors

        return self.current_pred, self.current_pred_errs

    def get_plateau(self):

        return self.params, self.param_errors

class ExponentialLinear(FittingAlgorithms):
    """
    """

    @staticmethod
    def exponential_linear(x, a, b, c, m):
        with np.errstate(divide='ignore'):
            return a * np.exp(- x / b) + m * x + c

    def fit(self, omit_errors=False):

        sigma = None
        absolute_sigma = False

        if not omit_errors and self.current_fit_errs.any():
            sigma = self.current_fit_errs
            absolute_sigma = True

        self.params, self.param_cov = curve_fit(self.exponential_linear, self.time_fit, self.current_fit,
                                                sigma=sigma, absolute_sigma=absolute_sigma, maxfev=100000,
                                                bounds=([-np.inf, 1e-12, -np.inf, -np.inf], [np.inf, np.inf, np.inf, np.inf]),
                                                p0=[np.max(self.current_fit) - np.min(self.current_fit),
                                                    np.median(self.time_fit), np.mean(self.current_fit[-20:]), 1e-13])
        self.param_errors = np.sqrt(np.diag(self.param_cov))

        # bounds=([-np.inf, 1e-12, -np.inf, -np.inf], [np.inf, np.inf, np.inf, np.inf]),
        # p0=[np.max(self.current_fit) - np.min(self.current_fit), np.median(self.time_fit), np.mean(self.current_fit[-20:]), 1e-12]

    def get_noise(self):

        current_pred = self.exponential_linear(self.time_fit, self.params[0], self.params[1], self.params[2], self.params[3])
        super()._get_noise_helper(current_pred)
        return self.current_noise

    def get_fit_pred(self):

        self.current_pred = self.exponential_linear(self.time_full, self.params[0], self.params[1],
                                                    self.params[2], self.params[3])

        # self.current_pred_errs = np.sqrt(np.exp(-2*self.params[1]*time_full) *
        #                             (self.param_errors[0]**2 + (self.params[0] * time_full * self.param_errors[1])**2)+
        #                             self.param_errors[2]**2)

        # Partial derivatives (gradient vector)
        exp_term = np.exp(-self.time_full / self.params[1])
        dy_da = exp_term
        dy_db = self.params[0] * self.time_full / self.params[1]**2 * exp_term
        dy_dc = np.ones_like(self.time_full)
        dy_dm = self.time_full

        grad = np.stack([dy_da, dy_db, dy_dc, dy_dm], axis=1)  # shape (3, N) if x is an array

        # sigma_y^2 = grad^T @ cov @ grad, do this element-wise across x
        current_pred_errs_sq = np.einsum('ij,jk,ik->i', grad, self.param_cov, grad)
        self.current_pred_errs = np.sqrt(current_pred_errs_sq)

        return self.current_pred, self.current_pred_errs

    def get_plateau(self):

        return self.params[2], self.param_errors[2]

    def get_time_const(self):

        return self.params[1], self.param_errors[1]

class StretchedExponentialLinear(FittingAlgorithms):
    """
    """

    @staticmethod
    def stretched_exponential_linear(x, a, b, c, d, m):
        with np.errstate(divide='ignore'):
            return a * np.exp(-np.power(x / b, d)) + m * x + c

    def fit(self, omit_errors=False):

        sigma = None
        absolute_sigma = False

        if not omit_errors and self.current_fit_errs.any():
            sigma = self.current_fit_errs
            absolute_sigma = True

        self.params, self.param_cov = curve_fit(self.stretched_exponential_linear, self.time_fit, self.current_fit,
                                                sigma=sigma, absolute_sigma=absolute_sigma, maxfev=100000,
                                                bounds=([-np.inf, 1e-12, -np.inf, 0.1, -np.inf],
                                                        [np.inf, np.inf, np.inf, 3, np.inf]),
                                                p0 = [np.max(self.current_fit) - np.min(self.current_fit),
                                                      np.median(self.time_fit), np.mean(self.current_fit[-20:]), 1.0, 1.16018158e-13])
        self.param_errors = np.sqrt(np.diag(self.param_cov))

        # bounds = ([-np.inf, 1e-12, -np.inf, 0.1, -np.inf], [np.inf, np.inf, np.inf, 3, np.inf]),
        # p0 = [np.max(self.current_fit) - np.min(self.current_fit), np.median(self.time_fit), np.mean(self.current_fit[-20:]), 1.0, 1.0]

        # [2.702621018317703e-12, 86.5132, 3.61171526990362e-12, 1.0]
        # [2.6334762638901966e-12, 86.5132, 3.547275411433637e-12, 1.0]

        # [6.636633242387488e-11, 22.11112833491001, 1.0106883202235335e-11, 2.1477941515800736]
        # [2.7566161799647233e-12, 5.1088121785254526, 1.0078848635255897e-11, 1.0300434867154067]

    def get_noise(self):

        current_pred = self.stretched_exponential_linear(self.time_fit, self.params[0], self.params[1],
                                                         self.params[2], self.params[3], self.params[4])
        super()._get_noise_helper(current_pred)
        return self.current_noise

    def get_fit_pred(self):

        self.current_pred = self.stretched_exponential_linear(self.time_full, self.params[0], self.params[1],
                                                              self.params[2], self.params[3], self.params[4])

        # self.current_pred_errs = np.sqrt(np.exp(-2*self.params[1]*time_full) *
        #                             (self.param_errors[0]**2 + (self.params[0] * time_full * self.param_errors[1])**2)+
        #                             self.param_errors[2]**2)

        z = self.time_full / self.params[1]
        exp_term = np.exp(-z ** self.params[3])

        dy_da = exp_term
        dy_db = self.params[0] * self.params[3] * self.time_full ** self.params[3] / self.params[1] ** (self.params[3] + 1) * exp_term
        dy_dc = np.ones_like(self.time_full)
        dy_dm = self.time_full

        dy_dd_mask = z != 0
        dy_dd = np.zeros_like(z)
        dy_dd_sign = np.where(z[dy_dd_mask] > 0, -1, 1)
        dy_dd[dy_dd_mask] = (dy_dd_sign * self.params[0] *
                             (z[dy_dd_mask] ** self.params[3]) * np.log(np.abs(z[dy_dd_mask])) * exp_term[dy_dd_mask])

        grad = np.array([dy_da, dy_db, dy_dc, dy_dd, dy_dm])  # shape (3, N) if x is an array

        # sigma_y^2 = grad^T @ cov @ grad, do this element-wise across x
        current_pred_errs_sq = np.einsum('ij,jk,ki->i', grad.T, self.param_cov, grad)
        self.current_pred_errs = np.sqrt(current_pred_errs_sq)

        # if self.twice:
        #     mask = np.isin(self.time_full, self.time_fit)
        #     exp2_obj = StretchedExponential()
        #     exp2_obj.initialise_data(self.time_fit, self.current_pred[mask], self.current_pred_errs[mask], self.time_full)

        return self.current_pred, self.current_pred_errs

    def get_plateau(self):

        return self.params[2], self.param_errors[2]

    def get_time_const(self):

        return self.params[1], self.param_errors[1]



# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------- NOT CHECKED ----------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------



class DoubleExponential(FittingAlgorithms):
    """
    """

    @staticmethod
    def double_exponential(x, a1, b1, a2, b2, c):
        with np.errstate(divide='ignore'):
            return a1 * np.exp(- x / b1) + a2 * np.exp(- x / b2) + c

    def fit(self, omit_errors=False):

        time_fit = self.time_fit.copy() - np.min(self.time_fit)

        sigma = None
        absolute_sigma = False

        if not omit_errors and self.current_fit_errs.any():
            sigma = self.current_fit_errs
            absolute_sigma = True

        self.params, self.param_cov = curve_fit(self.double_exponential, time_fit, self.current_fit,
                                                sigma=sigma, absolute_sigma=absolute_sigma, maxfev=100000,
                                                bounds=([-np.inf, 1e-12, -np.inf, 1e-12, -np.inf],
                                                        [ np.inf, np.inf,  np.inf, np.inf,  np.inf]))
        self.param_errors = np.sqrt(np.diag(self.param_cov))

    def get_fit_pred(self):

        time_full = self.time_full.copy() - np.min(self.time_full)

        self.current_pred = self.double_exponential(time_full, self.params[0], self.params[1], self.params[2],
                                                    self.params[3], self.params[4])

        # self.current_pred_errs = np.sqrt(np.exp(-2*self.params[1]*time_full) *
        #                             (self.param_errors[0]**2 + (self.params[0] * time_full * self.param_errors[1])**2)+
        #                             self.param_errors[2]**2)

        # Partial derivatives (gradient vector)
        exp_term_1 = np.exp(-time_full / self.params[1])
        exp_term_2 = np.exp(-time_full / self.params[3])

        dy_da1 = exp_term_1
        dy_da2 = exp_term_2
        dy_db1 = self.params[0] * time_full / self.params[1]**2 * exp_term_1
        dy_db2 = self.params[2] * time_full / self.params[3]**2 * exp_term_2
        dy_dc = np.ones_like(time_full)

        grad = np.stack([dy_da1, dy_db1, dy_da2, dy_db2, dy_dc], axis=1)

        # sigma_y^2 = grad^T @ cov @ grad, do this element-wise across x
        current_pred_errs_sq = np.einsum('ij,jk,ik->i', grad, self.param_cov, grad)
        self.current_pred_errs = np.sqrt(current_pred_errs_sq)

        return self.current_pred, self.current_pred_errs

    def get_plateau(self):

        return self.params[4], self.param_errors[4]

    def get_time_const(self):

        return [self.params[1], self.params[3]], [self.param_errors[1], self.param_errors[3]]

class ShiftedExponential(FittingAlgorithms):
    """
    """

    @staticmethod
    def shifted_exponential(x, a, b, c, d):
        with np.errstate(divide='ignore'):
            return a * np.exp(- (x - d) / b) + c

    def fit(self, omit_errors=False):

        time_fit = self.time_fit.copy() - np.min(self.time_fit)

        sigma = None
        absolute_sigma = False

        if not omit_errors and self.current_fit_errs.any():
            sigma = self.current_fit_errs
            absolute_sigma = True

        self.params, self.param_cov = curve_fit(self.shifted_exponential, time_fit, self.current_fit,
                                                sigma=sigma, absolute_sigma=absolute_sigma, maxfev=100000)
        self.param_errors = np.sqrt(np.diag(self.param_cov))

        print(self.params)
        print(self.param_errors)

    def get_fit_pred(self):

        time_full = self.time_full.copy() - np.min(self.time_full)

        self.current_pred = self.shifted_exponential(time_full, self.params[0], self.params[1],
                                                     self.params[2], self.params[3])

        # self.current_pred_errs = np.sqrt(np.exp(-2*self.params[1]*time_full) *
        #                             (self.param_errors[0]**2 + (self.params[0] * time_full * self.param_errors[1])**2)+
        #                             self.param_errors[2]**2)

        # Partial derivatives (gradient vector)
        exp_term = np.exp(- (time_full - self.params[3]) / self.params[1])
        dy_da = exp_term
        dy_db = self.params[0] * (time_full - self.params[3])  / self.params[1]**2 * exp_term
        dy_dc = np.ones_like(time_full)
        dy_dd = self.params[0] * 1/self.params[1] * exp_term

        grad = np.stack([dy_da, dy_db, dy_dc, dy_dd], axis=1)  # shape (4, N) if x is an array

        # sigma_y^2 = grad^T @ cov @ grad, do this element-wise across x
        current_pred_errs_sq = np.einsum('ij,jk,ik->i', grad, self.param_cov, grad)
        self.current_pred_errs = np.sqrt(current_pred_errs_sq)

        return self.current_pred, self.current_pred_errs

    def get_plateau(self):

        return self.params[2], self.param_errors[2]

    def get_time_const(self):

        return self.params[1], self.param_errors[1]

