"""
Evaluation results display window module.

This module provides the GUI window for displaying detailed flight evaluation
results organized by flight phase and performance tier. It includes interactive
features like hover-triggered histograms showing metric distributions and
score calculation functionality.
"""

import os
import json
import sys
import hashlib
import customtkinter
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from CTkTable import CTkTable
from tkinter import messagebox, simpledialog

import globals
from grading import tier_data, calculate_phase_weights
from gui.CTKcustom import PhasesTabView


class EvaluationWindow(customtkinter.CTkToplevel):
    """
    Window for displaying comprehensive flight evaluation results.

    This top-level window organizes evaluation metrics by flight phase (Alignment,
    Approach, Final Approach, Total Flight) and performance tier (Excellent, Good,
    Normal, Poor, Very Poor, Not Tierable). It provides interactive features including
    hover-triggered probability density functions and score calculation.

    :param master: The parent window.
    :type master: tkinter.Widget
    :param evaluated_results: Dictionary containing all evaluated flight metrics.
    :type evaluated_results: dict
    :param args: Additional positional arguments passed to CTkToplevel.
    :type args: tuple
    :param kwargs: Additional keyword arguments passed to CTkToplevel.
    :type kwargs: dict

    :ivar hist_window: Reference to the currently displayed histogram window, if any.
    :vartype hist_window: HistWindow or None
    :ivar metrics: Nested dictionary of metric data organized by phase and metric name.
    :vartype metrics: dict
    :ivar dataobjs: Nested dictionary of data objects for each metric by phase.
    :vartype dataobjs: dict
    :ivar sub_score_label: Label displaying individual phase sub-scores.
    :vartype sub_score_label: customtkinter.CTkLabel
    :ivar total_score_label: Label displaying the final calculated score.
    :vartype total_score_label: customtkinter.CTkLabel
    :ivar calculate_score_button: Button to trigger score calculation (hidden by default).
    :vartype calculate_score_button: customtkinter.CTkButton

    .. note::
       The score calculation button is hidden by default and can be revealed
       using the Shift+G keyboard shortcut or by unlocking with a password.
    """

    def __init__(self, master, evaluated_results, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("Evaluation of Flight Data")

        self.iconbitmap(default=globals.icon_path)

        self.hist_window = None

        self._hist_show_job = None
        self._hist_close_job = None

        self.metrics = {}

        # Add meta data labels as separate elements
        pilot_label = customtkinter.CTkLabel(
            master=self,
            text=f"Pilot ID: {self.master.results['Pilot'][0]}; Scenario: {self.master.results['Scenario'][0]}",
            fg_color="#8A2BE2",  # Add purple background
            text_color="white",
            corner_radius=8,
            anchor="w",
            padx=5,
            pady=5,
        )
        pilot_label.pack(anchor="center", padx=15, pady=15)

        phases_tabview = PhasesTabView(master=self)
        phases_tabview.pack(fill="both", expand=True, padx=15, pady=15)

        total_tiered_data = {}
        total_metric_database = {}

        for tab in phases_tabview.tabs:
            total_tiered_data[tab], self.metrics[tab], total_metric_database[tab] = tier_data(evaluated_results, tab)

            for evaluation_tier in phases_tabview.evaluation_tiers:
                if not total_tiered_data[tab][evaluation_tier]:
                    panel = phases_tabview.panels[tab][evaluation_tier]
                    panel.header_button.configure(text=f"{panel.title} (0)")
                    continue

                panel = phases_tabview.panels[tab][evaluation_tier]
                panel.header_button.configure(text=f"{panel.title} ({len(total_tiered_data[tab][evaluation_tier])})")

                if tab != "Total Flight":
                    # column_keys = ["Value", "Mean", "Std", "Type", "Weight", "Percentile"]
                    column_keys = ["Value", "Unit", "Description"]  # productive table version
                else:
                    # column_keys = ["Value", "Mean", "Std", "Type", "Percentile"]
                    column_keys = ["Value", "Unit", "Description"]  # productive table version

                mapping_file = r"src\flight_data_evaluation_tool\results_template.json"

                if getattr(sys, "frozen", False):  # Check if running in a PyInstaller bundle
                    mapping_file = sys._MEIPASS  # type: ignore
                    mapping_file = os.path.join(mapping_file, "results_template.json")
                with open(mapping_file, "r", encoding="utf-8") as f:
                    parameter_mapping = json.load(f)
                    parameter_mapping = parameter_mapping["columns"]
                    parameter_mapping = {key: value for key, value in parameter_mapping.items() if value}

                values = [["Name"] + column_keys]
                for item in total_tiered_data[tab][evaluation_tier]:
                    key = list(item.keys())[0]

                    try:
                        parameter_mapping[key]
                    except KeyError:
                        parameter_mapping[key] = {}

                    single_row_values = []
                    for col in column_keys:
                        if col == "Description" or col == "Unit":
                            if col in parameter_mapping[key]:
                                single_row_values.append(parameter_mapping[key][col])
                            else:
                                single_row_values.append("")

                            continue

                        if isinstance(item[key][col], float):
                            single_row_values.append(round(item[key][col], 4))
                        else:
                            single_row_values.append(item[key][col])

                    values.append([key] + single_row_values)

                table = CTkTable(
                    panel._content_frame,
                    row=len(values),
                    column=len(values[0]),
                    values=values,
                    corner_radius=0,
                    width=0,
                    header_color=panel.header_button.cget("fg_color"),
                )
                table.pack(expand=True, fill="both", padx=10, pady=2)

                # Add hover event for each row except header
                for row_idx in range(1, len(values)):
                    row_key = values[row_idx][0]

                    if "alt_name" in parameter_mapping[row_key]:
                        table.insert(row_idx, 0, parameter_mapping[row_key]["alt_name"])

                    widget_row = [table.frame[(row_idx, col_idx)] for col_idx in range(len(values[0]))]
                    # Bind <Enter> and <Leave> to all widgets in the row
                    for cell_widget in widget_row:
                        cell_widget.bind("<Enter>", lambda e, metric=row_key, tab=tab: self._on_row_hover(metric, tab))
                        cell_widget.bind(
                            "<Leave>",
                            lambda e, row_idx=row_idx, table=table: self._on_row_leave_row(row_idx, table),
                        )

        temp_tired_data = total_tiered_data
        self.dataobjs = {}

        for tab in phases_tabview.tabs:
            self.dataobjs[tab] = {}
            for tier in temp_tired_data[tab]:
                for item in temp_tired_data[tab][tier]:
                    self.dataobjs[tab].update(item)

        self.sub_score_label = customtkinter.CTkLabel(
            master=self,
            text="",
            fg_color="transparent",
        )
        self.sub_score_label.pack(side="left", pady=15, padx=(15, 10))

        self.total_score_label = customtkinter.CTkLabel(
            master=self,
            text="",
            fg_color="transparent",
        )
        self.total_score_label.pack(side="left", pady=15, padx=(15, 10))

        # Only show grading button with secret keyboard shortcut
        self.bind_all("<Shift-G>", self.show_grading_button)  # Ctrl+Shift+G

        self.calculate_score_button = customtkinter.CTkButton(
            master=self,
            text="Calculate Flight Score",
            command=lambda: self.calculate_score(total_tiered_data, total_metric_database),
        )
        if globals.grading_unlocked:
            self.calculate_score_button.pack(side="right", pady=15, padx=(15, 10))

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)

        # Because CTkToplevel currently is bugged on windows and doesn't check if a user specified icon is set we need
        # to set the icon again after 200ms
        if sys.platform.startswith("win"):
            self.after(200, lambda: self.iconbitmap(globals.icon_path))

    def show_grading_button(self, event=None):
        """
        Show the score calculation button (keyboard shortcut handler).

        This method is bound to the Shift+G keyboard shortcut and reveals the
        score calculation button if it's not already visible.

        :param event: The keyboard event that triggered this method, defaults to None.
        :type event: tkinter.Event, optional
        """
        if globals.grading_unlocked:
            return

        if self.calculate_score_button.winfo_ismapped():
            return

        self.calculate_score_button.pack(side="right", pady=15, padx=(15, 10))

    def calculate_score(self, total_tiered_data, total_metric_database):
        """
        Calculate the final score based on the sub-scores and update the label.
        """

        if not globals.grading_unlocked:
            entered_password = simpledialog.askstring("Password", "Enter password:", show="*")

            if not entered_password:
                return

            entered_password = hashlib.sha256(str.encode(entered_password)).hexdigest()

            if entered_password != globals.password:
                messagebox.showerror("Error", "Incorrect password!")
                return
            else:
                globals.grading_unlocked = True

        final_score = 0
        sub_scores = {"Alignment Phase": 0, "Approach Phase": 0, "Final Approach Phase": 0}
        phase_relevance_factors = {"Alignment Phase": 0.2, "Approach Phase": 0.3, "Final Approach Phase": 0.5}
        tier_factors = {
            "Excellent": 1,
            "Good": 2,
            "Normal": 3,
            "Poor": 4,
            "Very Poor": 5,
        }

        for phase in sub_scores:
            # calculate the weights of the evaluation metrics for this phase
            weights = calculate_phase_weights(total_metric_database[phase])

            for evaluation_tier in tier_factors:
                for item in total_tiered_data[phase][evaluation_tier]:
                    item = list(item.keys())[0]
                    sub_scores[phase] += weights[item] * tier_factors[evaluation_tier]

        sub_scores = {phase: round(sub_score, 2) for phase, sub_score in sub_scores.items()}

        for phase, sub_score in sub_scores.items():
            final_score += sub_score * phase_relevance_factors[phase]

        # Format sub scores in a user-friendly way
        sub_score_text = "Phase Sub Scores: "
        score_parts = []
        for phase, score in sub_scores.items():
            score_parts.append(f"{phase}: {score}")

        sub_score_text += " | ".join(score_parts)

        # Update the labels with the sub and final scores
        self.sub_score_label.configure(text=sub_score_text)
        self.total_score_label.configure(text=f"Total Flight Score: {round(final_score, 2)}")

    def close_hist_window(self, event=None):
        """
        Close the currently displayed histogram window if it exists.

        :param event: Optional event parameter, defaults to None.
        :type event: tkinter.Event, optional
        """
        if self.hist_window is not None and self.hist_window.winfo_exists():
            self.hist_window.destroy()
            self.hist_window = None

    def show_hist_window(self, metric, tab):
        """
        Display a histogram window showing the metric's distribution.

        Creates and displays a new HistWindow showing the probability density
        function for the specified metric, with tier boundaries and the current
        flight's value marked.

        :param metric: Name of the metric to display.
        :type metric: str
        :param tab: Name of the flight phase tab (e.g., 'Alignment Phase').
        :type tab: str

        .. note::
           Any existing histogram window is automatically closed before creating
           a new one.
        """
        # Close any existing window
        self.close_hist_window()
        self._hist_close_job = None

        data = self.metrics[tab][metric]

        borders = self.dataobjs[tab][metric]["Borders"]
        self.hist_window = HistWindow(
            master=self,
            data=data,
            metric=metric,
            tab=tab,
            borders=borders,
            on_close_callback=lambda: setattr(self, "hist_window", None),
        )

    def _on_hist_enter(self, event):
        # Cancel any scheduled close when mouse enters the histogram window
        if self._hist_close_job is not None:
            self.after_cancel(self._hist_close_job)
            self._hist_close_job = None

    def _on_hist_leave(self, event):
        # Schedule closing the histogram window after a short delay
        CLOSE_CHECK_DELAY_MS = 100
        if self._hist_close_job is not None:
            self.after_cancel(self._hist_close_job)
        self._hist_close_job = self.after(CLOSE_CHECK_DELAY_MS, self.close_hist_window)

    def _on_row_hover(self, metric, tab):
        """
        Handle mouse hover over a table row.
        Schedule showing histogram after a delay.
        """
        # Constants for timing
        HISTOGRAM_DISPLAY_DELAY_MS = 2000

        # Cancel any scheduled close
        if self._hist_close_job is not None:
            self.after_cancel(self._hist_close_job)
            self._hist_close_job = None

        # Cancel any previous scheduled show
        if self._hist_show_job is not None:
            self.after_cancel(self._hist_show_job)

        # Schedule the new show action after delay
        self._hist_show_job = self.after(HISTOGRAM_DISPLAY_DELAY_MS, lambda: self.show_hist_window(metric, tab))

    def _on_row_leave_row(self, row_idx, table):
        """
        Handle mouse leaving a table row.
        Close histogram window after delay if mouse isn't over row or histogram.
        """
        CLOSE_CHECK_DELAY_MS = 100

        # Cancel any scheduled show
        if self._hist_show_job is not None:
            self.after_cancel(self._hist_show_job)
            self._hist_show_job = None

        def is_mouse_over_row_or_hist():
            """Check if mouse is still over the row or histogram window"""
            x, y = self.winfo_pointerxy()
            widget = self.winfo_containing(x, y)

            # Check if mouse is over any cell in this row
            for col_idx in range(table.columns):
                if widget == table.frame[(row_idx, col_idx)]:
                    return True

            # Check if mouse is over the histogram window
            if self.hist_window is not None and self.hist_window.winfo_exists():
                if widget is not None:
                    parent = widget
                    while parent is not None:
                        if parent == self.hist_window:
                            return True
                        parent = parent.master
            return False

        def check_and_close_if_needed():
            """Close histogram if mouse is not over row or histogram"""
            if not is_mouse_over_row_or_hist():
                self.close_hist_window()

        # Cancel any previous close check
        if self._hist_close_job is not None:
            self.after_cancel(self._hist_close_job)

        # Schedule new close check
        self._hist_close_job = self.after(CLOSE_CHECK_DELAY_MS, check_and_close_if_needed)


