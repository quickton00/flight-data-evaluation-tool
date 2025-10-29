"""
Flight data structuring and phase calculation module.

This module provides functions for processing and structuring flight data,
calculating approach phases, and transforming coordinate systems for flight
data analysis.
"""

import math
import pandas as pd
import numpy as np


def calculate_approach_phases(data_frame: pd.DataFrame) -> list:
    """
    Calculate the timestamps of different flight phases based on specific criteria.

    This function analyzes the flight data to determine when key flight phases
    occur, including alignment, approach, final approach, and docking phases.
    If certain phases cannot be calculated, backup values are generated.

    :param data_frame: DataFrame with all parsed values of the flight Log.
    :type data_frame: pd.DataFrame
    :return: List of timestamps marking the start of each flight phase:
            [checkout_to_alignment, alignment_to_approach, approach_to_final_approach, final_approach_to_docked]
    :rtype: list
    :raises IndexError: Handled internally; backup values are used when phase calculation fails.

    .. note::
       If controller input is not found, a backup value using the first timestamp is used.
       If the vessel is not docked, a backup value using the last timestamp is used.
       If intermediate phases cannot be calculated, the function calls
       :func:`_calculate_backup_approach_phases` to generate estimates.
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
    Calculate backup values for flight phases when automatic calculation fails.

    This function generates estimated timestamps for flight phases by interpolating
    between successfully calculated phases. The backup values can be manually
    adjusted in the program's GUI.

    :param data_frame: DataFrame with all parsed values of the flight Log.
    :type data_frame: pd.DataFrame
    :param phases: List of timestamps for different flight phases, where None indicates
                  a failed calculation that needs a backup value.
    :type phases: list
    :return: List of timestamps with backup values replacing None entries.
    :rtype: list

    .. note::
       Backup values are calculated by dividing the time range between successful
       phases into equal segments. Messages are printed to inform users when
       backup values are used.
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
    Calculate the angle between the spacecraft direction and the docking port.

    This function computes the angle between the direction vector of the spacecraft
    (from back to front) and the vector from the spacecraft's periscope to the origin
    (docking port location).

    :param front: Coordinates [x, y, z] of the front of the spacecraft.
    :type front: array-like
    :param back: Coordinates [x, y, z] of the back of the spacecraft.
    :type back: array-like
    :return: Angle in degrees between the direction vector and the vector to the
            docking port. Returns NaN if vectors cannot be normalized (zero length).
    :rtype: float

    .. note::
       The function returns NaN if either the direction vector or the vector to
       the origin has zero magnitude, preventing division by zero errors.
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
    Transform and structure raw flight data into an analysis-ready DataFrame.

    This function performs comprehensive data transformation including coordinate
    system conversion, additional metric calculations, and data preparation for
    flight analysis and visualization.

    :param data: Raw flight data as a list of lists or array-like structure.
    :type data: list of dict or array-like
    :param columns: Column names for the DataFrame corresponding to the data values.
    :type columns: list of str
    :return: Structured DataFrame with transformed coordinates and calculated metrics.
    :rtype: pandas.DataFrame

    The function performs the following transformations:

    1. **Coordinate System Transformation**: Converts from OrbVLCS to IssTPLCS
       coordinate system with appropriate axis swaps and sign inversions.

    2. **Additional Calculated Metrics**:
       - Lateral offset and velocity from the x-axis center of gravity (COG)
       - Ideal approach velocity based on distance from the docking port
       - Angle from vessel line of sight to ISS docking port
       - Approach cone boundaries for constraint visualization
       - Maximum allowed rotational angle during final approach
       - Maximum allowed rotational velocity during final approach

    .. note::
       The function handles a known naming bug in the logger by renaming
       'Rot. Rate.Z [deg/s]' to 'Rot. Rate.z [deg/s]'.
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

    # data set for ideal approach velocity
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

    # data set for the may allowed rotational velocity
    data_frame.loc[(data_frame["Port Pos.x [m]"] > 0) & (data_frame["COG Pos.x [m]"] < 20), "Max Rot Velocity"] = 0.15

    return data_frame
