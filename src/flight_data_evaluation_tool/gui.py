import customtkinter
from tkinter import filedialog, messagebox, PhotoImage
import os
import sys
import matplotlib.style
from matplotlib.transforms import Bbox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from contextlib import contextmanager
from functools import partial

# Assure functionality of relative imports in development environment and standalone execution
try:
    from flight_data_evaluation_tool.datastructuring import structure_data, calculate_approach_phases
    from flight_data_evaluation_tool.evaluation import (
        create_dataframe_template_from_yaml,
        evaluate_flight_phases,
        calculate_phase_evaluation_values,
    )
    from flight_data_evaluation_tool.plot import create_figure, create_heatmaps
except ImportError:
    from datastructuring import structure_data, calculate_approach_phases
    from evaluation import (
        create_dataframe_template_from_yaml,
        evaluate_flight_phases,
        calculate_phase_evaluation_values,
    )
    from plot import create_figure, create_heatmaps


class ScrollableCheckBoxFrame(customtkinter.CTkScrollableFrame):
    """
    A scrollable frame containing checkboxes for each flight log.

    :param master: The parent widget.
    :type master: tkinter.Widget
    :param path_list: A list of file paths to be added as checkboxes, defaults to None
    :type path_list: list, optional
    :param command: The command to be executed when a checkbox is clicked, defaults to None
    :type command: function, optional
    :param kwargs: Additional arguments to be passed to the CTkScrollableFrame.
    :type kwargs: dict
    :method add_log: Adds a new checkbox for the provided file path.
    :param path: The path of the file to be added.
    :type path: str
    :method remove_all_logs: Removes all checkboxes from the frame.
    :method get_checked_items: Returns a list of file paths for checked items.
    :return: A list of file paths for the checked checkboxes.
    :rtype: list
    """

    def __init__(self, master, path_list=None, command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.command = command
        self.checkbox_dict = {}

        if path_list is not None:
            for path in path_list:
                self.add_log(path)

    def add_log(self, path):
        """
        Adds a new checkbox for the provided file path.

        Parameters
        ----------
        path : str
            The path of the file to be added.
        """
        checkbox = customtkinter.CTkCheckBox(self, text=os.path.basename(path))

        if self.command is not None:
            checkbox.configure(command=self.command)

        checkbox.grid(row=len(self.checkbox_dict), column=0, sticky="w", pady=(0, 10))
        self.checkbox_dict[checkbox] = path

    def remove_all_logs(self):
        """
        Removes all checkboxes from the frame.
        """
        for checkbox in self.checkbox_dict.keys():
            checkbox.destroy()

        self.checkbox_dict = {}

    def get_checked_items(self):
        """
        Returns a list of file paths for checked items.

        Returns
        -------
        list
            A list of file paths for the checked checkboxes.
        """
        return [self.checkbox_dict[checkbox] for checkbox in self.checkbox_dict.keys() if checkbox.get() == 1]


class HeatMapWindow(customtkinter.CTkToplevel):
    """
    A window for displaying heatmaps of flight phases.

    Parameters
    ----------
    master : tkinter.Widget
        The parent widget.
    data_frame : pandas.DataFrame
        The flight data.
    phases : list
        The flight phases for which heatmaps will be generated.
    *args : tuple
        Additional positional arguments.
    **kwargs : dict
        Additional keyword arguments.
    """

    def __init__(self, master, data_frame, phases, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("Flight Phase Heatmaps")

        self.iconbitmap(default=icon_path)

        self.figure = create_heatmaps(data_frame, phases)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)

        toolbar = NavigationToolbar2Tk(self.canvas, self)
        toolbar.update()
        toolbar.grid(row=0, column=0, sticky="ew")

        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        self.canvas.draw()

        print_button = customtkinter.CTkButton(
            master=self, text="Save Plots individually", command=self.print_button_event
        )
        print_button.grid(row=2, column=0, padx=15, pady=15, sticky="s")

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)

        # Make the canvas and toolbar resize with the window
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)

        # Because CTkToplevel currently is bugged on windows and doesn't check if a user specified icon is set we need
        # to set the icon again after 200ms
        if sys.platform.startswith("win"):
            self.after(200, lambda: self.iconbitmap(icon_path))

    def print_button_event(self):
        """
        Saves the heatmaps as individual PNG files in the selected directory.
        """

        save_dir = filedialog.askdirectory(title="Select Save Folder")
        if not save_dir:
            return

        for ax in self.figure.axes:
            extent = ax.get_window_extent().transformed(self.figure.dpi_scale_trans.inverted())

            # Manually adjust the extent to add extra space to the left and bottom
            xmin, ymin, xmax, ymax = extent.extents
            xmin -= 0.1  # left
            xmax += 0.1  # right
            ymin -= 0.1  # bottom
            ymax += 0.3  # top

            # Create a new extent with the adjusted coordinates
            extent = Bbox([[xmin, ymin], [xmax, ymax]])

            title = ax.get_title()
            self.figure.savefig(os.path.join(save_dir, f"{title}.png"), bbox_inches=extent, dpi=400)

        self.master.toplevel_window.execution_info.configure(
            text=f"Heatmaps individually saved as 'png' under {save_dir}.", fg_color="#00ab41"
        )

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)


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

        self.master = master
        self.phases = {}
        for counter, phase in enumerate(
            ["Alignment Start (s):", "Approach Start (s):", "Final Approach Start (s):", "Docking Time (s):"]
        ):
            self.phases[phase] = phases[counter]

        self.title("Flight Plots")

        self.iconbitmap(default=icon_path)

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
        toolbar.grid(row=0, column=0, columnspan=4, sticky="ew")

        self.canvas.get_tk_widget().grid(row=1, column=0, columnspan=4, sticky="nsew")
        self.canvas.draw()

        # Add phase number fields
        self.entries = {}
        for counter, phase in enumerate(
            ["Alignment Start (s):", "Approach Start (s):", "Final Approach Start (s):", "Docking Time (s):"]
        ):
            entry = customtkinter.CTkLabel(
                master=self, text=f"{phase} {self.phases[phase]}", fg_color="transparent", anchor="w"
            )
            self.entries[phase] = entry
            entry.grid(row=2, column=counter, sticky="sew")

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
                slider.grid(row=3, column=counter, sticky="sew")
                slider._canvas.bind("<Button-1>", self.on_focus)
                # Bind arrow keys for keyboard control
                slider._canvas.bind("<Left>", partial(self.keyboard_slider_control, slider, phase, "left"))
                slider._canvas.bind("<Right>", partial(self.keyboard_slider_control, slider, phase, "right"))

        # Add various buttons
        if x_axis_type == "SimTime":
            evaluate_button = customtkinter.CTkButton(
                master=self, text="Create EvaluationResults.txt", command=self.evaluate_button_event
            )
            evaluate_button.grid(row=4, column=0, padx=15, pady=15, sticky="s")
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
            phases_switch.grid(row=4, column=0, padx=15, pady=15, sticky="s")

        print_button = customtkinter.CTkButton(
            master=self, text="Save Plots individually", command=self.print_button_event
        )
        print_button.grid(row=4, column=1, padx=15, pady=15, sticky="s")

        # Button for Heatmap Calculation
        heatmap_button = customtkinter.CTkButton(
            master=self, text="Show Heatmaps for Flight Phases", command=self.heatmap_button_event
        )
        heatmap_button.grid(row=4, column=2, padx=15, pady=15, sticky="s")

        # create execution info box
        self.execution_info = customtkinter.CTkLabel(
            master=self, text="", fg_color="transparent", corner_radius=15, wraplength=350
        )
        self.execution_info.grid(row=4, column=3)
        if _failed_error_calculation_:
            self.execution_info.configure(
                text="Flight Errors could not be determined. Check if scenario is a docking scenario!",
                fg_color="#ED2939",
            )

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)

        # Make the canvas and toolbar resize with the window
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Because CTkToplevel currently is bugged on windows and doesn't check if a user specified icon is set we need
        # to set the icon again after 200ms
        if sys.platform.startswith("win"):
            self.after(200, lambda: self.iconbitmap(icon_path))

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

    def evaluate_button_event(self):
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

        save_dir = filedialog.askdirectory(title="Select Save Folder")
        if not save_dir:
            return

        eval_file_path = os.path.join(save_dir, "EvaluationResults.txt")
        if os.path.exists(eval_file_path):
            response = messagebox.askyesno(
                "File Exists", "EvaluationResults.txt already exists. Do you want to add the data to this file?"
            )
            if response is True:
                overwrite = False
            else:
                overwrite = True
        else:
            overwrite = True

        evaluate_flight_phases(
            self.master.data_frame, list(self.phases.values()), self.master.results, save_dir, overwrite
        )

        self.execution_info.configure(text=f"EvaluationResults.txt created under {save_dir}.", fg_color="#00ab41")

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)

    def heatmap_button_event(self):
        """
        Generate the Heatmaps of the flight according to slider position.
        """
        HeatMapWindow(self, self.master.data_frame, list(self.phases.values()))

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


