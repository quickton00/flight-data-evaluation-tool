import customtkinter
from tkinter import filedialog, messagebox
import os
import matplotlib.pyplot as plt
from datastructuring import structure_data, calculate_approach_phases
from evaluation import create_dataframe_template_from_yaml, evaluate_flight_phases, calculate_phase_evaluation_values
from plot import create_figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


class ScrollableCheckBoxFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, master, path_list=None, command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.command = command
        self.checkbox_dict = {}

        if path_list is not None:
            for path in path_list:
                self.add_log(path)

    def add_log(self, path):
        checkbox = customtkinter.CTkCheckBox(self, text=os.path.basename(path))

        if self.command is not None:
            checkbox.configure(command=self.command)

        checkbox.grid(row=len(self.checkbox_dict), column=0, sticky="w", pady=(0, 10))
        self.checkbox_dict[checkbox] = path

    def remove_all_logs(self):
        for checkbox in self.checkbox_dict.keys():
            checkbox.destroy()

        self.checkbox_dict = {}

    def get_checked_items(self):
        return [self.checkbox_dict[checkbox] for checkbox in self.checkbox_dict.keys() if checkbox.get() == 1]


class ToplevelWindow(customtkinter.CTkToplevel):
    def __init__(self, master, phases, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.master = master
        self.phases = phases
        self.title("Flight Plots")

        total_flight_errors = calculate_phase_evaluation_values(self.master.data_frame, "Total", 0, 3, self.phases, self.master.results)

        self.figure, self.axvlines = create_figure(self.master.data_frame, self.phases, total_flight_errors)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)

        toolbar = NavigationToolbar2Tk(self.canvas, self)
        toolbar.update()
        toolbar.grid(row=0, column=0, columnspan=4, sticky="ew")

        self.canvas.get_tk_widget().grid(row=1, column=0, columnspan=4, sticky="nsew")
        self.canvas.draw()

        # Add phase number fields
        self.entries = []
        for counter, phase in enumerate(["Alignment Start (s):", "Approach Start (s):", "Final Approach Start (s):", "Docking Time (s):"]):
            entry = customtkinter.CTkLabel(master=self, text=f"{phase} {round(self.phases[counter], 4)}", fg_color="transparent", anchor="w")
            self.entries.append(entry)
            entry.grid(row=2, column=counter, sticky="sew")

        # Add sliders for Flight Phase
        self.sliders = []
        for counter, _ in enumerate(self.phases):
            slider = customtkinter.CTkSlider(master=self, from_=0, to=self.master.data_frame.iloc[-1]["SimTime"], command=self.update_phase_lines)
            self.sliders.append(slider)
            slider.set(self.phases[counter])
            slider.grid(row=3, column=counter, sticky="sew")

        # Add various buttons
        evaluate_button = customtkinter.CTkButton(
            master=self, text="Create EvaluationResults.txt", command=self.evaluate_button_event
        )
        evaluate_button.grid(row=4, column=0, padx=15, pady=15, sticky="s")

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)

        # Make the canvas and toolbar resize with the window
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

    def update_phase_lines(self, _):
        self.master.results["Manually modified Phases"] = "Yes"

        for counter, phase in enumerate(["Alignment Start (s):", "Approach Start (s):", "Final Approach Start (s):", "Docking Time (s):"]):
            self.phases[counter] = self.sliders[counter].get()
            self.entries[counter].configure(text=f"{phase} {round(self.phases[counter], 4)}")
            for ax in self.axvlines:
                self.axvlines[ax][counter].set_xdata([self.phases[counter]])

        self.canvas.draw()

    def evaluate_button_event(self):
        # refactor timestamps of modified phases to nearest values in data_frame
        for counter, _ in enumerate(self.phases):
            self.phases[counter] = min(self.master.data_frame["SimTime"], key=lambda x: abs(x - self.phases[counter]))

        sorted = True
        for counter, _ in enumerate(self.phases[0:-1]):
            if self.phases[counter] > self.phases[counter+1]:
                sorted = False

        if not sorted:
            messagebox.showerror(
                "Phase Timestamps Error",
                f"Phase Timestamp have to be in ascending order (from smallest to largest) but are actually not: {self.phases}.\n"
                "Make sure that the order of the phases is: Alignment Start <= Approach Start <= Final Approach Start <= Docking Time",
            )
            return

        save_dir = filedialog.askdirectory(title="Select Save Folder")
        if not save_dir:
            return

        evaluate_flight_phases(self.master.data_frame, self.phases, self.master.results, save_dir)


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

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
        self.delete_files_button.grid(row=0, column=1, padx=15, pady=15)

        # create scrollable checkbox frame
        self.scrollable_checkbox_frame = ScrollableCheckBoxFrame(master=self)
        self.scrollable_checkbox_frame.grid(row=1, column=0, columnspan=3, padx=15, pady=15, sticky="nsew")

        # create evaluation button
        self.evaluate_button = customtkinter.CTkButton(
            master=self, text="Evaluate Flight", command=self.evaluate_button_event
        )
        self.evaluate_button.grid(row=2, column=0, padx=15, pady=15, sticky="w")

        self.toplevel_window = None

    def add_files(self):
        file_paths = filedialog.askopenfilenames(title="Select Files")
        for file_path in file_paths:
            self.scrollable_checkbox_frame.add_log(file_path)

    def remove_all_files(self):
        self.scrollable_checkbox_frame.remove_all_logs()

    def evaluate_button_event(self):
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
                return

            if not file_basename.startswith("FDL"):
                messagebox.showerror(
                    "Log Naming Error",
                    f"The Name of the Flight Log '{os.path.basename(flight_log)}' don't starts with FDL.",
                )
                return

            session_identifiers.append(file_basename.rsplit("_", 1)[0])

            try:
                log_numbers.append(int(file_basename.split("_")[-1]))
            except ValueError:
                messagebox.showerror(
                    "Log Naming Error",
                    f"The last part of the Log filename should be a numerical identifier like 0000, 0001 etc. but is actually '{file_basename.split("_")[-1]}'",
                )
                return

        if not all(session_identifier == session_identifiers[0] for session_identifier in session_identifiers):
            messagebox.showerror(
                "Log Selection Error",
                "Not all selected Logs are from the same Session.",
            )
            return

        if not all(log_numbers[i] == i for i in range(len(log_numbers))):
            messagebox.showerror(
                "Log Selection Error",
                f"Not all Logs of the Session are provided. Only the Logs {log_numbers} are selected.",
            )
            return

        data, columns = self._parse_logs(flight_logs)
        if data and columns and not self.results.empty:
            self.data_frame = structure_data(data, columns)

            phases = calculate_approach_phases(self.data_frame)

            self.toplevel_window = ToplevelWindow(self, phases)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.toplevel_window is not None and self.toplevel_window.winfo_exists():
                self.toplevel_window.quit()
            self.quit()

    # this function doesnt have to be a class function; ToDo
    def _parse_logs(self, flight_logs):
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


if __name__ == "__main__":
    customtkinter.set_appearance_mode("dark")
    app = App()

    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
