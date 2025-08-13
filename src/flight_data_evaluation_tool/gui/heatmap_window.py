import os
import sys
import customtkinter
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk

import globals
from plot import create_heatmaps


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

        self.iconbitmap(default=globals.icon_path)

        self.figure = create_heatmaps(data_frame, phases)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)

        toolbar = NavigationToolbar2Tk(self.canvas, self)
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="ew")

        self.canvas.get_tk_widget().grid(row=2, column=0, sticky="nsew")
        self.canvas.draw()

        # Add meta data labels as separate elements
        pilot_label = customtkinter.CTkLabel(
            master=self,
            text=f"Pilot ID: {self.master.results['Pilot'][0]}; Scenario: {self.master.results['Scenario'][0]}",
            fg_color="#8A2BE2",
            text_color="white",
            corner_radius=8,
            anchor="w",
            padx=5,
            pady=5,
        )
        pilot_label.grid(row=0, column=0, sticky="n", padx=15, pady=15)

        print_button = customtkinter.CTkButton(
            master=self, text="Save Plots individually", command=self.print_button_event
        )
        print_button.grid(row=3, column=0, padx=15, pady=15, sticky="s")

        # lift TopLevelWindow in front
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)

        # Make the canvas and toolbar resize with the window
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)

        # Because CTkToplevel currently is bugged on windows and doesn't check if a user specified icon is set we need
        # to set the icon again after 200ms
        if sys.platform.startswith("win"):
            self.after(200, lambda: self.iconbitmap(globals.icon_path))

        self.protocol("WM_DELETE_WINDOW", self.on_close)

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

    def on_close(self):
        plt.close(self.figure)
        self.destroy()