class App(customtkinter.CTk):
    """
    A GUI application for evaluating flight data logs using customtkinter.
    Attributes:
        preconfigured_phases (dict): Stores phases that were manually modified or previously calculated.
        file_button (customtkinter.CTkButton): Button to add flight log files.
        delete_files_button (customtkinter.CTkButton): Button to remove all flight log files.
        scrollable_checkbox_frame (ScrollableCheckBoxFrame): Frame containing checkboxes for each flight log file.
        evaluate_button (customtkinter.CTkButton): Button to evaluate the selected flight logs.
        option_menu (customtkinter.CTkOptionMenu): Option menu to select the x-axis for the plots.
        execution_info (customtkinter.CTkLabel): Label to display execution information.
        toplevel_window (PlotWindow or None): Window to display the plots of the evaluated flight logs.
        session_identifier (str): Identifier for the current session.
        data_frame (pd.DataFrame): DataFrame containing structured flight log data.
        results (pd.DataFrame): DataFrame template created from YAML configuration.
    Methods:
        __init__(): Initializes the GUI application.
        add_files(): Opens a file dialog to select flight log files and adds them to the checkbox frame.
        remove_all_files(): Removes all flight log files from the checkbox frame.
        evaluate_button_event(): Evaluates the selected flight logs and displays the results in a new window.
        on_closing(): Handles the closing event of the application.
        _parse_logs(flight_logs): Parses the selected flight log files and returns the data and columns.
        redirect_stdout_to_label(): Context manager to redirect stdout to the execution_info label.
    """

    def __init__(self):
        """
        Initializes the main GUI window for the Flight Data Evaluation Tool.
        This method sets up the main window's geometry, title, and layout configuration.
        It also creates and places various widgets including buttons, labels, and a scrollable
        checkbox frame.
        Attributes:
            preconfigured_phases (dict): Stores phases that were manually modified or previously calculated.
            file_button (CTkButton): Button to add flight files.
            delete_files_button (CTkButton): Button to remove all flight files.
            scrollable_checkbox_frame (ScrollableCheckBoxFrame): Frame containing scrollable checkboxes.
            evaluate_button (CTkButton): Button to evaluate the selected flight.
            option_menu (CTkOptionMenu): Dropdown menu to select the x-axis for plots.
            execution_info (CTkLabel): Label to display execution information.
            toplevel_window (None): Placeholder for a toplevel window, if needed.
        """
        super().__init__()

        # store phases that where manually modified or previously calculated in a variable
        self.preconfigured_phases = {}

        self.geometry("1400x800")
        self.title("Flight Data Evaluation Tool")

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # create button to add files
        self.file_button = customtkinter.CTkButton(master=self, text="Add Flights", command=self.add_files)
        self.file_button.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        # create button to remove all files
        self.delete_files_button = customtkinter.CTkButton(
            master=self, text="Remove All Flights", command=self.remove_all_files
        )
        self.delete_files_button.grid(row=0, column=3, padx=15, pady=15, sticky="e")

        # create scrollable checkbox frame
        self.scrollable_checkbox_frame = ScrollableCheckBoxFrame(master=self)
        self.scrollable_checkbox_frame.grid(row=1, column=0, columnspan=4, padx=15, pady=15, sticky="nsew")

        # create evaluation button
        self.evaluate_button = customtkinter.CTkButton(
            master=self, text="Evaluate Flight", command=self.evaluate_button_event
        )
        self.evaluate_button.grid(row=2, column=0, padx=15, pady=15, sticky="w")

        # create plot option menu
        settings_label = customtkinter.CTkLabel(
            master=self, text="Select the x-Axis for the plots:", fg_color="transparent"
        )
        settings_label.grid(row=2, column=1, padx=15, pady=15, sticky="w")

        # create plot option menu
        self.option_menu = customtkinter.CTkOptionMenu(
            master=self, values=["Simulation time", "Axial distance Vessel-Station"]
        )
        self.option_menu.grid(row=2, column=2, padx=15, pady=15, sticky="w")

        # create execution info box
        self.execution_info = customtkinter.CTkLabel(
            master=self, text="", fg_color="transparent", width=30, corner_radius=15
        )
        self.execution_info.grid(row=2, column=3, padx=15, pady=15)

        self.toplevel_window = None

    def add_files(self):
        """
        Opens a file dialog to select multiple files and adds their paths to the scrollable checkbox frame.

        This method uses the filedialog.askopenfilenames() function to open a file selection dialog,
        allowing the user to select multiple files. The selected file paths are then added to the
        scrollable checkbox frame by calling the add_log method on the scrollable_checkbox_frame object.
        """
        file_paths = filedialog.askopenfilenames(title="Select Files")
        for file_path in file_paths:
            self.scrollable_checkbox_frame.add_log(file_path)

    def remove_all_files(self):
        """
        Removes all files from the scrollable checkbox frame.

        This method calls the `remove_all_logs` method on the `scrollable_checkbox_frame`
        to clear all the logs/files displayed in the GUI.
        """
        self.scrollable_checkbox_frame.remove_all_logs()

    def evaluate_button_event(self):
        """
        Handles the event triggered by the evaluate button.
        This method performs the following steps:
        1. Clears the execution info label.
        2. Retrieves and sorts the selected flight logs.
        3. Validates the selected flight logs for correct format and naming conventions.
        4. Ensures all selected logs are from the same session and that all logs in the session are provided.
        5. Parses the logs and structures the data.
        6. Calculates or retrieves preconfigured approach phases.
        7. Opens a new window to plot the data.
        If any validation fails, an error message is displayed and the method returns early.
        Raises:
            ValueError: If the last part of the log filename is not a numerical identifier.
        Returns:
            None
        """

        self.execution_info.configure(text="", fg_color="transparent")
        flight_logs = self.scrollable_checkbox_frame.get_checked_items()
        flight_logs = sorted(flight_logs, key=os.path.basename)

        session_identifiers = []
        log_numbers = []

        if not flight_logs:
            return

        # Check if selected Logs are valid
        for flight_log in flight_logs:
            file_basename, file_extension = os.path.splitext(os.path.basename(flight_log))

            if file_extension != ".log":
                messagebox.showerror(
                    "Log Format Error",
                    f"The Format of the Flight Log '{os.path.basename(flight_log)}' is '{file_extension}' but '.log' is required",
                )
                self.execution_info.configure(text="Log Format Error", fg_color="#ED2939")
                return

            if not file_basename.startswith("FDL"):
                messagebox.showerror(
                    "Log Naming Error",
                    f"The Name of the Flight Log '{os.path.basename(flight_log)}' don't starts with FDL.",
                )
                self.execution_info.configure(text="Log Naming Error", fg_color="#ED2939")
                return

            session_identifiers.append(file_basename.rsplit("_", 1)[0])

            try:
                log_numbers.append(int(file_basename.split("_")[-1]))
            except ValueError:
                messagebox.showerror(
                    "Log Naming Error",
                    f"The last part of the Log filename should be a numerical identifier like 0000, 0001 etc. but is actually '{file_basename.split("_")[-1]}'",
                )
                self.execution_info.configure(text="Log Naming Error", fg_color="#ED2939")
                return

        if not all(session_identifier == session_identifiers[0] for session_identifier in session_identifiers):
            messagebox.showerror(
                "Log Selection Error",
                "Not all selected Logs are from the same Session.",
            )
            self.execution_info.configure(text="Log Selection Error", fg_color="#ED2939")
            return

        if not all(log_numbers[i] == i for i in range(len(log_numbers))):
            messagebox.showerror(
                "Log Selection Error",
                f"Not all Logs of the Session are provided. Only the Logs {log_numbers} are selected.",
            )
            self.execution_info.configure(text="Log Selection Error", fg_color="#ED2939")
            return

        self.session_identifier = session_identifiers[0]
        if self.session_identifier not in self.preconfigured_phases:
            self.preconfigured_phases[self.session_identifier] = None

        data, columns = self._parse_logs(flight_logs)
        if data and columns and not self.results.empty:
            self.data_frame = structure_data(data, columns)

            with self.redirect_stdout_to_label():
                if (
                    self.preconfigured_phases[self.session_identifier] is None
                    or self.option_menu.get() != "Axial distance Vessel-Station"
                ):
                    phases = calculate_approach_phases(self.data_frame)
                    self.preconfigured_phases[self.session_identifier] = phases
                else:
                    phases = self.preconfigured_phases[self.session_identifier]
                    print("Previously manually adjusted Flight Phases for the selected session used.")

            self.toplevel_window = PlotWindow(self, phases)

            current_text = self.execution_info.cget("text")
            if "BACKUP" in current_text:
                color = "#ED2939"  # red
                self.toplevel_window.execution_info.configure(text=current_text.rstrip(), fg_color=color)
            else:
                color = "#00ab41"  # green
            self.execution_info.configure(text=current_text + "Plots of selected Flight-Logs created.", fg_color=color)

    def on_closing(self):
        """
        Handles the event when the GUI window is being closed.

        This method prompts the user with a confirmation dialog to confirm if they want to quit the application.
        If the user confirms, it checks if there is an existing top-level window and if it exists, it quits that window.
        Finally, it quits the main application window.
        """
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.toplevel_window is not None and self.toplevel_window.winfo_exists():
                self.toplevel_window.quit()
            self.quit()

    def _parse_logs(self, flight_logs):
        """
        Parses flight log files and extracts relevant information into a structured format.
        Args:
            flight_logs (list of str): List of file paths to the flight log files.
        Returns:
            tuple: A tuple containing:
            - data (list of list of float): Parsed numerical data from the logs.
            - columns (filter): Filtered column names from the logs.
        Raises:
            None
        Notes:
            - If the last log file does not end with "# Log stopped.", an error message is shown and the function returns None, None.
            - The function updates self.results with extracted metadata from the logs.
            - Handles a specific bug in the logger by replacing "MFDRightMyROT.m11" with "MFDRight; MyROT.m11".
        """
        data = []
        self.results = create_dataframe_template_from_yaml()

        for flight_log in flight_logs:
            with open(flight_log, encoding="utf-8") as file:
                lines = file.readlines()
                if flight_log == flight_logs[-1] and lines[-1].strip() != "# Log stopped.":
                    messagebox.showerror(
                        "Log Selection Error",
                        "Last Log of the session is missing. Please select it and try again.",
                    )
                    self.execution_info.configure(text="Log Selection Error", fg_color="#ED2939")
                    return None, None

                # Iterate over each line in the file
                for line in lines:
                    if line.startswith("#"):
                        line = line.strip("#").strip()
                        if line.startswith("Logger Version:"):
                            self.results["Logger Version"] = line.split(":")[1].strip()
                        elif line.startswith("SESSION_ID:"):
                            self.results["Session ID"] = line.split(":")[1].strip()
                        elif line.startswith("PILOT:"):
                            self.results["Pilot"] = line.split(":")[1].strip()
                        elif line.startswith("TIME:"):
                            self.results["Date"] = line.split(":")[1].strip().split(" ")[0].replace("-", ".")
                        elif line.startswith("SCENARIO:"):
                            self.results["Scenario"] = line.split(":")[1].strip()
                        continue
                    if line.startswith("SimTime"):
                        line = line.replace("MFDRightMyROT.m11", "MFDRight; MyROT.m11")  # handle bug in logger
                        columns = map(str.strip, line.split(";"))
                        columns = filter(None, columns)
                        continue

                    # Split the line using ';' as delimiter
                    values = map(str.strip, line.split(";"))
                    values = filter(None, values)
                    values = [float(value) for value in values]
                    data.append(values)

        self.results["Manually modified Phases"] = "No"

        return data, columns

    @contextmanager
    def redirect_stdout_to_label(self):
        """
        Redirects the standard output (stdout) to a label widget in the GUI.
        This method temporarily replaces the standard output stream with a custom
        stream that appends any printed messages to a label widget (`self.execution_info`).
        This allows for capturing and displaying printed output directly in the GUI.
        Usage:
            with self.redirect_stdout_to_label():
                # Any print statements here will be redirected to the label
                print("This will appear in the label")
        The redirection is automatically reverted back to the original stdout
        when exiting the context manager.
        Note:
            This method uses a context manager to ensure that stdout is properly
            restored even if an exception occurs within the block.
        Raises:
            AttributeError: If `self.execution_info` does not have a `cget` or `configure` method.
        """

        def new_stdout_write(message):
            current_text = self.execution_info.cget("text")

            self.execution_info.configure(text=current_text + message)

        class StdoutRedirector:
            def write(self, message):
                new_stdout_write(message)

            def flush(self):
                pass

        sys.stdout = StdoutRedirector()

        try:
            yield
        finally:
            sys.stdout = sys.__stdout__


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        icon_path = sys._MEIPASS  # Check if running in a PyInstaller bundle
        icon_path = os.path.join(icon_path, "icon.ico")
    else:
        icon_path = r"src\flight_data_evaluation_tool\icon.ico"

    customtkinter.set_appearance_mode("system")
    app = App()

    app.iconbitmap(default=icon_path)

    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
