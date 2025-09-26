import os
import sys
import customtkinter
import matplotlib.style
from functools import partial
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk

# if getattr(sys, "frozen", False):
#     bundle_dir = sys._MEIPASS
#     sys.path.insert(0, bundle_dir)

try:
    import globals
except ImportError:
    from .. import globals

import globals
from plot import create_figure
from evaluation import evaluate_flight_phases, calculate_phase_evaluation_values
from gui.evaluation_window import EvaluationWindow
from gui.heatmap_window import HeatMapWindow


class PlotWindow(customtkinter.CTkToplevel):
    """
    A window for displaying plots of flight data.

    Parameters
    ----------
    master : tkinter.Widget
        The parent widget.
    phases : list
        The flight phases for which plots will be created.
    *args : tuple
        Additional positional arguments.
    **kwargs : dict
        Additional keyword arguments.
    """

    def __init__(self, master, phases, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.evaluation_window = None
        self.heatmap_window = None

        self.master = master
        self.phases = {}
        for counter, phase in enumerate(
            ["Alignment Start (s):", "Approach Start (s):", "Final Approach Start (s):", "Docking Time (s):"]
        ):
            self.phases[phase] = phases[counter]

        self.title("Flight Plots")

        self.iconbitmap(default=globals.icon_path)

        x_axis_type = self.master.option_menu.get()
        x_axis_type = {"Simulation time": "SimTime", "Axial distance Vessel-Station": "COG Pos.x [m]"}[x_axis_type]

        try:
            total_flight_errors = calculate_phase_evaluation_values(
                self.master.data_frame, "Total", 0, 3, list(self.phases.values()), self.master.results
            )
            _failed_error_calculation_ = False
        except ValueError:
            total_flight_errors = {"THC.x": [], "THC.y": [], "THC.z": [], "RHC.x": [], "RHC.y": [], "RHC.z": []}
            _failed_error_calculation_ = True

        self.figure, self.axvlines = create_figure(
            self.master.data_frame, list(self.phases.values()), total_flight_errors, x_axis_type
        )

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)

        toolbar = NavigationToolbar2Tk(self.canvas, self)
        toolbar.update()
        toolbar.grid(row=1, column=0, columnspan=4, sticky="ew")

        self.canvas.get_tk_widget().grid(row=2, column=0, columnspan=4, sticky="nsew")
        self.canvas.draw()

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
        pilot_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        # Add phase number fields
        self.entries = {}
        for counter, phase in enumerate(
            ["Alignment Start (s):", "Approach Start (s):", "Final Approach Start (s):", "Docking Time (s):"]
        ):
            entry = customtkinter.CTkLabel(
                master=self, text=f"{phase} {self.phases[phase]}", fg_color="transparent", anchor="w"
            )
            self.entries[phase] = entry
            entry.grid(row=3, column=counter, sticky="sew")

        # Add sliders for Flight Phase
        if x_axis_type == "SimTime":
            self.sliders = {}
            for counter, phase in enumerate(
                ["Alignment Start (s):", "Approach Start (s):", "Final Approach Start (s):", "Docking Time (s):"]
            ):
                slider = customtkinter.CTkSlider(
                    master=self,
                    from_=0,
                    to=self.master.data_frame.iloc[-1]["SimTime"],
                    command=partial(self.update_phase_lines, phase),
                )
                self.sliders[phase] = slider
                slider.set(self.phases[phase])
                slider.grid(row=4, column=counter, sticky="sew")
                slider._canvas.bind("<Button-1>", self.on_focus)
                # Bind arrow keys for keyboard control
                slider._canvas.bind("<Left>", partial(self.keyboard_slider_control, slider, phase, "left"))
                slider._canvas.bind("<Right>", partial(self.keyboard_slider_control, slider, phase, "right"))

        # Add various buttons
        evaluation_button = customtkinter.CTkButton(
            master=self, text="Evaluate Flight Phases", command=self.evaluate_button_event
        )
        evaluation_button.grid(row=5, column=2, sticky="s", padx=15, pady=15)

        if x_axis_type == "SimTime":
            if not getattr(sys, "frozen", False):
                add_to_database_button = customtkinter.CTkButton(
                    master=self, text="Add flight to database", command=self.add_to_database_button_event
                )
                add_to_database_button.grid(row=0, column=3, sticky="s", padx=5, pady=5)
        else:
            self.switch_var = customtkinter.StringVar(value="on")
            phases_switch = customtkinter.CTkSwitch(
                master=self,
                text="Phase lines",
                command=self.toggle_phases,
                variable=self.switch_var,
                onvalue="on",
                offvalue="off",
            )
            phases_switch.grid(row=0, column=3, padx=5, pady=5, sticky="s")

        print_button = customtkinter.CTkButton(
            master=self, text="Save Plots individually", command=self.print_button_event
        )
        print_button.grid(row=5, column=1, padx=15, pady=15, sticky="s")

        # Button for Heatmap Calculation
        heatmap_button = customtkinter.CTkButton(
            master=self, text="Show Heatmaps for Flight Phases", command=self.heatmap_button_event
        )
        heatmap_button.grid(row=5, column=0, padx=15, pady=15, sticky="s")

        # create execution info box
        self.execution_info = customtkinter.CTkLabel(
            master=self, text="", fg_color="transparent", corner_radius=15, wraplength=350
        )
        self.execution_info.grid(row=5, column=3)
        if _failed_error_calculation_:
            self.execution_info.configure(
                text="Flight Errors could not be determined. Check if scenario is a docking scenario!",
                fg_color="#ED2939",
            )

        self.state("zoomed")

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)

        # Make the canvas and toolbar resize with the window
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Because CTkToplevel currently is bugged on windows and doesn't check if a user specified icon is set we need
        # to set the icon again after 200ms
        if sys.platform.startswith("win"):
            self.after(200, lambda: self.iconbitmap(globals.icon_path))

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        if self.evaluation_window is not None and self.evaluation_window.winfo_exists():
            self.evaluation_window.destroy()
        if self.heatmap_window is not None and self.heatmap_window.winfo_exists():
            self.heatmap_window.destroy()
        plt.close(self.figure)
        self.destroy()

    def on_focus(self, event):
        """
        Handles the focus event for a widget.

        This method is called when a widget gains focus. It sets the focus to the
        widget that triggered the event.

        Args:
            event (tkinter.Event): The event object containing information about
            the focus event.
        """
        event.widget.focus_set()

    def update_phase_lines(self, slider_id, value):
        """
        Updates the vertical line for the specified phase.

        Parameters
        ----------
        phase : str
            The phase to be updated.
        value : float
            The new value for the phase.
        """
        matplotlib.style.use("fast")

        self.master.results["Manually modified Phases"] = "Yes"

        nearest_value = min(self.master.data_frame["SimTime"], key=lambda x: abs(x - value))
        self.sliders[slider_id].set(nearest_value)
        self.phases[slider_id] = nearest_value

        self.master.preconfigured_phases[self.master.session_identifier] = list(self.phases.values())

        self.entries[slider_id].configure(text=f"{slider_id} {nearest_value}")
        for ax in self.axvlines:
            self.axvlines[ax][list(self.phases.values()).index(nearest_value)].set_xdata([self.phases[slider_id]])

        self.canvas.draw()

    def keyboard_slider_control(self, slider, phase, direction, event):
        # Get the current slider in focus
        if slider.focus_get() == slider._canvas:
            current_value = slider.get()
            current_index = list(self.master.data_frame["SimTime"]).index(current_value)
            if direction == "right":
                new_index = current_index + 1
            elif direction == "left":
                new_index = current_index - 1

            self.update_phase_lines(phase, self.master.data_frame["SimTime"].iloc[new_index])

    def add_to_database_button_event(self):
        """
        Handles the event triggered by the evaluate button.
        This method performs the following steps:
        1. Clears the execution info display.
        2. Checks if the phase timestamps are in ascending order.
           - If not, shows an error message and exits the method.
        3. Prompts the user to select a directory to save the evaluation results.
           - If no directory is selected, exits the method.
        4. Constructs the file path for the evaluation results.
           - If the file already exists, prompts the user to decide whether to overwrite or append to the file.
        5. Calls the `evaluate_flight_phases` function to perform the evaluation.
        6. Updates the execution info display with the result of the evaluation.
        Raises:
            ValueError: If the phase timestamps are not in ascending order.
        Returns:
            None
        """

        self.execution_info.configure(text="", fg_color="transparent")

        try:
            self.master.data_frame[self.master.data_frame["Port Pos.x [m]"] == 0].iloc[0]["SimTime"]
        except IndexError:
            messagebox.showerror(
                "Flight Database Error",
                "You are only allowed to add successfull docking attempts to the database.",
            )
            self.execution_info.configure(text="Flight Database Error", fg_color="#ED2939")
            # lift TopLevelWindow in front
            self.lift()
            self.focus_force()
            self.after(10, self.focus_force)
            return

        sorted = True
        for counter, _ in enumerate(list(self.phases.values())[0:-1]):
            if list(self.phases.values())[counter] > list(self.phases.values())[counter + 1]:
                sorted = False

        if not sorted:
            messagebox.showerror(
                "Phase Timestamps Error",
                f"Phase Timestamp have to be in ascending order (from smallest to largest) but are actually not: {self.phases}.\n"
                "Make sure that the order of the phases is: Alignment Start <= Approach Start <= Final Approach Start <= Docking Time",
            )
            self.execution_info.configure(text="Phase Timestamps Error", fg_color="#ED2939")
            # lift TopLevelWindow in front
            self.lift()
            self.focus_force()
            self.after(10, self.focus_force)
            return

        if not os.path.exists(f"data/{self.master.results['Scenario'][0]}"):
            os.makedirs(f"data/{self.master.results['Scenario'][0]}")

        for file in os.listdir(f"data/{self.master.results['Scenario'][0]}"):

            if os.path.splitext(file)[0] == self.master.results["Flight ID"][0]:
                if not messagebox.askyesno(
                    "Flight already exists",
                    "Flight already exists in database, do you want to overwrite it?",
                ):
                    return

        if not messagebox.askyesno(
            "Flight Data Storage", "Do you really want to add this flight to the flight data storage base?"
        ):
            return

        evaluate_flight_phases(
            self.master.data_frame,
            list(self.phases.values()),
            self.master.results,
        )

        self.execution_info.configure(text="Flight added to database.", fg_color="#00ab41")

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)

    def evaluate_button_event(self):
        self.execution_info.configure(text="", fg_color="transparent")

        sorted = True
        for counter, _ in enumerate(list(self.phases.values())[0:-1]):
            if list(self.phases.values())[counter] > list(self.phases.values())[counter + 1]:
                sorted = False

        if not sorted:
            messagebox.showerror(
                "Phase Timestamps Error",
                f"Phase Timestamp have to be in ascending order (from smallest to largest) but are actually not: {self.phases}.\n"
                "Make sure that the order of the phases is: Alignment Start <= Approach Start <= Final Approach Start <= Docking Time",
            )
            self.execution_info.configure(text="Phase Timestamps Error", fg_color="#ED2939")
            # lift TopLevelWindow in front
            self.lift()
            self.focus_force()
            self.after(10, self.focus_force)
            return

        if not os.path.exists(
            f"src/flight_data_evaluation_tool/database/{self.master.results['Scenario'][0]}_flight_data.json"
        ):
            messagebox.showerror(
                "Data Error",
                f"For Flight scenario {self.master.results['Scenario'][0]} no data exists in the database.",
            )
            self.execution_info.configure(text="No Evaluation Data for this Flight Scenario.", fg_color="#ED2939")
            return

        evaluated_results = evaluate_flight_phases(
            self.master.data_frame,
            list(self.phases.values()),
            self.master.results,
            export=False,
        )

        if self.evaluation_window is not None and self.evaluation_window.winfo_exists():
            self.evaluation_window.destroy()
        self.evaluation_window = EvaluationWindow(self, evaluated_results)

        self.execution_info.configure(text="Flight evaluated.", fg_color="#00ab41")

    def heatmap_button_event(self):
        """
        Generate the Heatmaps of the flight according to slider position.
        """
        if self.heatmap_window is not None and self.heatmap_window.winfo_exists():
            self.heatmap_window.destroy()
        self.heatmap_window = HeatMapWindow(self, self.master.data_frame, list(self.phases.values()))

        self.execution_info.configure(text=f"Heatmaps created.", fg_color="#00ab41")

    def toggle_phases(self):
        """
        Toggles the visibility of the phase lines.
        """
        for ax in self.axvlines:
            for vline in self.axvlines[ax]:
                vline.set_visible({"on": True, "off": False}[self.switch_var.get()])

        self.canvas.draw()

    def print_button_event(self):
        """
        Saves the plot as PNG files in the selected directory.
        """
        self.execution_info.configure(text="", fg_color="transparent")

        save_dir = filedialog.askdirectory(title="Select Save Folder")
        if not save_dir:
            return

        for ax in self.figure.axes:
            extent = ax.get_window_extent().transformed(self.figure.dpi_scale_trans.inverted())

            # Manually adjust the extent to add extra space to the left and bottom
            xmin, ymin, xmax, ymax = extent.extents
            xmin -= 0.8  # left
            xmax += 0.05  # right
            ymin -= 0.5  # bottom
            ymax += 0.05  # top

            # Create a new extent with the adjusted coordinates
            extent = Bbox([[xmin, ymin], [xmax, ymax]])

            title = ax.get_title()
            self.figure.savefig(os.path.join(save_dir, f"{title}.png"), bbox_inches=extent, dpi=400)

            self.execution_info.configure(
                text=f"Plots individually saved as 'png' under {save_dir}.", fg_color="#00ab41"
            )

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)
