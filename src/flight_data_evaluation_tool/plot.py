import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd


# Responsive styling helpers
def _compute_scale(fig, base_px=1600):
    w, h = fig.get_size_inches()
    px_w = 2 * h * fig.get_dpi()
    # Clamp scale to reasonable bounds
    return max(0.75, min(1.6, px_w / base_px))


def _apply_responsive_styling(fig):
    scale = _compute_scale(fig)
    sizes = {
        "title": int(10 * scale),
        "label": int(9 * scale),
        "tick": int(7 * scale),
        "legend": int(7 * scale),
    }
    for ax in fig.axes:
        # Titles and labels
        ax.set_title(ax.get_title(), fontsize=sizes["title"], pad=4, wrap=True)
        ax.xaxis.label.set_size(sizes["label"])
        ax.yaxis.label.set_size(sizes["label"])
        ax.xaxis.labelpad = 2
        ax.yaxis.labelpad = 2

        # Ticks
        ax.tick_params(axis="both", labelsize=sizes["tick"])

        # Legends
        leg = ax.get_legend()
        if leg:
            leg.set_title(None)
            for text in leg.get_texts():
                text.set_fontsize(sizes["legend"])

    # Let layout engine resolve remaining overlaps
    fig.canvas.draw_idle()


def _attach_resize_listener(fig):
    def _on_resize(event):
        _apply_responsive_styling(event.canvas.figure)

    # Listen to resize events
    if fig.canvas is not None:
        fig.canvas.mpl_connect("resize_event", _on_resize)


def _plot_values(
    ax,
    flight_data: pd.DataFrame,
    x_values: pd.DataFrame,
    y_values: pd.DataFrame,
    title: str,
    x_label: str,
    y_label: str,
    total_flight_errors: dict,
    x_axis_type: str,
    plot_names=None,
    phases=[],
    corridor=None,
):
    """
    Function to plot x-values against y-values.
    The y-values can either be one list or a dataframe of multiple columns.
    Each column will be displayed as a new curve.

    :param x_values: values for the x-axis
    :type x_values: pd.DataFrame
    :param y_values: values for the y-axis
    :type y_values: pd.DataFrame
    :param title: title of the plot
    :type title: str
    :param x_label: label for the x-axis
    :type x_label: str
    :param y_label: label for the y-axis
    :type y_label: str
    :param plot_names: parameter to rename plots via a dictionary, defaults to None
    :type plot_names: dict, optional
    """

    mpl.rcParams["path.simplify"] = True
    mpl.rcParams["path.simplify_threshold"] = 1.0

    error_assignment = {
        "COG Pos.x [m]": "THC.x",
        "COG Pos.y [m]": "THC.y",
        "COG Pos.z [m]": "THC.z",
        "COG Vel.x [m]": "THC.x",
        "COG Vel.y [m]": "THC.y",
        "COG Vel.z [m]": "THC.z",
        "Rot Angle.x [deg]": "RHC.x",
        "Rot Angle.y [deg]": "RHC.y",
        "Rot Angle.z [deg]": "RHC.z",
        "Rot. Rate.x [deg/s]": "RHC.x",
        "Rot. Rate.y [deg/s]": "RHC.y",
        "Rot. Rate.z [deg/s]": "RHC.z",
        "THC.x": "THC.x",
        "THC.y": "THC.y",
        "THC.z": "THC.z",
        "RHC.x": "RHC.x",
        "RHC.y": "RHC.y",
        "RHC.z": "RHC.z",
    }

    if isinstance(y_values, pd.DataFrame):
        for column_name, column_data in y_values.items():
            if plot_names is not None:
                plot_name = plot_names[column_name]
            else:
                plot_name = column_name

            ax.plot(x_values.tolist(), column_data.tolist(), marker="", linestyle="-", linewidth=0.5, label=plot_name)

            # mark flight errors in respective plots
            if "." in column_name:
                if x_axis_type == "SimTime":
                    total_flight_errors_x_values = total_flight_errors[error_assignment[column_name]]
                elif x_axis_type == "COG Pos.x [m]":
                    total_flight_errors_x_values = flight_data[
                        flight_data["SimTime"].isin(total_flight_errors[error_assignment[column_name]])
                    ]["COG Pos.x [m]"].values

                ax.scatter(
                    total_flight_errors_x_values,
                    flight_data[flight_data["SimTime"].isin(total_flight_errors[error_assignment[column_name]])][
                        column_name
                    ].to_list(),
                    color="red",
                    s=10,
                    zorder=5,
                )

    else:
        ax.plot(
            x_values.tolist(), y_values.tolist(), marker="", linestyle="-", linewidth=0.5, label=y_values.name
        )  # better without using pandas series

    axvlines = []
    for value in phases:
        if value is not None:
            axvline = ax.axvline(x=value, color="black", linestyle=":")
            axvlines.append(axvline)

    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.legend(loc="upper right")
    ax.grid(linestyle="--", linewidth=0.5)

    if corridor:
        ax.fill_between(
            flight_data.sort_values(by=[x_axis_type])[x_axis_type].tolist(),
            flight_data.sort_values(by=[x_axis_type])[corridor].tolist(),
            (flight_data.sort_values(by=[x_axis_type])[corridor] * -1).tolist(),
            color="#d3d3d3",
            label=corridor,
        )
        ax.legend(loc="upper right")

    return axvlines


