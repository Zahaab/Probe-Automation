"""
Author : Divij Gupta

Combined class for electrical analysis of devices used in RadTol experiment
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FormatStrFormatter
from matplotlib.ticker import ScalarFormatter
from matplotlib.ticker import AutoMinorLocator

import sys
import os

# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from OscTools.Timeseries import *
from OscTools.IV import *

class DynamicsBase:

    def __init__(self, input_path=None, output_path=None):

        self.input_path = input_path
        self.output_path = output_path

        self.standoff_data = []
        self.standoff_voltages = []
        self.voltage_data = []
        self.voltage_standoffs = []

        self.dark_data = []
        self.dark_types = []

        self.device_name = None

    @staticmethod
    def _plot_helper(title):

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
        # ax.xaxis.set_minor_formatter(formatter)
        # ax.yaxis.set_minor_formatter(formatter)

        # ax.axvline(x=0, color='k', linestyle='-', alpha=0.2)
        # ax.set_xlim([-2, np.max(self.dataset[:, 0])+5])

        ax.set_title(title, y=1.01)

        return fig, ax

    def plot_standoff(self, titles=[], colour='k', label='data', show_plot=True, save_plot=False, show_zero=True):
        """
        Allows multiple if the standoff variation and different voltages want to be plotted
        """

        for ind, standoff_voltage in enumerate(self.standoff_voltages):

            if titles:
                if type(titles) is list:
                    title = titles[ind]
                else:
                    title = titles
            else:
                title = f"{self.device_name}_dynamics_standoff_{standoff_voltage}V"

            standoff_data_i = self.standoff_data[ind]

            plot_colour = colour
            plot_label = label

            fig, ax = self._plot_helper(title)

            ax.set_xlabel('Standoff [mm]', loc='right', labelpad=10)
            ax.set_ylabel(r'$\Delta$I [pA]', loc='top', labelpad=10)

            flag_multi = True
            if type(standoff_data_i) is not list:
                standoff_data_i = [standoff_data_i]
                plot_colour = [colour]
                plot_label = [label]
                flag_multi = False

            for index, standoff_data_i_j in enumerate(standoff_data_i):
                ax.errorbar(standoff_data_i_j[:, 0], standoff_data_i_j[:, 1] * 1e12, yerr=standoff_data_i_j[:, 2] * 1e12,
                            c=plot_colour[index], markersize=10, capsize=5, fmt='.', elinewidth=2, label=plot_label[index])

            ax.set_xlim([0, None])

            if show_zero:
                ax.axhline(y=0, color='k', linestyle='-', alpha=0.2)

            plt.tight_layout()

            if flag_multi:
                plt.legend(loc='upper left', borderpad=0.4, labelspacing=0.6, edgecolor="white",
                           facecolor="white", fancybox=True, handletextpad=0.4)

            if save_plot:
                os.makedirs(self.output_path, exist_ok=True)
                count = 1
                while os.path.isfile(f'{self.output_path}/{title}.pdf'):
                    title += '_1'
                    count += 1
                plt.savefig(f'{self.output_path}/{title}.pdf', dpi=1200)
                print(f"Plot saved to : {self.output_path}/{title}.pdf")
            if show_plot:
                plt.show()
            else:
                plt.close()

    def plot_voltage(self, titles=[], colour='k', label='data', show_plot=True, save_plot=False, log=True):
        """
        Allows multiple if the voltage variation and different standoffs want to be plotted
        """

        for ind, voltage_standoff in enumerate(self.voltage_standoffs):

            if titles:
                if type(titles) is list:
                    title = titles[ind]
                else:
                    title = titles
            else:
                title = f"{self.device_name}_dynamics_voltage_{voltage_standoff}mm"

            voltage_data_i = self.voltage_data[ind]

            plot_colour = colour
            plot_label = label

            fig, ax = self._plot_helper(title)

            ax.set_xlabel('Voltage [V]', loc='right', labelpad=10)
            ax.set_ylabel(r'|$\Delta$I| [pA]', loc='top', labelpad=10)

            flag_multi = True
            if type(voltage_data_i) is not list:
                voltage_data_i = [voltage_data_i]
                plot_colour = [colour]
                plot_label = [label]
                flag_multi = False

            for index, voltage_data_i_j in enumerate(voltage_data_i):
                ax.errorbar(voltage_data_i_j[:, 0], np.abs(voltage_data_i_j[:, 1]) * 1e12, yerr=voltage_data_i_j[:, 2] * 1e12,
                            c=plot_colour[index], markersize=10, capsize=5, fmt='.', elinewidth=2, label=plot_label[index])

            if log:
                ax.set_yscale('log')
                ax.yaxis.set_major_formatter(ScalarFormatter())
                # FormatStrFormatter('%.1d')

            plt.tight_layout()

            if flag_multi:
                plt.legend(loc='lower right', borderpad=0.4, labelspacing=0.6, edgecolor="white",
                           facecolor="white", fancybox=True, handletextpad=0.4)

            if save_plot:
                os.makedirs(self.output_path, exist_ok=True)
                count = 1
                while os.path.isfile(f'{self.output_path}/{title}.pdf'):
                    title += '_1'
                    count += 1
                plt.savefig(f'{self.output_path}/{title}.pdf', dpi=1200)
                print(f"Plot saved to : {self.output_path}/{title}.pdf")
            if show_plot:
                plt.show()
            else:
                plt.close()

    def plot_dark(self, titles=[], colour='k', label='data', show_plot=True, save_plot=False,
                  logx=False, logy=True, show_fit=False):
        """
        Allows multiple if different methods of dark current want to be plotted
        """

        if titles:
            if type(titles) is not list:
                titles = [titles]
            self.dark_types = ['' for _ in range(len(titles))]

        for ind, dark_type in enumerate(self.dark_types):

            if titles:
                title = titles[ind]
            else:
                title = f"{self.device_name}_dynamics_dark_{dark_type}"

            dark_data_i = self.dark_data[ind]

            plot_colour = colour
            plot_label = label

            fig, ax = self._plot_helper(title)

            ax.set_xlabel('Voltage [V]', loc='right', labelpad=10)
            ax.set_ylabel(r'$I_{dark}$ [pA]', loc='top', labelpad=10)

            flag_multi = True
            if type(dark_data_i) is not list:
                dark_data_i = [dark_data_i]
                plot_colour = [colour]
                plot_label = [label]
                flag_multi = False

            legend_handles = []
            legend_loc = "upper right"

            for index, dark_data_i_j in enumerate(dark_data_i):

                # mask = np.where(dark_data_i_j[:, 3] == 0, False, True)
                # dark_data_i_j_omit = dark_data_i_j[~mask]
                # dark_data_i_j = dark_data_i_j[mask]

                markers = np.full(len(dark_data_i_j), 'o', dtype=object)

                if logx and logy and show_fit:
                    dark_currents = [dark_data_i_j[dark_data_i_j[:, 0] < 0], dark_data_i_j[dark_data_i_j[:, 0] >= 0]]
                    for dark_current in dark_currents:
                        voltage_abs = np.abs(dark_current[:, 0])
                        ln_voltage = np.log(voltage_abs)
                        ln_current = np.log(np.abs(dark_current[:, 1]) * 1e12)
                        ln_current_err = dark_current[:, 2] / np.abs(dark_current[:, 1])
                        # ln_current_err = 0.05 * ln_current

                        A = np.vstack((np.ones(len(ln_voltage)), ln_voltage)).T
                        cov_inv = np.diag(1 / ln_current_err**2)

                        param_cov = np.linalg.pinv( np.dot(A.T, np.dot(cov_inv, A)) )
                        params = np.dot( param_cov, np.dot(A.T, np.dot(cov_inv, ln_current)) )

                        # param_cov = np.linalg.inv(np.dot(A.T, A))
                        # params = np.dot(param_cov, np.dot(A.T, ln_current))

                        ln_voltage_plot = np.linspace(np.min(voltage_abs), np.max(voltage_abs), 100)
                        ln_current_plot = np.exp(params[0]) * np.power(ln_voltage_plot, params[1])

                        errs = np.sqrt(np.diag(param_cov))
                        cov = param_cov[0, 1]
                        dy_dc = ln_current_plot
                        dy_dm = ln_current_plot * np.log(ln_voltage_plot)
                        ln_current_plot_err = np.sqrt( dy_dc**2 * errs[0] + dy_dm**2 * errs[1] + 2*dy_dc*dy_dm * cov )

                        # ln_current_plot_err = np.sqrt( np.exp(2*params[0]) * param_errs[0]**2 +
                        #     np.power(np.power(ln_voltage_plot, params[1]) * np.log(ln_voltage_plot), 2) * param_errs[1]**2 )

                        ax.plot(ln_voltage_plot, ln_current_plot, linestyle='--')
                        ax.fill_between(ln_voltage_plot, ln_current_plot - ln_current_plot_err,
                                        ln_current_plot + ln_current_plot_err, alpha=0.3)

                    if index == 0:
                        legend_handles.append(Patch(facecolor=plot_colour[index], edgecolor=plot_colour[index], alpha=0.3,
                                                    label=r'Fit 1$\sigma$'))
                        legend_handles.append(Line2D([0], [0], color=plot_colour[index], linestyle='--',
                                                     label='Fit', markersize=5))

                if logx:
                    markers[dark_data_i_j[:, 0] < 0] = 'd'
                    # markers[dark_data_i_j[:, 0] >= 0] = '#0072B2'
                    dark_data_i_j[:, 0] = np.abs(dark_data_i_j[:, 0])
                    if index == 0:
                        legend_handles.append(Line2D([0], [0], color=plot_colour[index], marker='d', linestyle='None',
                                                      markerfacecolor=plot_colour[index], label='Negative', markersize=5))
                        legend_handles.append(Line2D([0], [0], color=plot_colour[index], marker='o', linestyle='None',
                                                      markerfacecolor=plot_colour[index], label='Positive', markersize=5))
                        legend_handles.reverse()

                flag_errorbar = True
                for x, y, err, marker in zip(dark_data_i_j[:, 0], np.abs(dark_data_i_j[:, 1]) * 1e12,
                                             dark_data_i_j[:, 2] * 1e12, markers):
                    err = ax.errorbar(x, y, err, markersize=5, capsize=5, fmt=marker, c=plot_colour[index], elinewidth=2,
                                      alpha=1, label=plot_label[index])
                    if flag_errorbar:
                        if flag_multi:
                            legend_handles.append(err)
                        flag_errorbar = False

                # if dark_data_i_j_omit.any():
                #     if logx:
                #         dark_data_i_j_omit[:, 0] = np.abs(dark_data_i_j_omit[:, 0])
                #     ax.errorbar(dark_data_i_j_omit[:, 0], np.abs(dark_data_i_j_omit[:, 1]) * 1e12, dark_data_i_j_omit[:, 2] * 1e12,
                #                 markersize=5, capsize=5, fmt='o', c=plot_colour[index], elinewidth=2, alpha=0.2)
                #     if not logx:
                #         if index == 0:
                #             legend_handles.append(Line2D([0], [0], color=plot_colour[index], marker='o',
                #                                           markerfacecolor=plot_colour[index], label='Data', markersize=5, alpha=0.2))
                #     if index == 0:
                #         legend_handles.append(Line2D([0], [0], color=plot_colour[index], marker='o',
                #                                       markerfacecolor=plot_colour[index], label='Omitted', markersize=5, alpha=0.2))

            if logy:
                ax.set_yscale('log')
                ax.yaxis.set_major_formatter(ScalarFormatter())
                ax.set_ylabel(r'|$I_{dark}$| [pA]', loc='top', labelpad=10)
                title += '_logy'
            if logx:
                ax.set_xscale('log')
                ax.xaxis.set_major_formatter(ScalarFormatter())
                ax.set_xlabel('|Voltage| [V]', loc='right', labelpad=10)
                legend_loc = "lower right"
                title += '_logx'

            plt.tight_layout()

            if flag_multi:
                plt.legend(handles=legend_handles, loc=legend_loc, borderpad=0.4, labelspacing=0.6, edgecolor="white",
                           facecolor="white", fancybox=True, handletextpad=0.4, ncol=2, columnspacing=0.9)
            else:
                plt.legend(handles=legend_handles, loc=legend_loc, borderpad=0.4, labelspacing=0.6, edgecolor="white",
                           facecolor="white", fancybox=True, handletextpad=0.4)

            if save_plot:
                os.makedirs(self.output_path, exist_ok=True)
                count = 1
                while os.path.isfile(f'{self.output_path}/{title}.pdf'):
                    title += '_1'
                    count += 1
                plt.savefig(f'{self.output_path}/{title}.pdf', dpi=1200)
                print(f"Plot saved to : {self.output_path}/{title}.pdf")
            if show_plot:
                plt.show()
            else:
                plt.close()


class Dynamics(DynamicsBase):
    """
    General Dynamics class to read in from a config file output by Probe Station Code and do analysis

     config = {
        "output_directory": f'ProbeStation/{DUT}',  # Add data output directory here
        "device_name": PARAMS["DUT"],
        "run_iv": PARAMS["RUN_IV"],
        "run_pv": PARAMS["RUN_PV"],
        "run_td_voltage": PARAMS["RUN_TD_VOLTAGE"],
        "run_td_standoff": PARAMS["RUN_TD_STANDOFF"],
        "iv_range":PARAMS["IV_RANGE"],
        "iv_standoffs": PARAMS["IV_STANDOFFS"],
        "iv_type": PARAMS["IV_TYPE"].lower(),
        "pv_iv_range": PARAMS["PV_IV_RANGE"],
        "pv_iv_standoffs": PARAMS["PV_IV_STANDOFFS"],
        "td_repeats": PARAMS["TD_REPEATS"],
        "td_voltage_standoffs": PARAMS["TD_VOLTAGE_STANDOFFS"],
        "td_voltage_voltages": dynamic_voltages,
        "td_standoff_voltages": PARAMS["TD_STANDOFF_VOLTAGES"],
        "td_standoff_standoffs": PARAMS["TD_STANDOFF_STANDOFFS"],
        "measurement_error" : 10e-15
    }
    """

    def __init__(self, input_path, output_path):

        super().__init__(input_path=input_path, output_path=output_path)
        try:
            with open(f'{self.input_path}/config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"Config file not found. Check or create one following the template (given in the docstring).")
            raise KeyboardInterrupt
        self.device_name = self.config['device_name']

    def parse_data(self, show_plots=False, save_plots=False, save_data=False, manual_override={}, cross_parse=True):
        """
        Manual override example :
            manual_override = {"standoff_timestamps_OFF" :  [[10, 43], [108, 142], [208, 244], [310, 350]],
                               "voltage_timestamps_ON", [[38, 61], [109, 133]],
                               "DG032-1_dynamics_3V_1.5mm_12mm.csv" : {"timestamps_OFF" : [[5, 25], [72, 95], [145, 170]],
                                                                       "timestamps_ON" : [[38, 61], [109, 133]],
                                                                       "baseline_burnin" : 6.5,
                                                                       "baseline_method" : StretchedExponential(),
                                                                       "analysis_methods" : [Exponential(), Constant()],
                                                                       "dark_current" : False,
                                                                       "signal_accept" : [True, False]},
                               "DG032-2_standoffs_[1.5, 3.0, 4.5]mm_11.2V.csv" : {"baseline_burnin" : 10}
                               "DG032-1_dynamics_3V_1.5mm_12mm.csv" : "omit"}
        Uses nested dictionaries for readability in what exactly the user wants to set manually

        cross_parse (bool) : td_voltage and td_standoff can both allow for voltage and standoff variation to be plotted
            depending on how many datapoints are present; up to the user if they would like this or not
        """

        time_delay = self.config['td_time_delay']
        no_repeats = self.config['td_repeats']

        OFF = [[time_delay/4, time_delay-3]]
        ON = []
        count = 1

        for _ in range(no_repeats):
            ON.append([count*time_delay + 3, (count+1)*time_delay - 3])
            count += 1
            OFF.append([count*time_delay + 3, (count+1)*time_delay - 3])
            count += 1

        # Custom timestamps

        default_timestamps_OFF = manual_override.get("timestamps_OFF", OFF)
        default_timestamps_ON = manual_override.get("timestamps_ON", ON)
        default_baseline_burnin = manual_override.get("baseline_burnin", 5)
        default_baseline_method = manual_override.get("baseline_method", StretchedExponential())
        default_analysis_method = manual_override.get("analysis_method", Exponential())
        default_dark_type_accept = manual_override.get("dark_type_accept", 'plat')

        dataset_errors = self.config['measurement_error']
        full_data_summary = []

        if self.config['run_td_voltage']:

            if cross_parse:
                standoff_data_temp = []
            dark_data_temp = []

            for ind_h, standoff in enumerate(self.config['td_voltage_standoffs']):

                data_voltage_voltage = np.empty((0, 3))
                data_voltage_dark = np.empty((0, 3))
                if cross_parse:
                    data_voltage_standoff = np.empty((0, 3))

                for ind_v, voltage in enumerate(self.config['td_voltage_voltages']):

                    file_name = f'dynamic_voltages_{voltage}V_{standoff}mm.csv'
                    file_path = f"{self.input_path}/{file_name}"

                    timestamps_OFF = default_timestamps_OFF
                    timestamps_ON = default_timestamps_ON
                    baseline_burnin = default_baseline_burnin
                    baseline_method = default_baseline_method
                    analysis_method = default_analysis_method
                    signal_accept = [True] * no_repeats
                    dark_type_accept = default_dark_type_accept

                    omit_flag = False

                    if file_name in manual_override:

                        override_attributes = manual_override[file_name]

                        if type(override_attributes) is str:
                            if override_attributes.lower() != "omit":
                                print(f"Invalid entry, file has been omitted for now but please check again: "
                                      f"{file_name} : {override_attributes}")
                            omit_flag = True
                        else:
                            timestamps_OFF = override_attributes.get("timestamps_OFF", timestamps_OFF)
                            timestamps_ON = override_attributes.get("timestamps_ON", timestamps_ON)
                            baseline_burnin = override_attributes.get("baseline_burnin", baseline_burnin)
                            baseline_method = override_attributes.get("baseline_method", baseline_method)
                            analysis_method = override_attributes.get("analysis_method", analysis_method)
                            signal_accept = override_attributes.get("signal_accept", signal_accept)
                            dark_type_accept = override_attributes.get("dark_type_accept", dark_type_accept)

                    try:
                        timeseries_obj = Timeseries(input_path=file_path, output_path=self.output_path,
                                                    dataset_errors=dataset_errors, timestamps_ON=timestamps_ON,
                                                    timestamps_OFF=timestamps_OFF, baseline_burnin=baseline_burnin,
                                                    baseline_method=baseline_method, analysis_methods=analysis_method,
                                                    signal_accept=signal_accept, average_samples=True,
                                                    dark_type_accept=dark_type_accept,)
                    except FileNotFoundError:
                        print(f"File not found (skipped): {file_path}")
                        continue

                    if omit_flag:
                        timeseries_obj.plot_raw(save_plot=save_plots, show_plot=show_plots)
                        print(f"File omitted: {file_path}")
                        continue

                    params = timeseries_obj.main(get_data=True, show_plots=show_plots, save_plots=save_plots)

                    # For compliance params returns as None
                    if params is None:
                        continue

                    params_avg = params.iloc[-1]

                    if save_data:
                        extra_params = pd.DataFrame(data={
                            "Sample ID": [self.device_name],
                            "Run Type": ['td voltage'],
                            "Voltage [V]": [voltage],
                            "Standoff [mm]": [standoff]
                        })
                        full_summary_i = pd.concat(
                            [extra_params.reset_index(drop=True), params.iloc[[-1]].reset_index(drop=True)], axis=1)
                        full_data_summary.append(full_summary_i)

                    deltaI = params_avg["Delta I [A]"]
                    deltaI_err = params_avg["Delta I Err [A]"]

                    if any(signal_accept):
                        data_voltage_voltage = np.vstack((data_voltage_voltage, np.array([voltage, deltaI, deltaI_err])))
                        if cross_parse:
                            data_voltage_standoff = np.vstack((data_voltage_standoff, np.array([standoff, deltaI, deltaI_err])))
                            self.standoff_voltages.append(voltage)

                    if dark_type_accept.lower() == "plat":
                        dark = params_avg["Dark Plat [A]"]
                        dark_err = params_avg["Dark Plat Err [A]"]
                    elif dark_type_accept.lower() == "end":
                        dark = params_avg["Dark End [A]"]
                        dark_err = params_avg["Dark End Err [A]"]
                    else:
                        print("Invalid method for determining dark current, skipped for now. Needs to be : 'plat' or 'end'")
                        continue

                    if dark_type_accept:
                        data_voltage_dark = np.vstack((data_voltage_dark, np.array([voltage, dark, dark_err])))

                self.voltage_standoffs.append(standoff)
                self.voltage_data.append(data_voltage_voltage)
                if cross_parse:
                    standoff_data_temp.append(data_voltage_standoff)

                dark_data_temp.append(data_voltage_dark)

            if cross_parse:
                standoff_data_temp_swapped = []
                max_len = max(len(arr) for arr in standoff_data_temp)
                for i in range(max_len):
                    row = []
                    for arr in standoff_data_temp:
                        if i < len(arr):
                            row.append(np.array(arr[i]))
                    standoff_data_temp_swapped.append(np.array(row))
                self.standoff_data.append(standoff_data_temp_swapped)

            unique_x = np.unique(np.concatenate([arr[:, 0] for arr in dark_data_temp]))
            dark_data_temp_avg = []

            for x in unique_x:
                values = []
                errors = []

                for arr in dark_data_temp:
                    mask = arr[:, 0] == x

                    if np.any(mask):
                        values.append(arr[mask, 1][0])
                        errors.append(arr[mask, 2][0])

                values = np.asarray(values)
                errors = np.asarray(errors)

                weights = 1 / errors ** 2

                y_avg = np.sum(weights * values) / np.sum(weights)
                y_err = 1 / np.sqrt(np.sum(weights))

                dark_data_temp_avg.append(np.array([x, y_avg, y_err]))

            self.dark_data.append(np.array(dark_data_temp_avg))
            self.dark_types.append('avg_cycled')

        if self.config['run_td_standoff']:

            if cross_parse:
                voltage_data_temp = []
                dark_data_temp = np.empty((0, 3))

            for ind_v, voltage in enumerate(self.config['td_standoff_voltages']):

                data_standoff_standoff = np.empty((0, 3))
                if cross_parse:
                    data_standoff_voltage = np.empty((0, 3))
                    data_standoff_dark = np.empty((0, 3))

                for ind_h, standoff in enumerate(self.config['td_standoff_standoffs']):

                    file_name = f'dynamic_standoffs_{voltage}V_{standoff}mm.csv'
                    file_path = f"{self.input_path}/{file_name}"

                    timestamps_OFF = default_timestamps_OFF
                    timestamps_ON = default_timestamps_ON
                    baseline_burnin = default_baseline_burnin
                    baseline_method = default_baseline_method
                    analysis_method = default_analysis_method
                    signal_accept = [True] * no_repeats
                    dark_type_accept = default_dark_type_accept

                    omit_flag = False

                    if file_name in manual_override:

                        override_attributes = manual_override[file_name]

                        if type(override_attributes) is str:
                            if override_attributes.lower() != "omit":
                                print(f"Invalid entry, file has been omitted for now but please check again: "
                                      f"{file_name} : {override_attributes}")
                            omit_flag = True
                        else:
                            timestamps_OFF = override_attributes.get("timestamps_OFF", timestamps_OFF)
                            timestamps_ON = override_attributes.get("timestamps_ON", timestamps_ON)
                            baseline_burnin = override_attributes.get("baseline_burnin", baseline_burnin)
                            baseline_method = override_attributes.get("baseline_method", baseline_method)
                            analysis_method = override_attributes.get("analysis_method", analysis_method)
                            signal_accept = override_attributes.get("signal_accept", signal_accept)
                            dark_type_accept = override_attributes.get("dark_type_accept", dark_type_accept)

                    try:
                        timeseries_obj = Timeseries(input_path=file_path, output_path=self.output_path,
                                                    dataset_errors=dataset_errors, timestamps_ON=timestamps_ON,
                                                    timestamps_OFF=timestamps_OFF, baseline_burnin=baseline_burnin,
                                                    baseline_method=baseline_method, analysis_methods=analysis_method,
                                                    signal_accept=signal_accept, average_samples=True,
                                                    dark_type_accept=dark_type_accept,)
                    except FileNotFoundError:
                        print(f"File not found (skipped): {file_path}")
                        continue

                    if omit_flag:
                        timeseries_obj.plot_raw(save_plot=save_plots, show_plot=show_plots)
                        print(f"File omitted: {file_path}")
                        continue

                    params = timeseries_obj.main(get_data=True, show_plots=show_plots, save_plots=save_plots)

                    # For compliance params returns as None
                    if params is None:
                        continue

                    params_avg = params.iloc[-1]

                    if save_data:
                        extra_params = pd.DataFrame(data={
                            "Sample ID": [self.device_name],
                            "Run Type": ['td standoff'],
                            "Voltage [V]": [voltage],
                            "Standoff [mm]": [standoff]
                        })
                        full_summary_i = pd.concat(
                            [extra_params.reset_index(drop=True), params.iloc[[-1]].reset_index(drop=True)], axis=1)
                        full_data_summary.append(full_summary_i)

                    deltaI = params_avg["Delta I [A]"]
                    deltaI_err = params_avg["Delta I Err [A]"]

                    if any(signal_accept):
                        data_standoff_standoff = np.vstack((data_standoff_standoff, np.array([standoff, deltaI, deltaI_err])))
                        if cross_parse:
                            data_standoff_voltage = np.vstack((data_standoff_voltage, np.array([voltage, deltaI, deltaI_err])))
                            self.voltage_standoffs.append(standoff)

                    if cross_parse:
                        if dark_type_accept.lower() == "plat":
                            dark = params_avg["Dark Plat [A]"]
                            dark_err = params_avg["Dark Plat Err [A]"]
                        elif dark_type_accept.lower() == "end":
                            dark = params_avg["Dark End [A]"]
                            dark_err = params_avg["Dark End Err [A]"]
                        else:
                            print("Invalid method for determining dark current, skipped for now. Needs to be : 'plat' or 'end'")
                            continue

                        if dark_type_accept:
                            data_standoff_dark = np.vstack((data_standoff_dark, np.array([voltage, dark, dark_err])))

                self.standoff_voltages.append(voltage)
                self.standoff_data.append(data_standoff_standoff)
                if cross_parse:
                    voltage_data_temp.append(data_standoff_voltage)

                    weights = 1 / data_standoff_dark[:, 2]**2
                    y_avg = np.sum(weights * data_standoff_dark[:, 1]) / np.sum(weights)
                    y_err = 1 / np.sqrt(np.sum(weights))
                    dark_data_temp = np.vstack((dark_data_temp, np.array([voltage, y_avg, y_err])))

            if cross_parse:
                voltage_data_temp_swapped = []
                max_len = max(len(arr) for arr in voltage_data_temp)
                for i in range(max_len):
                    row = []
                    for arr in voltage_data_temp:
                        if i < len(arr):
                            row.append(np.array(arr[i]))
                    voltage_data_temp_swapped.append(np.array(row))
                self.voltage_data.append(voltage_data_temp_swapped)

                self.dark_data.append(dark_data_temp)
                self.dark_types.append('avg_consecutive')

        # self.standoff_data = np.array(self.standoff_data)
        # self.voltage_data = np.array(self.voltage_data)

        # if len(self.standoff_data.shape) > 3:
        #     self.standoff_data = self.standoff_data.reshape(-1, *self.standoff_data.shape[2:])
        # if len(self.voltage_data.shape) > 3:
        #     self.voltage_data = self.voltage_data.reshape(-1, *self.voltage_data.shape[2:])

        if cross_parse:
            if self.config['run_td_standoff'] & self.config['run_td_voltage']:
                self.standoff_data = list(self.standoff_data[0]) + list([self.standoff_data[1]])
                self.voltage_data = list(self.voltage_data[1]) + list([self.voltage_data[0]])
            else:
                if self.config['run_td_voltage']:
                    self.standoff_data = self.standoff_data[0]
                if self.config['run_td_standoff']:
                    self.voltage_data = self.voltage_data[0]

        if save_data:
            full_data_summary = pd.concat(full_data_summary, ignore_index=True)
            os.makedirs(self.output_path, exist_ok=True)
            full_data_summary.to_csv(f"{self.output_path}/{self.device_name}_dynamics_data.csv", index=False)
            print(f"Data saved to : {self.output_path}/{self.device_name}_dynamics_data.csv")

    def iv(self, show_final_plots=True, save_final_plots=False, show_indiv_plots=False, save_indiv_plots=False,
           save_data=False, log=True):

        iv_range = self.config['iv_range']
        iv_type = self.config['iv_type']

        if len(iv_range) == 2:
            iv_range_type = 'repeat'
            v_tol = (iv_range[0][1] - iv_range[0][0]) / 100
        elif len(iv_range) == 3:
            iv_range_type = 'step'
            v_tol = iv_range[2] / 100
        else:
            print("Invalid iv_range, should be : [[list], no_repeats] or [start, stop, step]")
            raise KeyboardInterrupt

        if save_data:
            save_data_full = []

        if iv_type == 'away' or iv_type == 'rad':
            file_names = []
            standoff_names = []

            if iv_type == 'away':
                file_name = f"IV_away.csv"
                file_names.append(file_name)
                standoff_names.append('N/A')

            elif iv_type == 'rad':
                for iv_standoff in self.config['iv_standoffs']:
                    file_name = f"IV_{iv_standoff}mm_rad.csv"
                    file_names.append(file_name)
                    standoff_names.append(iv_standoff)

            for ind, file_name_i in enumerate(file_names):

                title_base = '.'.join(file_name_i.split('.')[:-1])
                file_path_i = f'{self.input_path}/{file_name_i}'

                iv_obj = IV(input_path=f'{self.input_path}/{file_name_i}', output_path=self.output_path, v_tolerance=v_tol)
                iv_obj.main(show_plots=show_final_plots, save_plots=save_final_plots, save_data=save_data, iv_type=iv_range_type,
                            title=f"{self.device_name}_{title_base}")

                if save_data:
                    df = pd.read_csv(file_path_i)
                    extra_params = pd.DataFrame(data={
                        "Sample ID": [self.device_name] * len(df),
                        "Type": [iv_type] * len(df),
                        "Standoff": [standoff_names[ind]] * len(df),
                        "Spacing": [iv_range_type] * len(df)
                        })
                    full_df = pd.concat([extra_params, df], axis=1)
                    save_data_full.append(full_df)

        elif iv_type == 'both':

            for iv_standoff in self.config['iv_standoffs']:
                data_full = []

                for suffix in ['away', 'rad']:
                    file_name = f"IV_{iv_standoff}mm_{suffix}.csv"
                    file_path = f"{self.input_path}/{file_name}"

                    title_base = '.'.join(file_name.split('.')[:-1])

                    iv_obj_indiv = IV(input_path=file_path, output_path=self.output_path, v_tolerance=v_tol)
                    iv_obj_indiv.main(show_plots=show_indiv_plots, save_plots=save_indiv_plots, save_data=save_data,
                                      iv_type=iv_range_type, title=f"{self.device_name}_{title_base}", log=log)

                    data_full.append(iv_obj_indiv.dataset_collapsed)

                    if save_data:
                        df = pd.read_csv(file_path)
                        extra_params = pd.DataFrame(data={
                            "Sample ID": [self.device_name] * len(df),
                            "Type": [f'{iv_type}-{suffix}'] * len(df),
                            "Standoff": [iv_standoff] * len(df),
                            "Spacing": [iv_range_type] * len(df)
                        })
                        full_df = pd.concat([extra_params, df], axis=1)
                        save_data_full.append(full_df)

                if log:
                    logy = True
                else:
                    logy = False

                iv_obj = IV(output_path=self.output_path, dataset_collapsed=data_full)
                iv_obj.plot_collapsed(show_plot=show_final_plots, save_plot=save_final_plots, colour=['k', 'red'], logy=logy,
                                      label=['Clear', 'Rad'], title=f"{self.device_name}_IV_{iv_standoff}mm_both", iv_type=iv_range_type)
                if log:
                    iv_obj.plot_collapsed(show_plot=show_final_plots, save_plot=save_final_plots, colour=['k', 'red'], logy=True, logx=True,
                                          label=['Clear', 'Rad'], title=f"{self.device_name}_IV_{iv_standoff}mm_both", iv_type=iv_range_type)

        else:
            print("Invalid iv_type, should be : 'away', 'rad' or 'both'")

        if save_data:
            data_combined = pd.concat(save_data_full, ignore_index=True)
            os.makedirs(self.output_path, exist_ok=True)
            data_combined.to_csv(f"{self.output_path}/{self.device_name}_IV_{iv_type}.csv", index=False)
            print(f"Data saved to : {self.output_path}/{self.device_name}_IV_{iv_type}.csv")

    def pv_iv(self, show_plots=True, save_plots=False, save_data=False, log=True):

        pv_iv_range = self.config['pv_iv_range']
        v_tol = pv_iv_range[2] / 100

        if save_data:
            save_data_full = []

        for pv_iv_standoff in self.config['pv_iv_standoffs']:

            file_name = f"PV_IV_{pv_iv_standoff}mm_rad.csv"
            title_base = '.'.join(file_name.split('.')[:-1])
            file_path = f'{self.input_path}/{file_name}'

            iv_obj = IV(input_path=file_path, output_path=self.output_path, v_tolerance=v_tol)
            iv_obj.main(show_plots=show_plots, save_plots=save_plots, save_data=save_data, iv_type='step',
                        title=f"{self.device_name}_{title_base}", log=log)

            if save_data:
                df = pd.read_csv(file_path)
                extra_params = pd.DataFrame(data={
                    "Sample ID": [self.device_name] * len(df),
                    "Standoff": [pv_iv_standoff] * len(df),
                })
                full_df = pd.concat([extra_params, df], axis=1)
                save_data_full.append(full_df)

        if save_data:
            data_combined = pd.concat(save_data_full, ignore_index=True)
            os.makedirs(self.output_path, exist_ok=True)
            data_combined.to_csv(f"{self.output_path}/{self.device_name}_PV_IV.csv", index=False)
            print(f"Data saved to : {self.output_path}/{self.device_name}_PV_IV.csv")

    def main(self, show_final_plots=True, save_final_plots=False, show_indiv_plots=False, save_indiv_plots=False,
             save_data=False, manual_override={}, cross_parse=False, log_iv=True, log_pv=False):

        self.parse_data(show_plots=show_indiv_plots, save_plots=save_indiv_plots,
                        save_data=save_data, manual_override=manual_override, cross_parse=cross_parse)
        self.plot_standoff(show_plot=show_final_plots, save_plot=save_final_plots)
        self.plot_voltage(show_plot=show_final_plots, save_plot=save_final_plots)
        self.plot_dark(show_plot=show_final_plots, save_plot=save_final_plots, logy=True)
        self.plot_dark(show_plot=show_final_plots, save_plot=save_final_plots, logx=True, logy=True)
        if self.config['run_iv']:
            self.iv(show_final_plots=show_final_plots, save_final_plots=save_final_plots,
                    show_indiv_plots=show_indiv_plots, save_indiv_plots=save_indiv_plots, save_data=save_data, log=log_iv)
        if self.config['run_pv']:
            self.pv_iv(show_plots=show_final_plots, save_plots=save_final_plots, save_data=save_data, log=log_pv)


