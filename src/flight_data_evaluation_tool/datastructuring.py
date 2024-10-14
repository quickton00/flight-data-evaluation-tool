import math
import pandas as pd
import numpy as np


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
        phases.append(data_frame.iloc[0]["SimTime"])
        print(f"No Controller Input, check Log-File integrity, BACKUP value t={phases[-1]} is used.")

    # Alignment -> Approach phase
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
        phases.append(data_frame.iloc[-1]["SimTime"])
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
    """
    Calculate the angle between the direction vector from the back to the front of the spacecraft
    and the vector from the periscope of the spacecraft to the origin.
    Parameters:
    front (array-like): Coordinates of the front of the spacecraft.
    back (array-like): Coordinates of the back of the spacecraft.
    Returns:
    float: The angle in degrees between the direction vector and the vector to the origin.
           Returns NaN if the direction vector or the vector to the origin cannot be normalized.
    """
    # Calculate the direction vector from back to front
    direction_vector = np.array(front) - np.array(back)

    # Calculate the vector from the front of the spacecraft to the origin
    to_origin_vector = -np.array(front)

    # Normalize the vectors
    if np.linalg.norm(direction_vector) != 0:
        direction_unit_vector = direction_vector / np.linalg.norm(direction_vector)
    else:
        direction_unit_vector = np.array([np.nan, np.nan, np.nan])
    if np.linalg.norm(to_origin_vector) != 0:
        to_origin_unit_vector = to_origin_vector / np.linalg.norm(to_origin_vector)
    else:
        to_origin_unit_vector = np.array([np.nan, np.nan, np.nan])

    # Calculate the angle between the direction vector and the vector to the origin
    dot_product = np.dot(direction_unit_vector, to_origin_unit_vector)
    angle = np.arccos(dot_product) * (180 / np.pi)

    return angle


def structure_data(data, columns):
    """
    Transforms and structures flight data into a pandas DataFrame with additional calculated values.
    Args:
        data (list of dict): The raw flight data to be structured.
        columns (list of str): The column names for the DataFrame.
    Returns:
        pandas.DataFrame: The structured DataFrame with transformed coordinates and additional calculated values.
    The function performs the following operations:
    1. Converts the raw data into a pandas DataFrame with specified columns.
    2. Renames columns to handle naming inconsistencies.
    3. Transforms the coordinate system from OrbVLCS to IssTPLCS.
    4. Calculates additional value sets:
        - Lateral offset and velocity off COG Position from x-Axis.
        - Ideal approach velocity.
        - Angle from vessel line of sight to ISS-Port.
        - Approach cone for plotting.
        - Maximum allowed rotational angle.
        - Maximum allowed rotational velocity.
    """
    data_frame = pd.DataFrame(data, columns=columns)

    data_frame = data_frame.rename(
        columns={"Rot. Rate.Z [deg/s]": "Rot. Rate.z [deg/s]"}
    )  # handle naming bug in logger

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

    # angle from vessel line of sight to ISS-Port (3.471 is distance from port to periscope along flight direction)
    data_frame["Angle to Port"] = data_frame.apply(
        lambda row: angle_to_docking_port(
            [row["Port Pos.x [m]"] + 3.471, row["Port Pos.y [m]"], row["Port Pos.z [m]"]],
            [row["COG Pos.x [m]"] + 3.471, row["COG Pos.y [m]"], row["COG Pos.z [m]"]],
        ),
        axis=1,
    )

    # data set to draw approach cone in plots
    data_frame["Approach Cone"] = data_frame["COG Pos.x [m]"] * math.tan(10 * math.pi / 180)

    # data set fot the max allowed rotational angle
    data_frame.loc[(data_frame["Port Pos.x [m]"] > 0) & (data_frame["COG Pos.x [m]"] < 20), "Max Rot Angle"] = 1.5

    # data set for the may allowed rotaional velocity
    data_frame.loc[(data_frame["Port Pos.x [m]"] > 0) & (data_frame["COG Pos.x [m]"] < 20), "Max Rot Velocity"] = 0.15

    return data_frame
