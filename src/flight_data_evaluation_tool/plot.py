import matplotlib.pyplot as plt
import pandas as pd


def _plot_values(
    ax,
    flight_data: pd.DataFrame,
    x_values: pd.DataFrame,
    y_values: pd.DataFrame,
    title: str,
    x_label: str,
    y_label: str,
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

    if isinstance(y_values, pd.DataFrame):
        for column_name, column_data in y_values.items():
            if plot_names is not None:
                column_name = plot_names[column_name]

            ax.plot(x_values.tolist(), column_data.tolist(), marker="", linestyle="-", linewidth=0.5, label=column_name)

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
            flight_data["SimTime"].tolist(),
            flight_data[corridor].tolist(),
            (flight_data[corridor] * -1).tolist(),
            color="#d3d3d3",
            label=corridor,
        )
        ax.legend(loc="upper right")

    return axvlines


def create_figure(data_frame, phases):
    figure = plt.figure(figsize=(24, 12))  # Set figure size (width, height)

    plots = {
        "Translational Offset Port-Vessel/Port-Station": [
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
            data_frame[["Rot. Rate.x [deg/s]", "Rot. Rate.y [deg/s]", "Rot. Rate.Z [deg/s]"]],
            "Rotational Rate (°/s)",
            {
                "Rot. Rate.x [deg/s]": "Roll Rate",
                "Rot. Rate.y [deg/s]": "Yaw Rate",
                "Rot. Rate.Z [deg/s]": "Pitch Rate",
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
        "Angle to Port": [
            data_frame["Angle to Port"],
            "Angle",
            None,
            None,
        ],
    }
    counter = 1

    axvlines = {}
    for title in plots:
        ax = figure.add_subplot(240 + counter)
        sub_axvlines = _plot_values(
            ax,
            data_frame,
            data_frame["SimTime"],
            plots[title][0],
            title,
            "Simulation time (s)",
            plots[title][1],
            plots[title][2],
            phases,
            corridor=plots[title][3],
        )
        axvlines[ax] = sub_axvlines
        counter += 1

    plt.subplots_adjust(left=0.04, right=0.99)

    return figure, axvlines