class HistWindow(customtkinter.CTkToplevel):
    """
    Popup window displaying a metric's probability density function (PDF).

    This window shows the distribution of a flight metric across all historical
    flights, with tier boundaries marked and the current flight's value highlighted.
    The PDF is color-coded by performance tier for easy visual interpretation.

    :param master: The parent EvaluationWindow.
    :type master: EvaluationWindow
    :param data: Historical data for the metric across all flights.
    :type data: array-like
    :param metric: Name of the metric being displayed.
    :type metric: str
    :param tab: Name of the flight phase.
    :type tab: str
    :param borders: List of four tier boundary values.
    :type borders: list of float
    :param on_close_callback: Optional callback function when window closes, defaults to None.
    :type on_close_callback: callable, optional

    .. note::
       The window automatically positions itself near the mouse cursor with a small
       offset to avoid blocking the cursor. It includes color-coded regions for each
       performance tier (Excellent, Good, Normal, Poor, Very Poor).
    """

    def __init__(self, master, data, metric, tab, borders, on_close_callback=None):
        super().__init__(master)
        self.master = master
        self.on_close_callback = on_close_callback

        self.title(f"Distribution for {metric}")
        self.iconbitmap(default=globals.icon_path)

        # Because CTkToplevel currently is bugged on windows and doesn't check if a user specified icon is set we need
        # to set the icon again after 200ms
        if sys.platform.startswith("win"):
            self.after(200, lambda: self.iconbitmap(globals.icon_path))

        # Offset to avoid mouse being over the title bar
        OFFSET_X = 10
        OFFSET_Y = 20
        mouse_x = master.winfo_pointerx()
        mouse_y = master.winfo_pointery()
        self.geometry(f"400x300+{mouse_x + OFFSET_X}+{mouse_y + OFFSET_Y}")

        # Bring the window to the front and focus it
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)

        fig, ax = plt.subplots(figsize=(4, 3), dpi=100)

        # Plot histogram
        # ax.hist(data, bins=20, color="#8A2BE2", edgecolor="black", density=True, alpha=0.6, label="Histogram")

        # Draw vertical lines for each border
        for border in borders:
            ax.axvline(border, color="black", linestyle="--", lw=1)

        # Add a vertical line for the current value
        if "trans_Value" in self.master.dataobjs[tab][metric]:
            current_value = self.master.dataobjs[tab][metric]["trans_Value"]
            transformed_label = " (Transformed)"
        else:
            current_value = self.master.dataobjs[tab][metric]["Value"]
            transformed_label = ""
        ax.axvline(current_value, color="#8A2BE2", linestyle="-", lw=2, label=f"Value{transformed_label}")

        # Plot PDF
        if len(data) > 1 and len(set(data)) > 1:  # Check for variance in data
            kde = gaussian_kde(data)
            if not borders or min(data) < borders[0]:
                x_min = min(data)
            else:
                x_min = borders[0]
            if max(data) < current_value:
                x_max = current_value
            else:
                x_max = max(data)
            x_vals = np.linspace(x_min, x_max, 200)
            ax.plot(x_vals, kde(x_vals), color="black", lw=1, label=f"PDF{transformed_label}")

            # Define tier colors, altered for white background
            tier_colors = {
                "Excellent": "#015220",
                "Good": "#1AA260",
                "Normal": "#f38200",
                "Poor": "#E55451",
                "Very Poor": "#C40717",
            }

            # Color the area under the curve between borders
            # Sort borders and add min and max x values to ensure full coverage
            all_borders = [x_min] + borders + [x_max]

            # Get tier colors in a list for easier indexing
            colors = list(tier_colors.values())

            # Fill each section between borders with the appropriate tier color
            for i in range(len(all_borders) - 1):
                section_min = all_borders[i]
                section_max = all_borders[i + 1]
                section_x = np.linspace(section_min, section_max, 100)
                section_y = kde(section_x)
                ax.fill_between(section_x, section_y, alpha=0.3, color=colors[i])

        fig.suptitle("Probability Density Function(PDF) with tiers")
        ax.set_xlabel(f"Flight Metric Value{transformed_label}")
        ax.set_ylabel("Density")
        ax.legend()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        # Bind enter/leave events to the histogram window
        self.bind("<Enter>", self._on_hist_enter)
        self.bind("<Leave>", self._on_hist_leave)

        # Destroy the figure after embedding to avoid memory leaks
        plt.close(fig)

    def _on_hist_enter(self, event):
        if hasattr(self.master, "_on_hist_enter"):
            self.master._on_hist_enter(event)

    def _on_hist_leave(self, event):
        if hasattr(self.master, "_on_hist_leave"):
            self.master._on_hist_leave(event)

    def destroy(self):
        if self.on_close_callback:
            self.on_close_callback()
        super().destroy()
