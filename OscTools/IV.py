"""
Author : Divij Gupta
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, AutoMinorLocator
import os
import pandas as pd

class IV:

    def __init__(self, output_path, input_path=None, dataset=None, dataset_errors=None,
                 dataset_collapsed=None, v_tolerance=0.2, title_addition=''):

        if dataset_collapsed:
            self.dataset_collapsed = dataset_collapsed
            self.output_path = output_path

        else:
            if input_path is None:
                if dataset is not None:
                    self.dataset = dataset
                else:
                    print("No input path, dataset or dataset collapsed provided, please provide one")
                    return
            else:
                self.dataset = np.genfromtxt(input_path, delimiter=',', skip_header=1, encoding='utf-8-sig')

            # if dataset_errors is None:
            #     dataset_errors = np.zeros(len(self.dataset))
            # else:
            #     if type(dataset_errors) is float:
            #         dataset_errors = np.ones(len(self.dataset)) * dataset_errors
            #     else:
            #         dataset_errors = np.array(dataset_errors)
            # self.dataset = np.column_stack((self.dataset, dataset_errors))

            if dataset_errors:
                if type(dataset_errors) is float:
                    dataset_errors = np.ones(len(self.dataset)) * dataset_errors
                else:
                    dataset_errors = np.array(dataset_errors)
                self.dataset = np.column_stack((self.dataset, dataset_errors))

            self.filename = input_path.split("/")[-1]
            self.filename = '.'.join(self.filename.split('.')[:-1])
            self.filename += f'_{title_addition}'

            if output_path:
                self.output_path = output_path
            else:
                self.output_path = f'{input_path.split("/")[:-1]}/Output'

        self.v_tolerance = v_tolerance

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

        ax.set_xlabel('Voltage [V]', loc='right', labelpad=10)
        ax.set_ylabel('Current [pA]', loc='top', labelpad=10)

        ax.set_title(title, y=1.01)

        return fig, ax

    @staticmethod
    def _iv_fig_plot_helper(ax, location, iv_type='repeat'):

        if location == 'upper left':
            axins = ax.inset_axes([0.02, 0.76, 0.30, 0.25])
        elif location == 'lower right':
            axins = ax.inset_axes([0.68, 0.02, 0.30, 0.25])
        else:
            print("Enter valid location : 'upper left' or 'lower right'")

        axins.set_xlim(-1.2, 1.2)
        axins.set_ylim(-0.52, 0.58)
        axins.axis('off')

        arrc = 'maroon'
        txtc = '0.15'

        arrow_kw = dict(arrowstyle='-|>', lw=1.2, color=arrc, mutation_scale=10)

        num_kw = dict(ha='center', va='center', fontsize=8, color=arrc,
                      bbox=dict(boxstyle='circle,pad=0.14', fc='white', ec='none'))

        axis_kw = dict(ha='center', va='center', fontsize=9, color=txtc,
                       bbox=dict(boxstyle='round,pad=0.30', fc='white', ec='none'))

        # # --- vertical layout ---
        # y1 = 0.30  # top positive arrow
        # y2 = 0.13  # lower positive arrow
        # yref = -0.05  # voltage reference axis
        # y3 = -0.20  # upper negative arrow
        # y4 = -0.38  # lower negative arrow
        #
        # # number positions
        # yn1 = 0.30
        # yn2 = 0.13
        # yn3 = -0.20
        # yn4 = -0.38
        #
        # # reference voltage axis
        # axins.plot([-1.05, 1.05], [yref + 0.02, yref + 0.02], color='black', lw=0.8, solid_capstyle='round')
        #
        # # optional ticks for structure
        # for x in [-1, 0, 1]:
        #     axins.plot([x, x], [yref, yref], color='black', lw=1.0)
        #
        # # voltage labels centered on the axis
        # axins.text(-1.00, yref, r'$-V$', **axis_kw)
        # axins.text(0.00, yref, r'$0$', **axis_kw)
        # axins.text(1.00, yref, r'$+V$', **axis_kw)
        #
        # # positive sweep above axis
        # axins.annotate('', xy=(1.00, y1), xytext=(0.00, y1), arrowprops=arrow_kw)  # 1
        # axins.text(0.50, yn1, '1', **num_kw)
        #
        # axins.annotate('', xy=(0.00, y2), xytext=(1.00, y2), arrowprops=arrow_kw)  # 2
        # axins.text(0.50, yn2, '2', **num_kw)
        #
        # # negative sweep below axis
        # axins.annotate('', xy=(-1.00, y3), xytext=(0.00, y3), arrowprops=arrow_kw)  # 3
        # axins.text(-0.50, yn3, '3', **num_kw)
        #
        # axins.annotate('', xy=(0.00, y4), xytext=(-1.00, y4), arrowprops=arrow_kw)  # 4
        # axins.text(-0.50, yn4, '4', **num_kw)

        # Voltage axis
        yref = -0.05
        axins.plot([-1.05, 1.05], [yref + 0.02, yref + 0.02],
                   color='black', lw=0.8, solid_capstyle='round')

        for x in [-1, 0, 1]:
            axins.plot([x, x], [yref, yref], color='black', lw=1.0)

        axins.text(-1.00, yref, r'$-V$', **axis_kw)
        axins.text(0.00, yref, r'$0$', **axis_kw)
        axins.text(1.00, yref, r'$+V$', **axis_kw)

        if iv_type == 'repeat':
            y1, y2, y3, y4 = 0.30, 0.13, -0.20, -0.38

            axins.annotate('', xy=(1.00, y1), xytext=(0.00, y1), arrowprops=arrow_kw)
            axins.text(0.50, y1, '1', **num_kw)

            axins.annotate('', xy=(0.00, y2), xytext=(1.00, y2), arrowprops=arrow_kw)
            axins.text(0.50, y2, '2', **num_kw)

            axins.annotate('', xy=(-1.00, y3), xytext=(0.00, y3), arrowprops=arrow_kw)
            axins.text(-0.50, y3, '3', **num_kw)

            axins.annotate('', xy=(0.00, y4), xytext=(-1.00, y4), arrowprops=arrow_kw)
            axins.text(-0.50, y4, '4', **num_kw)

        elif iv_type == 'step':
            y_top = 0.22
            y_bottom = -0.28

            # -V -> +V
            axins.annotate('', xy=(1.00, y_top), xytext=(-1.00, y_top),
                           arrowprops=arrow_kw)
            axins.text(0.00, y_top, '1', **num_kw)

            # +V -> -V
            axins.annotate('', xy=(-1.00, y_bottom), xytext=(1.00, y_bottom),
                           arrowprops=arrow_kw)
            axins.text(0.00, y_bottom, '2', **num_kw)

        else:
            raise ValueError("mode must be '4-step' or '2-step'")

    def _legend_locator(self, x, y, ax, location_trials, logx=False, logy=False, return_overlaps=False):

        # Keep prefered legend first since it will default to that if no of overlap points is identical

        with np.errstate(invalid='ignore'):
            if logx:
                mask_x = np.abs(x) < self.v_tolerance
                x = np.where(x >= 0, np.log10(x), -np.log10(-x))
                x[mask_x] = 0
            if logy:
                y = np.where(y >= 0, np.log10(y), -np.log10(-y))

        # x cuttoff, y cuttoff (in percentage form)
        cutoffs = []
        for location_trial in location_trials:
            if location_trial == 'upper left':
                cutoffs.append([30, 80])
            elif location_trial == 'lower right':
                cutoffs.append([70, 20])
            else:
                print('Invalid legend location, please check')

        y_lims = list(ax.get_ylim())
        x_lims = list(ax.get_xlim())

        with np.errstate(invalid='ignore'):
            for i in range(2):
                if logx:
                    x_lims[i] = np.where(x_lims[i] >= 0, np.log10(x_lims[i]), -np.log10(-x_lims[i]))
                if logy:
                    y_lims[i] = np.where(y_lims[i] >= 0, np.log10(y_lims[i]), -np.log10(-y_lims[i]))

        # Only looking at the current points within the plot window
        mask_x = (x < x_lims[1]) & (x > x_lims[0])
        mask_y = (y < y_lims[1]) & (y > y_lims[0])
        plot_mask = mask_x & mask_y
        y_plot = y[plot_mask]
        x_plot = x[plot_mask]

        overlaps = []
        for x_cutoff, y_cutoff in cutoffs:

            x_cutoff_val = x_cutoff / 100 * (x_lims[1] - x_lims[0]) + x_lims[0]
            if x_cutoff >= 50:
                x_mask = x_plot > x_cutoff_val
            else:
                x_mask = x_plot < x_cutoff_val

            y_cutoff_val = y_cutoff / 100 * (y_lims[1] - y_lims[0]) + y_lims[0]
            if y_cutoff >= 50:
                overlap = np.sum(y_plot[x_mask] > y_cutoff_val)
            else:
                overlap = np.sum(y_plot[x_mask] < y_cutoff_val)

            overlaps.append(overlap)

        if return_overlaps:
            return overlaps
        else:
            return location_trials[np.argmin(overlaps)]

    def plot_raw(self, y_lim=None, show_plot=True, save_plot=False, log=False, title=None):

        if title is None:
            try:
                title = f"{self.filename}"
            except AttributeError:
                title = "IV_raw"
        else:
            title = f"{title}_raw"

        fig, ax = self._plot_helper(title)

        # ax.errorbar(self.dataset[:, 1], self.dataset[:, 0] * 1e12, yerr=self.dataset[:, 2],
        #             c='k', markersize=10, capsize=5, fmt='.', elinewidth=2)
        ax.scatter(self.dataset[:, 1], self.dataset[:, 0] * 1e12, color='k', marker='.')
        ax.set_ylim(y_lim)

        if log:
            ax.set_yscale('symlog')
            ax.yaxis.set_major_formatter(ScalarFormatter())

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

    def collapse_data(self, v_tolerance=None, save_data=False):

        if v_tolerance:
            self.v_tolerance = v_tolerance

        dataset_voltages = self.dataset[:, 1]
        dataset_currents = self.dataset[:, 0]

        dataset_collapsed = np.empty((0, 4))

        ind = 0
        while ind < len(dataset_voltages):

            voltages = [dataset_voltages[ind]]
            currents = [dataset_currents[ind]]
            ind_temp = 1

            try:
                while np.abs(dataset_voltages[ind] - dataset_voltages[ind+ind_temp]) < self.v_tolerance :
                    voltages.append(dataset_voltages[ind+ind_temp])
                    currents.append(dataset_currents[ind+ind_temp])
                    ind_temp += 1
            except IndexError:
                pass

            # For completeness should include possible dataset errors in calculation but doesn't at the moment
            # (deemed to be very subleading and not very important as the error is constant, for now...)

            dataset_collapsed_i = np.array([np.mean(currents), np.std(currents, ddof=1) / len(currents),
                                            np.mean(voltages), np.std(voltages, ddof=1) / len(voltages)])
            dataset_collapsed = np.vstack((dataset_collapsed, dataset_collapsed_i))

            ind += ind_temp

        self.dataset_collapsed = dataset_collapsed

        if save_data:
            df = pd.DataFrame(data=dataset_collapsed, columns=["Current [A]", "Current Err [A]", "Voltage [V]", "Voltage Err [V]"])
            os.makedirs(self.output_path, exist_ok=True)
            df.to_csv(f'{self.output_path}/{self.filename}.csv', index=False)

    def plot_collapsed(self, show_plot=True, save_plot=False, y_lim=None, x_lim=None, logx=False, logy=False,
                       colour='k', label='data', title=None, iv_type='repeat'):

        if title is None:
            try:
                title = f"{self.filename}"
            except AttributeError:
                title = "IV_collapsed"

        if type(self.dataset_collapsed) is not list:
            dataset_collapsed = [self.dataset_collapsed]
            plot_colour = [colour]
            plot_label = [label]
        else:
            dataset_collapsed = self.dataset_collapsed
            plot_colour = colour
            plot_label = label

        fig, ax = self._plot_helper(title)
        iv_fig_loc_overlaps = []
        iv_fig_loc_trials = ['upper left', 'lower right']

        for j, dataset_collapsed_i in enumerate(dataset_collapsed):
            if x_lim:
                x_lim_mask = ((dataset_collapsed_i[:, 0] > (x_lim[0]-self.v_tolerance)) &
                              (dataset_collapsed_i[:, 0] < (x_lim[1]+self.v_tolerance)))
                title = f"{title}_x[{x_lim[0]}-{x_lim[1]}]"
            else:
                x_lim_mask = [True] * len(dataset_collapsed_i[:, 0])
            x_lim_mask = np.array(x_lim_mask)

            try:
                voltage_data = np.ma.array(dataset_collapsed_i[:, 2], mask=~x_lim_mask)
                ax.errorbar(voltage_data,
                            np.ma.array(dataset_collapsed_i[:, 0], mask=~x_lim_mask) * 1e12,
                            yerr=np.ma.array(dataset_collapsed_i[:, 1], mask=~x_lim_mask) * 1e12,
                            linestyle='--', color=plot_colour[j], label=plot_label[j],
                            marker='.', markersize=10, capsize=5)
            except IndexError:
                voltage_data = np.ma.array(dataset_collapsed_i[:, 1], mask=~x_lim_mask)
                ax.scatter(voltage_data,
                           np.ma.array(dataset_collapsed_i[:, 0], mask=~x_lim_mask) * 1e12,
                           linestyle='--', color=plot_colour[j], label=plot_label[j],
                           marker='.')

            iv_fig_loc_overlaps.append(
                self._legend_locator(voltage_data,
                                     np.ma.array(dataset_collapsed_i[:, 0], mask=~x_lim_mask) * 1e12,
                                     ax, logx=logx, logy=logy, location_trials=iv_fig_loc_trials, return_overlaps=True))

        ax.set_ylim(y_lim)

        ax.axvline(x=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)

        iv_fig_loc_overlap = np.sum(iv_fig_loc_overlaps, axis=0)
        iv_fig_loc = iv_fig_loc_trials[np.argmin(iv_fig_loc_overlap)]
        self._iv_fig_plot_helper(ax, iv_fig_loc, iv_type=iv_type)

        if logy:
            ax.set_yscale('symlog')
            ax.yaxis.set_major_formatter(ScalarFormatter())
            title += '_logy'
        if logx:
            ax.set_xscale('symlog')
            ax.xaxis.set_major_formatter(ScalarFormatter())
            title += '_logx'

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

    def main(self, show_plots=True, save_plots=False, save_data=False, iv_type='repeat', title=None, log=False):

        self.plot_raw(show_plot=show_plots, save_plot=save_plots, log=False, title=title)

        if iv_type == 'step':
            self.dataset_collapsed = self.dataset
        elif iv_type == 'repeat':
            self.collapse_data(save_data=save_data)
        else:
            print("Invalid IV type, please choose from : 'step' or 'repeat'")
            return

        if log:
            logy = True
        else:
            logy = False

        self.plot_collapsed(show_plot=show_plots, save_plot=save_plots, logy=logy, title=title, iv_type=iv_type)
        if log:
            self.plot_collapsed(show_plot=show_plots, save_plot=save_plots, logy=True, logx=True, title=title, iv_type=iv_type)
        # self.plot_collapsed(show_plot=show_plots, save_plot=save_plots, x_lim=[-30, 30], log=log)