def create_figure(data_frame, phases, total_flight_errors, x_axis_type):
    """
    Creates a matplotlib figure with multiple subplots based on the provided data.
    Parameters:
    data_frame (pd.DataFrame): The data frame containing the flight data.
    phases (list): A list of phase times or positions to be marked on the x-axis.
    total_flight_errors (dict): A dictionary containing total flight errors for each phase.
    x_axis_type (str): The type of x-axis to use ('SimTime' or 'COG Pos.x [m]').
    Returns:
    tuple: A tuple containing the created figure and a dictionary of vertical lines for each subplot.
    """
    mpl.style.use("fast")
    # Use constrained layout to reduce overlaps
    figure = plt.figure(figsize=(24, 12))
    figure.set_constrained_layout(True)

    plots = {
        "Translational Offset to Port-Station": [
            data_frame[["COG Pos.x [m]", "COG Pos.y [m]", "COG Pos.z [m]", "Lateral Offset"]],
            "Translational Offset (m)",
            {
                "COG Pos.x [m]": "Trans. Offset X",
                "COG Pos.y [m]": "Trans. Offset Y",
                "COG Pos.z [m]": "Trans. Offset Z",
                "Lateral Offset": "Lateral Offset",
            },
            "Approach Cone",
        ],
        "Translational Velocity (CoG Vessel)": [
            data_frame[["COG Vel.x [m]", "COG Vel.y [m]", "COG Vel.z [m]", "Ideal Approach Vel"]],
            "Translational Velocity (m/s)",
            None,
            None,
        ],
        "Angular Position of the Vessel": [
            data_frame[["Rot Angle.x [deg]", "Rot Angle.y [deg]", "Rot Angle.z [deg]"]],
            "Rotational Angle (°)",
            {
                "Rot Angle.x [deg]": "Roll Position",
                "Rot Angle.y [deg]": "Yaw Position",
                "Rot Angle.z [deg]": "Pitch Position",
            },
            "Max Rot Angle",
        ],
        "Rotation Velocities": [
            data_frame[["Rot. Rate.x [deg/s]", "Rot. Rate.y [deg/s]", "Rot. Rate.z [deg/s]"]],
            "Rotational Rate (°/s)",
            {
                "Rot. Rate.x [deg/s]": "Roll Rate",
                "Rot. Rate.y [deg/s]": "Yaw Rate",
                "Rot. Rate.z [deg/s]": "Pitch Rate",
            },
            "Max Rot Velocity",
        ],
        "THC": [
            data_frame[["THC.x", "THC.y", "THC.z"]],
            "Translational Controller Inputs",
            None,
            None,
        ],
        "RHC": [
            data_frame[["RHC.x", "RHC.y", "RHC.z"]],
            "Rotational Controller Inputs",
            None,
            None,
        ],
        "Tank Mass over Simulation Time": [
            data_frame["Tank mass [kg]"],
            "Tank Mass (kg)",
            None,
            None,
        ],
        "Angle between periscope and port-axis": [
            data_frame["Angle to Port"],
            "Angle (docking port is visible when under 7.5°)",
            None,
            None,
        ],
    }

    axvlines = {}
    for counter, title in enumerate(plots, 1):
        ax = figure.add_subplot(240 + counter)

        if x_axis_type == "SimTime":
            _x_label_ = "Simulation time (s)"
            _phases_ = phases
        elif x_axis_type == "COG Pos.x [m]":
            _x_label_ = "Axial distance Vessel-Station [m]"
            _phases_ = data_frame[data_frame["SimTime"].isin(phases)]["COG Pos.x [m]"].values

        sub_axvlines = _plot_values(
            ax,
            data_frame,
            data_frame[x_axis_type],
            plots[title][0],
            title,
            _x_label_,
            plots[title][1],
            total_flight_errors,
            x_axis_type,
            plots[title][2],
            _phases_,
            corridor=plots[title][3],
        )

        axvlines[ax] = sub_axvlines

    # Apply responsive fonts now and on future resizes
    _apply_responsive_styling(figure)
    _attach_resize_listener(figure)

    return figure, axvlines


