import matplotlib as mpl
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
        "Rot. Rate.Z [deg/s]": "RHC.z",
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

    mpl.rcParams["path.simplify"] = True
    mpl.rcParams["path.simplify_threshold"] = 1.0

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
            flight_data[x_axis_type].tolist(),
            flight_data[corridor].tolist(),
            (flight_data[corridor] * -1).tolist(),
            color="#d3d3d3",
            label=corridor,
        )
        ax.legend(loc="upper right")

    return axvlines


def create_figure(data_frame, phases, total_flight_errors, x_axis_type):
    mpl.style.use("fast")

    figure = plt.figure(figsize=(24, 12))  # Set figure size (width, height)

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

    axvlines = {}
    for counter, title in enumerate(plots, 1):
        ax = figure.add_subplot(240 + counter)

        if x_axis_type == "SimTime":
            sub_axvlines = _plot_values(
                ax,
                data_frame,
                data_frame[x_axis_type],
                plots[title][0],
                title,
                "Simulation time (s)",
                plots[title][1],
                total_flight_errors,
                x_axis_type,
                plots[title][2],
                phases,
                corridor=plots[title][3],
            )
        elif x_axis_type == "COG Pos.x [m]":
            sub_axvlines = _plot_values(
                ax,
                data_frame,
                data_frame[x_axis_type],
                plots[title][0],
                title,
                "Axial distance Vessel Station [m]",
                plots[title][1],
                total_flight_errors,
                x_axis_type,
                plots[title][2],
                data_frame[data_frame["SimTime"].isin(phases)]["COG Pos.x [m]"].values,
                corridor=plots[title][3],
            )
        axvlines[ax] = sub_axvlines

    plt.subplots_adjust(left=0.04, right=0.99)

    return figure, axvlines
