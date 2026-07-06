"""
Author : Divij Gupta
Adapted from : Albanik Gashi

Description : Modified from osctools.py for data taken using (now) automated probe station and some additional functionality

Analysis code which covers current-time measurements. Developed specifically with the RadTol experiment (2026 Q1) in mind
but can be used generally.

Notice:
This code is not to be redistributed without the prior written consent of the author.

Things to add:
- Strictly speaking there should be one object per instance, same object shouldn't be reused in analyis
- Errors on points ? -> would make the whole plot too busy

"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

from IPython.display import display, HTML
from numpy.ma.extras import average
from scipy.stats import alpha
from tinycss2.ast import AtRule

style_path = os.path.join(os.path.dirname(__file__), "plot_style.mplstyle")
plt.style.use(style_path)
# plt.style.use('../plot_style.mplstyle')
plt.rcParams.update({
    "text.usetex": False,
    "text.latex.preamble": r"\usepackage{amsmath}"
})

from matplotlib.ticker import AutoMinorLocator
from matplotlib.ticker import ScalarFormatter

from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# OS for filename listing
from os import listdir
from os.path import isfile, join
from os import walk
from IPython.display import display, HTML

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from BaselineAlgorithms import *


class Timeseries:
    """
    Timeseries Object:
    
    To be used for any Current - Time measurements taken, commonly referred to the time dynamic technique.
    """

    def __init__(self, input_path, output_path=None, dataset=None, dataset_errors=None, mask_OFF=None, mask_ON=None,
                 timestamps_ON=[[]], timestamps_OFF=[[]], title_addition='',
                 baseline_burnin=0, mask_burnin=None, baseline_filled=None, dataset_baselined=None,
                 baseline_method : FittingAlgorithms=Exponential(), analysis_methods : FittingAlgorithms=Exponential(),
                 dark_type_accept='plat', signal_accept=None, average_samples=False):
        """
        Initialsises the relevant parameters of the Timeseries object.
        filename: default => empty; the path and filename of the dataset of interest.
        machine: default => "K4200A"; used to set the time_str and current_str default column titles, must be predefined in __init__
        if the data is from a non-standard machine the user must define time_str and current_str 
        
        Below includes the initialisation of each parameter, they are organised by the function in which they first appear, comments indicate the function name.
        """

        # Previous code turns all files into csv files ready for analysis
        if dataset:
            self.dataset = dataset
        else:
            self.dataset = np.genfromtxt(input_path, delimiter=',', skip_header=1, encoding='utf-8-sig')

        self.dataset = self.dataset[:, :2]

        if dataset_errors is None:
            dataset_errors = np.zeros(len(self.dataset))
        else:
            if type(dataset_errors) is float:
                dataset_errors = np.ones(len(self.dataset)) * dataset_errors
            else:
                dataset_errors = np.array(dataset_errors)
        self.dataset = np.column_stack((self.dataset, dataset_errors))

        # Parameters from the filename
        self.filename = input_path.split("/")[-1]
        self.filename = '.'.join(self.filename.split('.')[:-1])
        if title_addition:
            self.filename += f'_{title_addition}'

        if output_path:
            self.output_path = output_path
        else:
            self.output_path = f'{input_path.split("/")[:-1]}/Output'

        # SEE SetOff and SetOn functions
        self.timestamps_ON = timestamps_ON
        self.timestamps_OFF = timestamps_OFF
        self.mask_OFF = mask_OFF
        self.mask_ON = mask_ON

        # self.noalpha = True                                 # Set to false if the SetOn function is called

        # SEE Baseline Function
        self.baseline_burnin = baseline_burnin
        if mask_burnin:
            self.mask_burnin = mask_burnin
        else:
            self.mask_burnin = self.dataset[:, 0] > self.baseline_burnin
        self.dataset_cut = self.dataset[self.mask_burnin]
        self.baseline_filled = baseline_filled
        self.dataset_baselined = dataset_baselined

        self.baseline_method = baseline_method

        if type(analysis_methods) is list:
            self.analysis_methods = analysis_methods
        else:
            self.analysis_methods = [analysis_methods] * len(self.timestamps_ON)

        self.summary_parameters = None

        self.fit_params_baseline = []
        self.fit_params_ON = []
        self.fit_data_ON = []

        self.dark_type_accept = dark_type_accept
        if signal_accept is None:
            self.signal_accept = [True] * len(self.timestamps_ON)
        else:
            self.signal_accept = signal_accept

        self.average = average_samples

    def check_compliance(self):

        if np.std(self.dataset[:, 1]) * 1e12 < 0.5:
            return True
        else:
            return False

    def set_OFF(self, timestamps_OFF=None, buffer_OFF=0):
        """
        This function sets the OFF times of the data (referring) to radiation.

        No alpha radiation is present here, therefore this should only consider the dark current.
        """

        # Adding a time buffer on either side to exclude in off period
        if buffer_OFF != 0:
            for i, timestamp_OFF in enumerate(timestamps_OFF):
                timestamps_OFF[i] = [timestamp_OFF[0]+buffer_OFF, timestamp_OFF[1]-buffer_OFF]
        
        # Global: required for plotting functions.
        if timestamps_OFF is not None:
            self.timestamps_OFF = timestamps_OFF

        # Defining the mask for all radiation off periods
        timestamps = self.dataset[:, 0]
        mask = np.zeros_like(timestamps, dtype=bool)
        for start, end in self.timestamps_OFF:
            mask |= (timestamps >= start) & (timestamps <= end)
        self.mask_OFF = mask

    def set_ON(self, timestamps_ON=None, buffer_ON=0):
        """
        This function sets the ON times of the data (referring) to radiation.
        
        ALPHA radiation present is ON.
        """

        # if timestamps_ON:
        #     self.noalpha = False                            # User has defined some peaks

        # Adding a time buffer on either side to exclude in off period
        if buffer_ON != 0:
            for i, timestamp_ON in enumerate(timestamps_ON):
                timestamps_ON[i] = [timestamp_ON[0] + buffer_ON, timestamp_ON[1] - buffer_ON]

        # Global: required for plotting functions.
        if timestamps_ON is not None:
            self.timestamps_ON = timestamps_ON

        # Defining the mask for all radiation off periods
        timestamps = self.dataset[:, 0]
        mask = np.zeros_like(timestamps, dtype=bool)
        for start, end in self.timestamps_ON:
            mask |= (timestamps >= start) & (timestamps <= end)
        self.mask_ON = mask

    def baseline(self, method : FittingAlgorithms=None, baseline_burnin=None, show_fit=False, show_params=False):
        """
        This function strips the dataset of the ON sections and fits a baseline function for background subtraction.

        cut_initial : default => 20 seconds of the timeseries data is cut off to assist with the baseline.
        method : default => GPR; uses the Gaussian Process Regressor code developed by Taifakou FE in "timeseries.py",
            other methods may include polynomials and exponentials
        kernel : default => kernels.Matern(); determines the shape of the GP, inherited by Taifakou FE in "timeseries.py"
        """

        # Update burn in time if new value is supplied by the user
        if baseline_burnin is not None:
            self.baseline_burnin = baseline_burnin

            # Extract mask for data not in burn in time
            self.mask_burnin = self.dataset[:, 0] > self.baseline_burnin

            # Use masks to extract data to be used in fitting
            self.dataset_cut = self.dataset[self.mask_burnin]

        if method is not None:
            self.baseline_method = method

        # Needs to be done like this since mask_OFF and self.dataset need to have the same length
        baseline_unfilled = self.dataset[self.mask_burnin & self.mask_OFF]

        # Perform baseline fitting as determined by the user and store for later use
        self.baseline_method.initialise_data(baseline_unfilled[:, 0], baseline_unfilled[:, 1],
                               baseline_unfilled[:, 2], self.dataset_cut[:, 0])
        self.baseline_method.fit()
        baseline_output = self.baseline_method.get_fit_pred()

        if len(baseline_output) == 2:
            baseline_current, baseline_current_errs = baseline_output
        else:
            baseline_current = baseline_output
            baseline_current_errs = np.zeros(len(baseline_current))

        self.baseline_filled = np.column_stack((self.dataset_cut[:, 0], baseline_current, baseline_current_errs))

        # Calculate and store dataset after baselining
        dataset_baselined_current_errs = np.sqrt(np.power(self.dataset_cut[:, 2], 2) +
                                                 np.power(self.baseline_filled[:, 2], 2))
        self.dataset_baselined = np.column_stack((self.dataset_cut[:, 0],
                                                  self.dataset_cut[:, 1] - self.baseline_filled[:, 1],
                                                  dataset_baselined_current_errs))

        self.fit_params_baseline = np.concatenate((self.baseline_method.get_plateau(), [self.baseline_method.get_noise()]))

        try:
            # self.fit_params_baseline += self.baseline_method.get_time_const()
            self.fit_params_baseline = np.concatenate((self.fit_params_baseline, self.baseline_method.get_time_const()))
        except AttributeError:
            pass

        # Maybe add chi2 or residual plot to show a type of fitting score ?

        if show_params:
            return self.baseline_method.show_params()

        if show_fit:
            self.baseline_method.plot(show_plateau=True)

    def _plot_helper(self, title):

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

        ax.axhline(y=0, color='k', linestyle='-', alpha=0.2)
        # ax.axvline(x=0, color='k', linestyle='-', alpha=0.2)
        ax.set_xlim([-2, np.max(self.dataset[:, 0])+5])

        ax.set_title(title, y=1.01)

        return fig, ax

    def plot_raw(self, y_lim=None, show_plot=True, save_plot=False):

        title = f"{self.filename}_raw"
        fig, ax = self._plot_helper(title)

        ax.scatter(self.dataset[:, 0], self.dataset[:, 1] * 1e12, c='k', marker='.', s=3)
        ax.set_ylim(y_lim)

        plt.tight_layout()
        if save_plot:
            os.makedirs(self.output_path, exist_ok=True)
            # plt.savefig(f'{self.output_path}/{title}.jpg', dpi=1200)
            # plt.savefig(f'{self.output_path}/{title}.png', dpi=1200)
            plt.savefig(f'{self.output_path}/{title}.pdf', dpi=1200)
            print(f"Plot saved to : {self.output_path}/{title}.pdf")
        if show_plot:
            plt.show()
        else:
            plt.close()

    @staticmethod
    def _legend_locator(x, y, ax, location_trials):

        # Keep prefered legend first since it will default to that if no of overlap points is identical

        # x cuttoff, y cuttoff (in percentage form)
        cutoffs = []
        for location_trial in location_trials:
            if location_trial == 'upper right':
                cutoffs.append([60, 70])
            elif location_trial == 'lower right':
                cutoffs.append([60, 30])
            elif location_trial == 'upper left':
                cutoffs.append([40, 70])
            elif location_trial == 'lower left':
                cutoffs.append([40, 30])
            else:
                print('Invalid legend location, please check')

        y_lims = ax.get_ylim()
        x_lims = ax.get_xlim()

        # Only looking at the current points within the plot window
        mask_x = (x < x_lims[1]) & (x > x_lims[0])
        mask_y = (y < y_lims[1]) & (y > y_lims[0])
        plot_mask = mask_x & mask_y
        y_plot = y[plot_mask]
        x_plot = x[plot_mask]

        overlaps = []
        for x_cutoff, y_cutoff in cutoffs:

            x_cutoff_val = x_cutoff/100 * (x_lims[1] - x_lims[0]) + x_lims[0]
            if x_cutoff >= 50:
                x_mask = x_plot > x_cutoff_val
            else:
                x_mask = x_plot < x_cutoff_val

            y_cutoff_val = y_cutoff/100 * (y_lims[1] - y_lims[0]) + y_lims[0]
            if y_cutoff >= 50:
                overlap = np.sum(y_plot[x_mask] > y_cutoff_val)
            else:
                overlap = np.sum(y_plot[x_mask] < y_cutoff_val)

            overlaps.append(overlap)

        return location_trials[np.argmin(overlaps)]

    def plot_initial(self, y_lim=None, save_plot=False, show_plot=True):

        title = f"{self.filename}_initial"
        fig, ax = self._plot_helper(title)

        time = self.dataset[:, 0]
        current = self.dataset[:, 1] * 1e12

        colours = np.full(len(current), 'black')
        legend_handles = [Line2D([0], [0], color='w', marker='.', markerfacecolor='black', label='Raw Data')]

        if self.mask_ON is not None:
            colours[self.mask_ON] = 'cyan'
            legend_handles.append(Line2D([0], [0], color='w', marker='.', markerfacecolor='cyan', label='Rad ON'))

        if self.mask_OFF is not None:
            colours[self.mask_OFF] = 'red'
            legend_handles.append(Line2D([0], [0], color='w', marker='.', markerfacecolor='red', label='Rad OFF'))

        if (self.mask_ON is not None and self.mask_OFF is not None and
                np.any(self.mask_ON & self.mask_OFF)):
            print("Warning: overlap between ON and OFF periods")
            colours[self.mask_ON & self.mask_OFF] = 'purple'
            legend_handles.append(Line2D([0], [0], color='w', marker='.', markerfacecolor='green', label='Overlap!'))

        if self.baseline_burnin != 0:
            ax.axvline(self.baseline_burnin, color='grey', alpha=0.7, linestyle='--', label='Burn in')
            legend_handles.append(Line2D([0], [0], color='grey', alpha=0.7, linestyle='--', label='Burn in'))

        if self.baseline_filled is not None:
            ax.plot(self.baseline_filled[:, 0], self.baseline_filled[:, 1] * 1e12,
                    linestyle='--', color='tab:blue')
            baseline_filled_err = np.sqrt(self.baseline_filled[:, 2]**2 + self.fit_params_baseline[2]**2)
            ax.fill_between(self.baseline_filled[:, 0],
                            (self.baseline_filled[:, 1] - baseline_filled_err)*1e12,
                            (self.baseline_filled[:, 1] + baseline_filled_err)*1e12,
                            alpha=0.3, color='tab:blue')
            legend_handles.append(Line2D([0], [0], color='tab:blue', linestyle='-', label='Baseline Fit'))
            legend_handles.append(Patch(facecolor='tab:blue', edgecolor='tab:blue', alpha=0.3, label=r'Baseline Fit 1$\sigma$'))

        if self.fit_params_baseline is not None:
            baseline_current = self.fit_params_baseline[0] * 1e12
            baseline_current_err = np.sqrt(self.fit_params_baseline[1]**2 + self.fit_params_baseline[2]**2) * 1e12
            ax.plot([self.baseline_burnin, time[-1]], [baseline_current, baseline_current],
                    color='green', linestyle='--')
            ax.fill_between([self.baseline_burnin, time[-1]], [baseline_current - baseline_current_err, baseline_current - baseline_current_err],
                            [baseline_current + baseline_current_err, baseline_current + baseline_current_err],
                            alpha=0.3, color='green')
            legend_handles.append(Line2D([0], [0], color='green', linestyle='-', label='Baseline I'))
            legend_handles.append(Patch(facecolor='green', edgecolor='green', alpha=0.3, label=r'Baseline I 1$\sigma$'))

        ax.scatter(time, current, c=colours, marker='.', s=3)

        if y_lim == 'auto':
            current_cut = self.dataset_cut[:, 1] * 1e12
            current_cut_mean = np.mean(current_cut)
            current_cut_std = np.std(current_cut)
            current_cut_masked = current_cut[(current_cut < (current_cut_mean + 5*current_cut_std)) &
                                             (current_cut > (current_cut_mean - 5*current_cut_std))]
            current_cut_max = np.max(current_cut_masked)
            current_cut_min = np.min(current_cut_masked)

            y_lim_lower = current_cut_min - current_cut_std
            y_lim_upper = current_cut_max + current_cut_std

            y_lim = [y_lim_lower, y_lim_upper]

        ax.set_ylim(y_lim)

        legend_location = self._legend_locator(self.dataset_cut[:, 0], self.dataset_cut[:, 1] * 1e12, ax,
                                               location_trials=['upper right', 'lower right'])
        plt.legend(handles=legend_handles, loc=legend_location,
                   borderpad=0.4, labelspacing=0.6, edgecolor="white", facecolor="white", fancybox=True,
                   ncol=3, columnspacing=0.9, handletextpad=0.4, markerscale=2)

        plt.tight_layout()
        if save_plot:
            os.makedirs(self.output_path, exist_ok=True)
            # plt.savefig(f'{self.output_path}/{title}.jpg', dpi=1200)
            # plt.savefig(f'{self.output_path}/{title}.png', dpi=1200)
            plt.savefig(f'{self.output_path}/{title}.pdf', dpi=1200)
            print(f"Plot saved to : {self.output_path}/{title}.pdf")
        if show_plot:
            plt.show()
        else:
            plt.close()

    def do_analysis(self, method : FittingAlgorithms=None, show_fit=False, get_data=False):
        """
        This function should use information gathered from the baseline to determine the deltaI values and the
        leakage current values for each region. Should work regardless of the number of irradiated periods.
        """

        # if self.noalpha:
        #     self.summary_parameters = \
        #         ("No radiation is present therefore no analysis summary is performed and only a capacitor fit is done.\n"
        #          "\tIf this is not the case please check the SetOFF & SetOn methods have been used.")
        #
        #     # this should conduct a capacitance fit on the whole dataset:
        #     method.initialise_data(self.dataset[:, 0], self.dataset[:, 1], self.dataset[:, 2], self.dataset[:, 0])
        #     method.fit()
        #     method.show_params()
        #     return

        if method is not None:
            if type(method) is list:
                self.analysis_methods = method
            else:
                self.analysis_methods = [method] * len(self.timestamps_ON)

        time = self.dataset_baselined[:, 0]
        current = self.dataset_baselined[:, 1]
        current_err = self.dataset_baselined[:, 2]

        # Calculating the deltaI & noise

        for ind, (start, end) in enumerate(self.timestamps_ON):

            mask = (time >= start) & (time <= end)
            time_masked = time[mask]

            analysis_method = self.analysis_methods[ind]
            analysis_method.initialise_data(time_masked, current[mask], current_err[mask], time_masked, offset=True)
            analysis_method.fit()

            deltaI, deltaI_err = analysis_method.get_plateau()
            deltaI_noise = analysis_method.get_noise()
            fit_params_ON_i = [deltaI, deltaI_err, deltaI_noise]
            try:
                fit_params_ON_i += analysis_method.get_time_const()
            except AttributeError:
                pass
            self.fit_params_ON.append(fit_params_ON_i)

            current_pred, current_pred_err = analysis_method.get_fit_pred()
            data_pred = np.column_stack((time_masked, current_pred, current_pred_err))
            self.fit_data_ON.append(data_pred)

            if show_fit:
                analysis_method.plot(show_plateau=True)

        time_dark = self.dataset[:, 0]
        current_dark = self.dataset[:, 1]
        current_dark_err = self.dataset[:, 2]
        dark_end_mask = (time_dark >= self.timestamps_OFF[-1][0]) & (time_dark <= self.timestamps_OFF[-1][1])
        dark_end_obj = Constant()
        dark_end_obj.initialise_data(time_dark[dark_end_mask], current_dark[dark_end_mask],
                                     current_dark_err[dark_end_mask], time_dark[dark_end_mask])
        dark_end_obj.fit()
        if show_fit:
            dark_end_obj.plot(show_plateau=True)
        dark_end, dark_end_err = dark_end_obj.get_plateau()

        # Several sources of noise:
        # - Fit error
        # - Noise error on dark current intrinsic
        # - Noise of alpha source irradiation energy deposition (statistical decay) -> larger noise at higher standoff

        self.summary_parameters = pd.DataFrame(columns=[
            "Dark Fit", "Dark Accept", "Sig Fit", "Sig Accept",
            "Delta I [A]", "Delta I Err [A]", "Delta I Noise [A]", "Dark Noise [A]", "Sig Noise [A]",
            "SNR Dark", "SNR Dark Err", "Dark Plat [A]", "Dark Plat Err [A]", "SDR Plat", "SDR Plat Err",
            "Dark End [A]", "Dark End Err [A]", "SDR End", "SDR End Err",
            "RC Dark [s]", "RC Dark Err [s]", "RC Sig [s]", "RC Sig Err [s]"])

        analysis_method_names = [i.__class__.__name__ for i in self.analysis_methods]

        for ind, fit_params_ON_i in enumerate(self.fit_params_ON):

            deltaI = fit_params_ON_i[0]
            deltaI_err = fit_params_ON_i[1]
            dark_plat = self.fit_params_baseline[0]
            dark_plat_err = self.fit_params_baseline[1]

            dark_noise = self.fit_params_baseline[2]
            deltaI_noise = fit_params_ON_i[2]
            noise_delta = deltaI_noise**2 - dark_noise**2
            if noise_delta > 0:
                sig_noise = np.sqrt(deltaI_noise**2 - dark_noise**2)
            else:
                sig_noise = dark_noise

            deltaI_err_full = np.sqrt(deltaI_err**2 + deltaI_noise**2)
            dark_plat_err_full = np.sqrt(dark_plat_err**2 + dark_noise**2)
            dark_end_err_full = np.sqrt(dark_end_err**2 + dark_noise**2)

            snr_dark = np.abs(deltaI / dark_noise)
            snr_dark_err = deltaI_err_full / dark_noise

            sdr_plat = np.abs(deltaI / dark_plat)
            sdr_plat_err = np.sqrt( (1 / dark_plat**2) * (deltaI_err_full**2 + (sdr_plat * dark_plat_err_full)**2) )

            sdr_end = np.abs(deltaI / dark_end)
            sdr_end_err = np.sqrt( (1 / dark_end**2) * (deltaI_err_full**2 + (sdr_end * dark_end_err_full)**2) )

            summary_params_i = [
                self.baseline_method.__class__.__name__, self.dark_type_accept,
                analysis_method_names[ind], self.signal_accept[ind],
                deltaI, deltaI_err, deltaI_noise, dark_noise, sig_noise,
                snr_dark, snr_dark_err, dark_plat, dark_plat_err, sdr_plat, sdr_plat_err,
                dark_end, dark_end_err, sdr_end, sdr_end_err]

            try:
                summary_params_i += [self.fit_params_baseline[3], self.fit_params_baseline[4]]
            except IndexError:
                summary_params_i += [np.nan, np.nan]

            try:
                summary_params_i += [fit_params_ON_i[3], fit_params_ON_i[4]]
            except IndexError:
                summary_params_i += [np.nan, np.nan]

            self.summary_parameters.loc[ind] = summary_params_i

        if self.average:

            if len(set(analysis_method_names)) == 1:
                analysis_method_names_avg = analysis_method_names[0]
            else:
                analysis_method_names_avg = 'Mixed'

            deltaI_weights = 1 / (self.summary_parameters["Delta I Err [A]"]**2 + self.summary_parameters["Delta I Noise [A]"]**2)
            deltaI_avg = np.average(self.summary_parameters["Delta I [A]"], weights=deltaI_weights)
            deltI_avg_err = np.sqrt(1 / np.sum(deltaI_weights))

            snr_dark_weights = 1 / self.summary_parameters["SNR Dark Err"]**2
            snr_dark_avg = np.average(self.summary_parameters["SNR Dark"], weights=snr_dark_weights)
            snr_dark_avg_err = np.sqrt(1 / np.sum(snr_dark_weights))

            sdr_plat_weights = 1 / self.summary_parameters["SDR Plat Err"]**2
            sdr_plat_avg = np.average(self.summary_parameters["SDR Plat"], weights=sdr_plat_weights)
            sdr_plat_avg_err = np.sqrt(1 / np.sum(sdr_plat_weights))

            sdr_end_weights = 1 / self.summary_parameters["SDR End Err"]**2
            sdr_end_avg = np.average(self.summary_parameters["SDR End"], weights=sdr_end_weights)
            sdr_end_avg_err = np.sqrt(1 / np.sum(sdr_end_weights))

            summary_params_avg = [
                self.baseline_method.__class__.__name__, self.dark_type_accept, analysis_method_names_avg, any(self.signal_accept),
                deltaI_avg, deltI_avg_err, np.mean(self.summary_parameters["Delta I Noise [A]"]),
                self.summary_parameters["Dark Noise [A]"][0], np.mean(self.summary_parameters["Sig Noise [A]"]),
                snr_dark_avg, snr_dark_avg_err, self.summary_parameters["Dark Plat [A]"][0],
                np.sqrt(self.summary_parameters["Dark Plat Err [A]"][0]**2 + self.summary_parameters["Dark Noise [A]"][0]**2),
                sdr_plat_avg, sdr_plat_avg_err, self.summary_parameters["Dark End [A]"][0],
                np.sqrt(self.summary_parameters["Dark End Err [A]"][0]**2 + self.summary_parameters["Dark Noise [A]"][0]**2),
                sdr_end_avg, sdr_end_avg_err]

            if self.summary_parameters["RC Dark [s]"][0] == np.nan:
                summary_params_avg += [np.nan, np.nan]
            else:
                summary_params_avg += [self.summary_parameters["RC Dark [s]"][0], self.summary_parameters["RC Dark Err [s]"][0]]

            RC_sig_mask = [~np.isnan(i) for i in self.summary_parameters["RC Sig [s]"]]
            if any(RC_sig_mask):
                RC_sig_weights = 1 / self.summary_parameters["RC Sig Err [s]"][RC_sig_mask]**2
                RC_sig_avg = np.average(self.summary_parameters["RC Sig [s]"][RC_sig_mask], weights=RC_sig_weights)
                RC_sig_avg_err = np.sqrt(1 / np.sum(RC_sig_weights))
                summary_params_avg += [RC_sig_avg, RC_sig_avg_err]
            else:
                summary_params_avg += [np.nan, np.nan]

            self.summary_parameters.loc[-1] = summary_params_avg

        if get_data:
            return self.summary_parameters

    def plot_baselined(self, y_lim=[-5, None], save_plot=False, show_plot=True):

        title = f"{self.filename}_baselined"
        fig, ax = self._plot_helper(title)

        time = self.dataset_baselined[:, 0]
        current = self.dataset_baselined[:, 1] * 1e12

        # colours = np.full(len(current), 'black')
        #
        # if self.mask_ON is not None:
        #     colours[self.mask_ON[self.mask_burnin]] = 'cyan'
        #     legend_handles.append(Line2D([0], [0], color='w', marker='o', markerfacecolor='cyan', label='Rad ON'))
        #
        # if self.mask_OFF is not None:
        #     colours[self.mask_OFF[self.mask_burnin]] = 'red'
        #     legend_handles.append(Line2D([0], [0], color='w', marker='o', markerfacecolor='red', label='Rad OFF'))
        #
        # if (self.mask_ON is not None and self.mask_OFF is not None and
        #         np.any(self.mask_ON & self.mask_OFF)):
        #     print("Warning: overlap between ON and OFF periods")
        #     colours[self.mask_ON & self.mask_OFF] = 'green'
        #     legend_handles.append(Line2D([0], [0], color='w', marker='o', markerfacecolor='green', label='Overlap!'))

        ax.scatter(time, current, c='k', marker='.', s=3, label='Data')

        if self.mask_ON is not None:
            for ind, (start, end) in enumerate(self.timestamps_ON):
                ax.axvspan(start, end, color='cyan', alpha=0.1, label='Rad ON' if ind == 0 else None)

        for ind, data_ON in enumerate(self.fit_data_ON):
            time_ON = data_ON[:, 0]
            current_ON = data_ON[:, 1] * 1e12
            current_err_ON = np.sqrt(data_ON[:, 2]**2 + self.fit_params_ON[ind][2]**2) * 1e12
            ax.plot(time_ON, current_ON, c='red', linestyle='--', label='Fit' if ind == 0 else None)
            ax.fill_between(time_ON, current_ON - current_err_ON, current_ON + current_err_ON,
                            alpha=0.3, color='red', label=r'Fit 1$\sigma$' if ind == 0 else None)

        for ind, params_ON in enumerate(self.fit_params_ON):
            deltaI_ON = params_ON[0] * 1e12
            deltaI_err_ON = np.sqrt(params_ON[1]**2 + params_ON[2]**2) * 1e12
            time_start, time_end = self.timestamps_ON[ind]
            ax.plot([time_start, time_end], [deltaI_ON, deltaI_ON], c='green', linestyle='--',
                    label=r'$\Delta$I' if ind == 0 else None)
            ax.fill_between([time_start, time_end], [deltaI_ON - deltaI_err_ON, deltaI_ON - deltaI_err_ON],
                            [deltaI_ON + deltaI_err_ON, deltaI_ON + deltaI_err_ON],
                            alpha=0.3, color='green', label=r'$\Delta$I 1$\sigma$' if ind == 0 else None)

        if y_lim == 'auto':
            current_baselined_mean = np.mean(current)
            current_baselined_std = np.std(current)
            mask = ((current < (current_baselined_mean + 5 * current_baselined_std)) &
                    (current > (current_baselined_mean - 5 * current_baselined_std)))
            current_baselined_masked = current[mask]
            current_cut_masked = self.dataset_cut[:, 1][mask] * 1e12
            baseline_std = np.std(current[self.mask_OFF[self.mask_burnin]])

            if np.max(current_cut_masked) < 0:
                y_lim_upper = 5 * baseline_std
            else:
                y_lim_upper = np.max(current_baselined_masked) + current_baselined_std

            if np.min(current_cut_masked) > 0:
                y_lim_lower = - 5 * baseline_std
            else:
                y_lim_lower = np.min(current_baselined_masked) - current_baselined_std

            y_lim = [y_lim_lower, y_lim_upper]

        ax.set_ylim(y_lim)

        legend_location = self._legend_locator(time, current, ax, location_trials=['upper right', 'lower right'])

        if not self.summary_parameters.empty:
            text = []
            for j, params_i in self.summary_parameters.iterrows():
                text_add = fr'$\Delta$I = {params_i['Delta I [A]']*1e12:.3f} $\pm$ ({params_i['Delta I Err [A]']*1e12:.3f} + {params_i['Delta I Noise [A]']*1e12:.3f}) pA'
                if self.signal_accept[j] is False:
                    text_add += ' (omitted)'
                text.append(text_add)
                # text.append(fr'SNR = {params_i['SNR']:.3f}')
                # text.append(fr'SDR = {params_i['SDR_plat']:.3f} $\pm$ {params_i['SDR_plat_err']:.3f}')
            if self.average:
                text[-1] = fr'$\Delta$I (average) = {self.summary_parameters.loc[-1]['Delta I [A]']*1e12:.3f} $\pm$ {self.summary_parameters.loc[-1]['Delta I Err [A]']*1e12:.3f} pA'
            if self.dark_type_accept.lower() == 'plat':
                text.append(fr'Dark (fit) = {self.summary_parameters.loc[0]['Dark Plat [A]'] * 1e12:.3f} $\pm$ ({self.summary_parameters.loc[0]['Dark Plat Err [A]'] * 1e12:.3f} + {self.summary_parameters.loc[0]['Dark Noise [A]'] * 1e12:.3f}) pA')
            elif self.dark_type_accept.lower() == 'end':
                text.append(fr'Dark (end) = {self.summary_parameters.loc[0]['Dark End [A]'] * 1e12:.3f} $\pm$ ({self.summary_parameters.loc[0]['Dark End Err [A]'] * 1e12:.3f} + {self.summary_parameters.loc[0]['Dark Noise [A]'] * 1e12:.3f}) pA')
            else:
                print("Invalid method for determining dark current, need to be : 'plat' or 'end'")
            text = '\n'.join(text)

            text_location = self._legend_locator(time, current, ax, location_trials=['upper left', 'lower left'])
            x, y = 0.03, 0.9625
            va = 'top'
            if text_location == 'lower left':
                x, y = 0.03, 0.04
                va = 'bottom'

            ax.text(x, y, text, transform=ax.transAxes, linespacing=1.6, ha='left', va=va,
                    bbox=dict(boxstyle='round,pad=0.4', edgecolor='white', facecolor='white', alpha=0.8))

        plt.legend(loc=legend_location, borderpad=0.4, labelspacing=0.6, edgecolor="white",
                   facecolor="white", fancybox=True, handletextpad=0.4, ncol=2, columnspacing=0.9, markerscale=5)

        plt.tight_layout()
        if save_plot:
            os.makedirs(self.output_path, exist_ok=True)
            # plt.savefig(f'{self.output_path}/{title}.jpg', dpi=1200)
            # plt.savefig(f'{self.output_path}/{title}.png', dpi=1200)
            plt.savefig(f'{self.output_path}/{title}.pdf', dpi=1200)
            print(f"Plot saved to : {self.output_path}/{title}.pdf")
        if show_plot:
            plt.show()
        else:
            plt.close()

    def main(self, show_plots=True, save_plots=False, get_data=False, save_data=False, show_fits=False):

        if self.check_compliance():
            self.plot_raw(save_plot=save_plots, show_plot=show_plots)
            print(f"Data at compliance (skipped) : {self.filename}")
            return None

        self.plot_raw(save_plot=save_plots, show_plot=show_plots)
        self.set_OFF()
        self.set_ON()
        self.baseline(show_fit=show_fits)
        self.plot_initial(y_lim='auto', show_plot=show_plots, save_plot=save_plots)
        self.do_analysis(show_fit=show_fits)
        self.plot_baselined(y_lim='auto', show_plot=show_plots, save_plot=save_plots)

        if save_data:
            os.makedirs(self.output_path, exist_ok=True)
            self.summary_parameters.to_csv(f"{self.output_path}/{self.filename}_summary_parameters.csv", index=False)
            print(f"Data saved to : {self.output_path}/{self.filename}_summary_parameters.csv")

        if get_data:
            return self.summary_parameters


def plot_long(file_name, output_path=None, x_units='s', y_lim=None, show_plot=False, save_plot=False):

    dataset = np.genfromtxt(file_name, delimiter=',', skip_header=1, encoding='utf-8-sig')
    dataset = dataset[:, :2]

    title = file_name.split("/")[-1]
    title = '.'.join(title.split('.')[:-1])

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

    ax.set_ylabel('Current [pA]', loc='top', labelpad=10)

    ax.axhline(y=0, color='k', linestyle='-', alpha=0.2)
    # ax.axvline(x=0, color='k', linestyle='-', alpha=0.2)

    ax.set_title(f"{title}_long", y=1.01)

    if x_units == 's':
        x_scale = 1
    elif x_units == 'min':
        x_scale = 60
    elif x_units == 'hours':
        x_scale = 3600
    elif x_units == 'days':
        x_scale = 86400
    else:
        print('x_units not recognized')

    ax.set_xlabel('Time [s]', loc='right', labelpad=10)

    ax.scatter(dataset[:, 0]/x_scale, dataset[:, 1] * 1e12, c='k', marker='.', s=3)
    ax.set_ylim(y_lim)

    ax.set_xlabel(f'Time [{x_units}]', loc='right', labelpad=10)
    scaling = np.max(dataset[:, 0] / x_scale) * 0.02
    ax.set_xlim([np.min(dataset[:, 0] / x_scale) - scaling, np.max(dataset[:, 0] / x_scale) + scaling])

    plt.tight_layout()
    if save_plot:
        if output_path is None:
            print("Must give an output path!")
            return
        os.makedirs(output_path, exist_ok=True)
        # plt.savefig(f'{self.output_path}/{title}.jpg', dpi=1200)
        # plt.savefig(f'{self.output_path}/{title}.png', dpi=1200)
        plt.savefig(f'{output_path}/{title}.pdf', dpi=1200)
        print(f"Plot saved to : {output_path}/{title}.pdf")
    if show_plot:
        plt.show()
    else:
        plt.close()


# dg032_1_electrical = Timeseries('../Raw Data/RadTol/ProbeStation/Before/DG032/DG032-1_dynamics_3V_1.5mm_12mm.csv',
#                                 output_path='../Results/RadTol/ProbeStation/Before/DG032',
#                                 timestamps_OFF=[[5, 25], [72, 95], [145, 170]], timestamps_ON=[[38, 62], [109, 134]],
#                                 dataset_errors=10e-15, baseline_burnin=6.5,
#                                 baseline_method=Exponential(), analysis_methods=Constant())
# params = dg032_1_electrical.main(get_data=True, show_plots=True, save_plots=False, save_data=False, show_fits=True)
# print(params)



# #====================================SaveData FUNCTION=======================================#
#     def SaveData(self):
#         """
#         This function saves all the data into csv files, ready for futher analysis, and figure creation. This should be the final
#         function called in the analysis portfolio.
#
#         This function should print the location of all files saved any what they contain.
#
#         ONLY Save parts of the analysis that have been completed and alert the user if some analysis hasnt been performed
#
#         Should save the baseline dataset & the summary parameters as a starter
#         """
#
#         #saving the summary_parameters
#         self.summary_parameters.to_csv((self.file[:-4]+"summary_parameters.csv"),index=False)
#         print("DATA SAVED: " +(self.file[:-3]+"summary_parameters.csv"))
#
#         self.baseline_dataset.to_csv((self.file[:-4]+"baselined_dataset.csv"),index=False)
#         print("\nDATA SAVED: " +(self.file[:-3]+"baselined_dataset.csv"))
#
#         #creating a dataframe for the baseline -> may be used for examples in plots
#         baseline_values = pd.DataFrame({self.time_str:self.dataset_cut[self.time_str],
#                                         self.current_str:self.baseline_filled})
#         print("\nDATA SAVED: "+(self.file[:-3]+"baseline_values.csv"))

