import customtkinter
from tkinter import filedialog, messagebox
import os
from main import start_flight_evaluation
from evaluation import create_dataframe_template_from_yaml
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
    def __init__(self, master, figure, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("Flight Plots")

        canvas = FigureCanvasTkAgg(figure, master=self)

        toolbar = NavigationToolbar2Tk(canvas, self)
        toolbar.update()
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")

        canvas.get_tk_widget().grid(row=1, column=0, columnspan=2, sticky="nsew")
        canvas.draw()

        # Add sliders for Flight Phase
        slider_start = customtkinter.CTkSlider(self, from_=0, to=100, command=None)
        slider_start.grid(row=2, column=0, sticky="sew")

        slider_allign = customtkinter.CTkSlider(self, from_=0, to=100, command=None)
        slider_allign.grid(row=2, column=1, sticky="sew")

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)

        # Make the canvas and toolbar resize with the window
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)


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
        # Check if selected Logs are valid
        for flight_log in flight_logs:
            file_basename, file_extension = os.path.splitext(os.path.basename(flight_log))
            session_identifiers.append(file_basename.split("_")[0:-1])
            log_numbers.append(int(file_basename.split("_")[-1]))

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

        data, columns, results = self._parse_logs(flight_logs)
        if data and columns and not results.empty:
            figure = start_flight_evaluation(data, columns, results)
            self.toplevel_window = ToplevelWindow(self, figure)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.toplevel_window is not None and self.toplevel_window.winfo_exists():
                self.toplevel_window.quit()
            self.quit()

    # this function doesnt have to be a class function; ToDo
    def _parse_logs(self, flight_logs):
        data = []
        results = create_dataframe_template_from_yaml()

        for flight_log in flight_logs:
            with open(flight_log, encoding="utf-8") as file:
                lines = file.readlines()
                if flight_log == flight_logs[-1] and lines[-1].strip() != "# Log stopped.":
                    messagebox.showerror(
                        "Log Selection Error",
                        f"Last Log of the session is missing. Please select it and try again.",
                    )
                    return None, None, None

                # Iterate over each line in the file
                for line in lines:
                    if line.startswith("#"):
                        line = line.strip("#").strip()
                        if line.startswith("Logger Version:"):
                            results["Logger Version"] = line.split(":")[1].strip()
                        elif line.startswith("SESSION_ID:"):
                            results["Session ID"] = line.split(":")[1].strip()
                        elif line.startswith("PILOT:"):
                            results["Pilot"] = line.split(":")[1].strip()
                        elif line.startswith("TIME:"):
                            results["Date"] = line.split(":")[1].strip().split(" ")[0].replace("-", ".")
                        elif line.startswith("SCENARIO:"):
                            results["Scenario"] = line.split(":")[1].strip()
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

        return data, columns, results


if __name__ == "__main__":
    customtkinter.set_appearance_mode("dark")
    app = App()

    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