def create_heatmaps(flight_data: pd.DataFrame, phases: list):
    """
    Create heatmaps for different flight phases.
    This function generates a figure with subplots representing different phases of a flight.
    Each subplot contains scatter plots of the vessel's position and circles representing the
    approach cone at the start and end of each phase.
    Parameters:
    flight_data (pd.DataFrame): DataFrame containing flight data with columns "SimTime",
                                "Approach Cone", "COG Pos.z [m]", and "COG Pos.y [m]".
    phases (list): List of phase start times. The last element is the end time of the last phase.
    Returns:
    matplotlib.figure.Figure: The generated figure containing the heatmaps.
    """
    mpl.style.use("fast")
    mpl.rcParams["path.simplify"] = True
    mpl.rcParams["path.simplify_threshold"] = 1.0

    figure = plt.figure(figsize=(12, 12))

    titles = ["Alignment Phase", "Approach Phase", "Final Approach", "Total Flight"]

    for counter, _ in enumerate(phases):
        if counter != len(phases) - 1:
            phase_start = phases[counter]
            phase_end = phases[counter + 1]
        else:
            phase_start = flight_data["SimTime"].iloc[0]
            phase_end = phases[counter]

        ax = figure.add_subplot(220 + counter + 1)

        filtered_flight_data = flight_data[
            (flight_data["SimTime"] >= phase_start) & (flight_data["SimTime"] < phase_end)
        ]

        start_circle = plt.Circle(
            (0, 0),
            radius=filtered_flight_data["Approach Cone"].iloc[0],
            fill=False,
            linestyle="--",
            linewidth=1,
            color="green",
            label="Approach Cone at Phase Start",
        )
        ax.add_patch(start_circle)
        end_circle = plt.Circle(
            (0, 0),
            radius=filtered_flight_data["Approach Cone"].iloc[-1],
            fill=False,
            linestyle="--",
            linewidth=1,
            color="red",
            label="Approach Cone at Phase End",
        )
        ax.add_patch(end_circle)

        ax.scatter(
            filtered_flight_data["COG Pos.z [m]"],
            filtered_flight_data["COG Pos.y [m]"],
            s=1,
            color="grey",
        )

        ax.scatter(
            filtered_flight_data["COG Pos.z [m]"].iloc[0],
            filtered_flight_data["COG Pos.y [m]"].iloc[0],
            s=10,
            color="green",
            label="Vessel Pos. at Phase Start",
            marker="x",
        )

        ax.scatter(
            filtered_flight_data["COG Pos.z [m]"].iloc[-1],
            filtered_flight_data["COG Pos.y [m]"].iloc[-1],
            s=10,
            color="red",
            label="Vessel Pos. at Phase End",
            marker="x",
        )

        xabs_max = abs(max(ax.get_xlim(), key=abs))
        yabs_max = abs(max(ax.get_ylim(), key=abs))

        if xabs_max > yabs_max:
            ax.set_xlim(xmin=-xabs_max, xmax=xabs_max)
            ax.set_ylim(ymin=-xabs_max, ymax=xabs_max)
        else:
            ax.set_xlim(xmin=-yabs_max, xmax=yabs_max)
            ax.set_ylim(ymin=-yabs_max, ymax=yabs_max)

        ax.set_title(titles[counter])
        ax.grid(linestyle="dotted", linewidth=1)
        ax.legend(loc="upper right", prop={"size": 8})

        # set the x-spine (see below for more info on `set_position`)
        ax.spines["left"].set_position("zero")

        # turn off the right spine/ticks
        ax.spines["right"].set_color("none")
        ax.yaxis.tick_left()

        # set the y-spine
        ax.spines["bottom"].set_position("zero")

        # turn off the top spine/ticks
        ax.spines["top"].set_color("none")
        ax.xaxis.tick_bottom()

        # Remove zero from axis labels
        x_ticks = ax.get_xticks().tolist()
        y_ticks = ax.get_yticks().tolist()
        if 0 in x_ticks:
            x_ticks.remove(0)
        if 0 in y_ticks:
            y_ticks.remove(0)
        ax.set_xticks(x_ticks)
        ax.set_yticks(y_ticks)

        ax.set_xlabel("Trans. Offset Z", loc="right")
        ax.set_ylabel("Trans. Offset Y", loc="bottom")

        ax.set_aspect("equal")

    # Apply responsive fonts now and on future resizes
    _apply_responsive_styling(figure)
    _attach_resize_listener(figure)

    return figure
