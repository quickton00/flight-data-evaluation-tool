import math
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from evaluation import create_dataframe_template_from_yaml, evaluate_flight_phases


def plot_values(
    x_values: pd.DataFrame, y_values: pd.DataFrame, title: str, x_label: str, y_label: str, plot_names=None, phases=[]
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

    plt.figure(figsize=(20, 12))  # Set figure size (width, height)

    if isinstance(y_values, pd.DataFrame):
        for column_name, column_data in y_values.items():
            if plot_names is not None:
                column_name = plot_names[column_name]

            plt.plot(
                x_values.tolist(), column_data.tolist(), marker="", linestyle="-", linewidth=0.5, label=column_name
            )

    else:
        plt.plot(
            x_values.tolist(), y_values.tolist(), marker="", linestyle="-", linewidth=0.5, label=y_values.name
        )  # better without using pandas series

    for value in phases:
        if value is not None:
            plt.axvline(x=value, color="black", linestyle=":")

    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend(loc="upper right")
    plt.grid(linestyle="--", linewidth=0.5)


def calculate_approach_phases(data_frame: pd.DataFrame) -> list:
    """
    Function to calculate the timestamps of the different flight phases based on certain criteria's.

    :param data_frame: DataFrame with all parsed values of the flight Log.
    :type data_frame: pd.DataFrame
    :return: List of timestamps of the different flight phases.
    :rtype: list
    """

    phases = []

    # Checkout -> Alignment phase
    try:
        phases.append(
            data_frame[data_frame[["THC.x", "THC.y", "THC.z", "RHC.x", "RHC.y", "RHC.z"]].any(axis=1)].iloc[0][
                "SimTime"
            ]
        )
    except IndexError:
        phases.append(data_frame["SimTime"][0])
        print(f"No Controller Input, check Log-File integrity, BACKUP value t={phases[-1]} is used.")

    # Alignment -> Approach phase
    try:
        # strict criteria
        phases.append(
            data_frame[
                (
                    data_frame["Lateral Offset"] < data_frame["Approach Cone"] * 0.1
                )  # lateral offset max. 10% from x-Axes relative to approach cone diameter
                & (data_frame["Rot Angle.x [deg]"].abs() <= 1.5)  # angular pos within max angular deviation for docking
                & (data_frame["Rot Angle.y [deg]"].abs() <= 1.5)  # angular pos within max angular deviation for docking
                & (data_frame["Rot Angle.z [deg]"].abs() <= 1.5)  # angular pos within max angular deviation for docking
                & (data_frame["COG Vel.x [m]"] <= -0.1)  # alignment phase ends with acceleration towards station
                & (
                    data_frame["COG Vel.x [m]"] > data_frame["COG Vel.x [m]"].shift(-1)
                )  # velocity towards station has to increase
                & (data_frame["SimTime"] > phases[-1])
            ].iloc[0]["SimTime"]
        )  # alignment has to be after checkout

    except IndexError:
        # soft criteria
        try:
            phases.append(
                data_frame[
                    (data_frame["COG Vel.x [m]"] <= -0.1)  # alignment phase ends with acceleration towards station
                    & (
                        data_frame["COG Vel.x [m]"] > data_frame["COG Vel.x [m]"].shift(-1)
                    )  # velocity towards station has to increase
                    & (data_frame["SimTime"] > phases[-1])
                ].iloc[0]["SimTime"]
            )  # alignment has to be after checkout
            print("soft criteria between Alignment -> Approach phase is used")
        except IndexError:
            phases.append(None)

    # Approach -> Final Approach phase
    try:
        phases.append(data_frame[data_frame["COG Pos.x [m]"] < 20].iloc[0]["SimTime"])
    except IndexError:
        phases.append(None)

    # Final Approach -> Docked
    try:
        phases.append(data_frame[data_frame["Port Pos.x [m]"] == 0].iloc[0]["SimTime"])
    except IndexError:
        phases.append(data_frame["SimTime"][-1])
        print(f"Vessel not docked, BACKUP value t={phases[-1]} is used.")

    if None in phases:
        phases = _calculate_backup_approach_phases(data_frame, phases)

    return phases


def _calculate_backup_approach_phases(data_frame: pd.DataFrame, phases: list) -> list:
    """
    Function to calculate backup values for the different flight phases if they can't be calculated correctly.
    These Backup Values can then be manually adjusted in the programs GUI.

    :param data_frame: DataFrame with all parsed values of the flight Log.
    :type data_frame: pd.DataFrame
    :param phases: List of timestamps of the different flight phases with None where the previous calculation failed.
    :type phases: list
    :return: List of timestamps of the different flight phases with the now calculated backup values.
    :rtype: list
    """

    for index in range(len(phases) - 1):
        if phases[index] is None and phases[index + 1] is None:
            start_index = int(data_frame[data_frame["SimTime"] == phases[index - 1]].index[0])
            stop_index = int(data_frame[data_frame["SimTime"] == phases[index + 2]].index[0])

            phases[index] = data_frame.iloc[start_index + int((stop_index - start_index) * 1 / 3)]["SimTime"]
            phases[index + 1] = data_frame.iloc[start_index + int((stop_index - start_index) * 2 / 3)]["SimTime"]

            print(f"End of alignment phase could not be calculated, BACKUP value t={phases[index]} is used.")
            print(f"No Final Approach Phase, BACKUP value t={phases[index+1]} is used.")

            return phases
        elif phases[index] is None:
            start_index = data_frame[data_frame["SimTime"] == phases[index - 1]].index[0]
            stop_index = data_frame[data_frame["SimTime"] == phases[index + 1]].index[0]

            phases[index] = data_frame.iloc[start_index + int((stop_index - start_index) * 1 / 2)]["SimTime"]

            if index == 1:
                print(f"End of alignment phase could not be calculated, BACKUP value t={phases[index]} is used.")
            else:
                print(f"No Final Approach Phase, BACKUP value t={phases[index+1]} is used.")

            return phases
        else:
            continue

    return phases


def angle_to_docking_port(front, back):
    # Calculate the direction vector from back to front
    direction_vector = np.array(front) - np.array(back)

    # Calculate the vector from the front of the spacecraft to the origin
    to_origin_vector = -np.array(front)

    # Normalize the vectors
    direction_unit_vector = direction_vector / np.linalg.norm(direction_vector)
    to_origin_unit_vector = to_origin_vector / np.linalg.norm(to_origin_vector)

    # Calculate the angle between the direction vector and the vector to the origin
    dot_product = np.dot(direction_unit_vector, to_origin_unit_vector)
    angle = np.arccos(dot_product) * (180 / np.pi)

    return angle


if __name__ == "__main__":
    # Open the log file
    # with open(r"C:\Users\Admin\Downloads\SoyuzData\Data Flights\1st week ITA\FDL-2022-11-10-12-56-04_15Dima_ITA_0000.log", 'r') as file:
    with open(
        r"C:\Users\Admin\Desktop\flight_data_test\FDL-2024-05-15-07-07-23_Anton_B004FT-FT2-Anton-15_0000 - myTool.log",
        "r",
        encoding="utf-8",
    ) as file:
        # with open(r"C:\Users\Admin\Desktop\flight_data\FDL-2024-05-08-08-22-26_Anton_FT2-B001b-Anton_0000.log","r",encoding="utf-8",) as file:

        lines = file.readlines()

        data = []
        results = create_dataframe_template_from_yaml()

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

    data_frame = pd.DataFrame(data, columns=columns)

    # coordinate system transformation from OrbVLCS to IssTPLCS
    data_frame = data_frame.rename(columns={"THC.x": "THC.z", "THC.z": "THC.x", "RHC.x": "RHC.z", "RHC.z": "RHC.x"})
    data_frame["THC.x"] = data_frame["THC.x"] * -1
    data_frame["THC.z"] = data_frame["THC.z"] * -1

    # calculate additional value sets
    # lateral offset and velocity off COG Position from x-Axis
    data_frame["Lateral Offset"] = (data_frame["COG Pos.y [m]"] ** 2 + data_frame["COG Pos.z [m]"] ** 2) ** 0.5
    data_frame["Lateral Velocity"] = (data_frame["COG Vel.y [m]"] ** 2 + data_frame["COG Vel.z [m]"] ** 2) ** 0.5

    # data set for ideal aproach velocity
    data_frame["Ideal Approach Vel"] = -data_frame["COG Pos.x [m]"] / 200
    data_frame.loc[data_frame["COG Pos.x [m]"] < 20, "Ideal Approach Vel"] = -0.1

    # angle from vessel line of sight to ISS-Port
    data_frame["Angle to Port"] = data_frame.apply(
        lambda row: angle_to_docking_port(
            [row["Port Pos.x [m]"], row["Port Pos.y [m]"], row["Port Pos.z [m]"]],
            [row["COG Pos.x [m]"], row["COG Pos.y [m]"], row["COG Pos.z [m]"]],
        ),
        axis=1,
    )

    # data set to draw approach cone in plots
    data_frame["Approach Cone"] = data_frame["COG Pos.x [m]"] * math.tan(10 * math.pi / 180)

    # data set fot the max allowed rotational angle
    data_frame.loc[(data_frame["Port Pos.x [m]"] > 0) & (data_frame["COG Pos.x [m]"] < 20), "Max Rot Angle"] = 1.5

    # data set for the may allowed rotaional velocity
    data_frame.loc[(data_frame["Port Pos.x [m]"] > 0) & (data_frame["COG Pos.x [m]"] < 20), "Max Rot Velocity"] = 0.15

    # calculate diff flight phases

    phases = calculate_approach_phases(data_frame)

    evaluate_flight_phases(data_frame, phases, results)

    # plot translational offset (Port to Port)
    plot_values(
        data_frame["SimTime"],
        data_frame[["COG Pos.x [m]", "COG Pos.y [m]", "COG Pos.z [m]", "Lateral Offset"]],
        "Translational Offset Port-Vessel/Port-Station",
        "Simulation time (s)",
        "Translational Offset (m)",
        {
            "COG Pos.x [m]": "Trans. Offset X",
            "COG Pos.y [m]": "Trans. Offset Y",
            "COG Pos.z [m]": "Trans. Offset Z",
            "Lateral Offset": "Lateral Offset",
        },
        phases,
    )

    plt.fill_between(
        data_frame["SimTime"].tolist(),
        data_frame["Approach Cone"].tolist(),
        (data_frame["Approach Cone"] * -1).tolist(),
        color="#d3d3d3",
        label="Lateral Approach Cone",
    )
    plt.legend(loc="upper right")

    # plot translational velocity (CoG Vessel)
    plot_values(
        data_frame["SimTime"],
        data_frame[["COG Vel.x [m]", "COG Vel.y [m]", "COG Vel.z [m]", "Ideal Approach Vel"]],
        "Translational Velocity (CoG Vessel)",
        "Simulation time (s)",
        "Translational Velocity (m/s)",
        None,
        phases,
    )

    # plot rotaional angles
    plot_values(
        data_frame["SimTime"],
        data_frame[["Rot Angle.x [deg]", "Rot Angle.y [deg]", "Rot Angle.z [deg]"]],
        "Angular Position of the Vessel",
        "Simulation time (s)",
        "Rotational Angle (°)",
        {
            "Rot Angle.x [deg]": "Roll Position",
            "Rot Angle.y [deg]": "Yaw Position",
            "Rot Angle.z [deg]": "Pitch Position",
        },
        phases,
    )

    plt.fill_between(
        data_frame["SimTime"].tolist(),
        data_frame["Max Rot Angle"].tolist(),
        (data_frame["Max Rot Angle"] * -1).tolist(),
        color="#d3d3d3",
        label="Max Rotaional Angle",
    )
    plt.legend(loc="upper right")

    # plot rotational rates
    plot_values(
        data_frame["SimTime"],
        data_frame[["Rot. Rate.x [deg/s]", "Rot. Rate.y [deg/s]", "Rot. Rate.Z [deg/s]"]],
        "Rotation Velocities",
        "Simulation time (s)",
        "Rotational Rate (°/s)",
        {"Rot. Rate.x [deg/s]": "Roll Rate", "Rot. Rate.y [deg/s]": "Yaw Rate", "Rot. Rate.Z [deg/s]": "Pitch Rate"},
        phases,
    )

    plt.fill_between(
        data_frame["SimTime"].tolist(),
        data_frame["Max Rot Velocity"].tolist(),
        (data_frame["Max Rot Velocity"] * -1).tolist(),
        color="#d3d3d3",
        label="Max Rot Velocity",
    )
    plt.legend(loc="upper right")

    # plot translational controller inputs
    plot_values(
        data_frame["SimTime"],
        data_frame[["THC.x", "THC.y", "THC.z"]],
        "THC",
        "Simulation time (s)",
        "Translational Controller Inputs",
        None,
        phases,
    )

    # plot rotaional controller inputs
    plot_values(
        data_frame["SimTime"],
        data_frame[["RHC.x", "RHC.y", "RHC.z"]],
        "RHC",
        "Simulation time (s)",
        "Rotational Controller Inputs",
        None,
        phases,
    )

    # plot tank mass over time
    plot_values(
        data_frame["SimTime"],
        data_frame["Tank mass [kg]"],
        "Tank Mass over Simulation Time",
        "Simulation Time",
        "Tank Mass (kg)",
        None,
        phases,
    )

    # plot angles to port over time
    plot_values(
        data_frame["SimTime"],
        data_frame["Angle to Port"],
        "Angle to Port",
        "Simulation Time",
        "Angle",
        None,
        phases,
    )

    plt.show()  # Display the plot
