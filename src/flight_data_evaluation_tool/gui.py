import customtkinter
from tkinter import filedialog, messagebox
import os
from main import start_flight_evaluation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


class ScrollableCheckBoxFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, master, item_list=None, command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.command = command
        self.checkbox_dict = {}

        if item_list is not None:
            for item in item_list:
                self.add_item(item)

    def add_item(self, item):
        checkbox = customtkinter.CTkCheckBox(self, text=os.path.basename(item))

        if self.command is not None:
            checkbox.configure(command=self.command)

        checkbox.pack(anchor="w", pady=(0, 10))
        self.checkbox_dict[checkbox] = item

    def remove_item(self, item):
        for checkbox in self.checkbox_dict.keys():
            if item == checkbox.cget("text"):
                checkbox.destroy()
                del self.checkbox_dict[checkbox]
                return

    def get_checked_items(self):
        return [self.checkbox_dict[checkbox] for checkbox in self.checkbox_dict.keys() if checkbox.get() == 1]


class ToplevelWindow(customtkinter.CTkToplevel):
    def __init__(self, master, figure, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # figure_size = figure.get_size_inches() * figure.dpi
        # self.geometry(f"{int(figure_size[0])}x{int(figure_size[1])}")

        self.title("Flight Plots")

        canvas = FigureCanvasTkAgg(figure, master=self)

        toolbar = NavigationToolbar2Tk(canvas, self)
        toolbar.update()
        canvas.get_tk_widget().pack(side="bottom", fill="both", expand=1)

        canvas.draw()
        canvas.get_tk_widget().pack(expand=1)


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.geometry("1400x800")

        self.title("Flight Data Evaluation Tool")

        # create button to add files
        self.file_button = customtkinter.CTkButton(master=self, text="Add Flights", command=self.add_files)
        self.file_button.pack(anchor="w", padx=15, pady=15)

        # create scrollable checkbox frame
        self.scrollable_checkbox_frame = ScrollableCheckBoxFrame(master=self)
        self.scrollable_checkbox_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # create evaluation button
        self.evaluate_button = customtkinter.CTkButton(
            master=self, text="Evaluate Flight", command=self.evaluate_button_event
        )
        self.evaluate_button.pack(anchor="w", padx=15, pady=15)

        self.toplevel_window = None

    def add_files(self):
        file_paths = filedialog.askopenfilenames(title="Select Files")
        for file_path in file_paths:
            self.scrollable_checkbox_frame.add_item(file_path)

    def evaluate_button_event(self):
        flight_logs = self.scrollable_checkbox_frame.get_checked_items()
        figure = start_flight_evaluation(flight_logs)
        self.toplevel_window = ToplevelWindow(self, figure)

        self.toplevel_window.focus()

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.quit()
            if self.toplevel_window is not None and self.toplevel_window.winfo_exists():
                self.toplevel_window.destroy()
            self.destroy()


if __name__ == "__main__":
    customtkinter.set_appearance_mode("dark")
    app = App()

    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
