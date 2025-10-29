"""
Flight data visualization and plotting module.

This module provides functions for creating matplotlib figures and heatmaps
from flight data, with responsive styling and interactive features. It includes
utilities for plotting time-series data, creating heatmaps of flight phases,
and applying dynamic styling based on figure size.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd


# Responsive styling helpers
def _compute_scale(fig, base_px=1600):
    """
    Compute a scaling factor for responsive font sizing based on figure dimensions.

    :param fig: The matplotlib figure object to compute scale for.
    :type fig: matplotlib.figure.Figure
    :param base_px: Base pixel width for scale calculation, defaults to 1600.
    :type base_px: int, optional
    :return: Scaling factor clamped between 0.75 and 1.6.
    :rtype: float
    """
    w, h = fig.get_size_inches()
    px_w = 2 * h * fig.get_dpi()
    # Clamp scale to reasonable bounds
    return max(0.75, min(1.6, px_w / base_px))


def _apply_responsive_styling(fig):
    """
    Apply responsive font sizing to all elements of a matplotlib figure.

    This function adjusts title, label, tick, and legend font sizes based on
    the computed scale factor to ensure readability across different figure sizes.

    :param fig: The matplotlib figure to apply styling to.
    :type fig: matplotlib.figure.Figure

    .. note::
       Font sizes are calculated based on the figure's scale factor and applied
       to all axes in the figure.
    """
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
    """
    Attach a resize event listener to dynamically update styling on figure resize.

    :param fig: The matplotlib figure to attach the listener to.
    :type fig: matplotlib.figure.Figure

    .. note::
       The listener automatically calls :func:`_apply_responsive_styling` whenever
       the figure is resized, ensuring consistent appearance across different window sizes.
    """

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
    Plot x-values against y-values on a given matplotlib axis with error markers.

    This function creates line plots for flight data metrics, with support for
    multiple data series, phase markers, corridors, and error highlighting.

    :param ax: The matplotlib axis to plot on.
    :type ax: matplotlib.axes.Axes
    :param flight_data: Complete flight data DataFrame for error lookups.
    :type flight_data: pd.DataFrame
    :param x_values: Values for the x-axis (time or distance).
    :type x_values: pd.DataFrame
    :param y_values: Values for the y-axis. Can be a single Series or DataFrame
                    with multiple columns (each column becomes a separate curve).
    :type y_values: pd.DataFrame or pd.Series
    :param title: Title for the plot.
    :type title: str
    :param x_label: Label for the x-axis.
    :type x_label: str
    :param y_label: Label for the y-axis.
    :type y_label: str
    :param total_flight_errors: Dictionary mapping controller axes to lists of
                               error timestamps.
    :type total_flight_errors: dict
    :param x_axis_type: Type of x-axis data ('SimTime' or 'COG Pos.x [m]').
    :type x_axis_type: str
    :param plot_names: Optional dictionary to rename plot labels, defaults to None.
    :type plot_names: dict, optional
    :param phases: List of phase timestamps to mark with vertical lines, defaults to [].
    :type phases: list, optional
    :param corridor: Name of column to use for corridor bounds, defaults to None.
    :type corridor: str, optional
    :return: List of vertical line artists marking phase boundaries.
    :rtype: list

    .. note::
       Flight errors are marked with red scatter points on the corresponding plots.
       The error_assignment dictionary maps data columns to their corresponding
       controller inputs.
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
    Create a comprehensive matplotlib figure with multiple subplots for flight data.

    This function generates an 8-subplot figure containing various flight metrics
    including translational offsets, velocities, angular positions, rotations,
    controller inputs, tank mass, and angle to docking port.

    :param data_frame: The flight data containing all metrics and measurements.
    :type data_frame: pd.DataFrame
    :param phases: List of phase times or positions to mark on the x-axis with
                  vertical lines.
    :type phases: list
    :param total_flight_errors: Dictionary mapping controller axes to lists of
                               error timestamps for error visualization.
    :type total_flight_errors: dict
    :param x_axis_type: Type of x-axis to use - either 'SimTime' for time-based
                       or 'COG Pos.x [m]' for distance-based plotting.
    :type x_axis_type: str
    :return: Tuple containing the created figure and a dictionary mapping each
            axis to its vertical phase line artists.
    :rtype: tuple(matplotlib.figure.Figure, dict)

    .. note::
       The function uses constrained layout for automatic spacing and applies
       responsive styling that adapts to figure size changes. Phase lines can
       be toggled on/off in the GUI.
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
    Create heatmaps showing lateral flight path for different flight phases.

    This function generates a 4-subplot figure displaying the vessel's lateral
    position (y-z plane) during each phase of flight, along with approach cone
    boundaries at phase start and end points.

    :param flight_data: DataFrame containing flight data with columns 'SimTime',
                       'Approach Cone', 'COG Pos.z [m]', and 'COG Pos.y [m]'.
    :type flight_data: pd.DataFrame
    :param phases: List of phase start times. The last element represents the
                  end time of the last phase.
    :type phases: list
    :return: The generated matplotlib figure containing the heatmaps.
    :rtype: matplotlib.figure.Figure

    .. note::
       - Green markers and circles indicate phase start positions
       - Red markers and circles indicate phase end positions
       - Grey scatter points show the full trajectory
       - Approach cone circles show the allowed lateral deviation boundaries
       - Axes are centered at origin with equal scaling for accurate representation
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
