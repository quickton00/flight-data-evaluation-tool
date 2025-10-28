import customtkinter
from tkinter import filedialog, messagebox
import hashlib
import os
import sys
from contextlib import contextmanager

if getattr(sys, "frozen", False):
    # Running in PyInstaller bundle
    bundle_dir = sys._MEIPASS
    src_dir = os.path.join(bundle_dir)
    sys.path.insert(0, src_dir)

# Assure functionality of relative imports in development environment and standalone execution
try:
    import flight_data_evaluation_tool.globals as globals
    from flight_data_evaluation_tool.datastructuring import structure_data, calculate_approach_phases
    from flight_data_evaluation_tool.evaluation import create_dataframe_template_from_json
    from flight_data_evaluation_tool.gui.plot_window import PlotWindow
except ImportError:
    import globals
    from datastructuring import structure_data, calculate_approach_phases
    from evaluation import create_dataframe_template_from_json
    from gui.plot_window import PlotWindow


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

    NEW_COLOR = "#00ab41"
    ANALYZED_COLOR = customtkinter.ThemeManager.theme["CTkButton"]["fg_color"]

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
        # color newly added items
        checkbox.configure(text_color=self.NEW_COLOR)

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

    # mark selected/processed files as analyzed (green)
    def mark_analyzed(self, paths):
        path_set = set(paths)
        for cb, p in self.checkbox_dict.items():
            if p in path_set:
                cb.configure(text_color=self.ANALYZED_COLOR)
            elif cb.cget("text_color") != self.ANALYZED_COLOR:
                cb.configure(text_color=customtkinter.ThemeManager.theme["CTkCheckBox"]["text_color"])


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
                    f"The last part of the Log filename should be a numerical identifier like 0000, 0001 etc. but is actually '{file_basename.split('_')[-1]}'",
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

            # mark evaluated files as analyzed (green)
            self.scrollable_checkbox_frame.mark_analyzed(flight_logs)

            current_text = self.execution_info.cget("text")
            if "BACKUP" in current_text:
                color = "#ED2939"  # red
                self.toplevel_window.execution_info.configure(text=current_text.rstrip(), fg_color=color)
            else:
                color = "#00ab41"  # green
                self.toplevel_window.execution_info.configure(
                    text=current_text.rstrip() + "Plots of selected Flight-Logs created.", fg_color=color
                )

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
        self.results = create_dataframe_template_from_json()

        self.results["Flight ID"] = hashlib.sha256(str.encode(os.path.basename(flight_logs[0]))).hexdigest()

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
                            self.results["Date"] = int(line.split(":")[1].strip().split(" ")[0].split("-")[2])
                        elif line.startswith("SCENARIO:"):
                            self.results["Scenario"] = line.split(":")[1].strip()
                        continue
                    if line.startswith("SimTime"):
                        line = line.replace("MFDRightMyROT.m11", "MFDRight; MyROT.m11")  # handle bug in logger
                        for name in ["; m12", "; m13", "; m21", "; m22", "; m23", "; m31", "; m32", "; m33"]:
                            line = line.replace(name, f"; MyROT.{name.split()[1]}", 1)
                            line = line.replace(name, f"; TgtRot.{name.split()[1]}", 1)
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
    customtkinter.set_appearance_mode("system")
    app = App()

    app.iconbitmap(default=globals.icon_path)

    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
