# methods to create the data points for evaluation

import os
import sys
import json
import pandas as pd
import numpy as np


def create_dataframe_template_from_json(template_file=r"src\flight_data_evaluation_tool\results_template.json"):
    """
    Creates a pandas DataFrame template based on the structure defined in a json file.
    Args:
        template_file (str): Path to the json file containing the DataFrame template configuration.
                         Defaults to "src\\flight_data_evaluation_tool\\results_template.json".
    Returns:
        pd.DataFrame: An empty DataFrame with columns and data types defined in the json file.
    """
    if getattr(sys, "frozen", False):  # Check if running in a PyInstaller bundle
        template_file = sys._MEIPASS  # type: ignore
        template_file = os.path.join(template_file, "results_template.json")

    with open(template_file, "r") as f:
        config = json.load(f)

    # Extract columns from the loaded json
    columns = config["columns"].keys()

    # Create an empty DataFrame with defined columns and data types
    df_template = pd.DataFrame(columns=columns, index=[0])

    return df_template


def start_stop_condition_evaluation(
    flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps, controller=""
):
    """
    Evaluates the start and stop conditions for flight data and returns the corresponding timestamps.
    The calculated timestamps are used to determine the length between two corresponding conditions.
    Parameters:
    flight_data (DataFrame): A data frame containing the flight data.
    start_condition (str): The condition to determine the start of the steering.
    stop_condition (str): The condition to determine the stop of the steering.
    start_index (int): The index in flight_phase_timestamps to use if start timestamps of flight phases are missing.
    stop_index (int): The index in flight_phase_timestamps to use if stop timestamps of flight phases are missing.
    flight_phase_timestamps (list): A list of timestamps of the flight phases.
    controller (str, optional): The name of the controller for logging purposes. Defaults to "".
    Returns:
    tuple: A tuple containing two lists:
        - start_steering_timestamps (list): Timestamps where steering starts.
        - stop_steering_timestamps (list): Timestamps where steering stops.
    Notes:
    - If the number of start timestamps is less than the number of stop timestamps, the start timestamp list is corrected by inserting a timestamp from flight_phase_timestamps.
    - If the number of start timestamps is greater than the number of stop timestamps, the stop timestamp list is corrected by appending a timestamp from flight_phase_timestamps.
    - If the number of start and stop timestamps still do not match, backup values for stop timestamps are calculated.
    """
    start_steering_timestamps = []
    stop_steering_timestamps = []

    # calculate timestamps where steering starts
    start_steering_timestamps = flight_data[start_condition]["SimTime"].to_list()

    # calculate timestamps where steering stops
    stop_steering_timestamps = flight_data[stop_condition]["SimTime"].to_list()

    # correct missing timestamps due to individual phase calculation
    if len(start_steering_timestamps) < len(stop_steering_timestamps):
        start_steering_timestamps.insert(0, flight_phase_timestamps[start_index])
    if len(start_steering_timestamps) > len(stop_steering_timestamps):
        stop_steering_timestamps.append(flight_phase_timestamps[stop_index])

    if len(stop_steering_timestamps) != len(start_steering_timestamps):
        print(
            f"{controller}: Different number of start ({len(start_steering_timestamps)})/stop ({len(stop_steering_timestamps)}) timestamps found. Check your start/stop condition"
        )
        print("Backup values for stop timestamps are calculated for 'Fuel on Error' value.")
        flight_data["Shifted_SimTime"] = flight_data["SimTime"].shift(-1)
        filtered_data = flight_data[flight_data["SimTime"].isin(start_steering_timestamps)]
        stop_steering_timestamps = filtered_data["Shifted_SimTime"].to_list()

    return (start_steering_timestamps, stop_steering_timestamps)


def export_data(results: pd.DataFrame, flight_data: pd.DataFrame):
    """
    Exports flight data to a CSV file.

    Parameters:
    flight_data (DataFrame): The flight data to be exported.
    save_path (str): The file path where the CSV file will be saved.
    overwrite (bool, optional): Whether to overwrite the existing file. Default is True.

    Returns:
    None
    """

    # TODO disable function and button for exe

    try:
        results = results.copy().drop(columns=["Logger Version", "Session ID", "Pilot"])
    except KeyError:
        pass

    json_file_path = "src/flight_data_evaluation_tool/flight_data.json"

    if os.path.exists(json_file_path):
        existing_data = pd.read_json(json_file_path, orient="records", lines=True, convert_dates=False)
        updated_data = pd.concat([existing_data, results], ignore_index=True).drop_duplicates(
            subset="Flight ID", keep="last", ignore_index=True
        )
    else:
        updated_data = results

    updated_data = updated_data.dropna(axis="columns", how="all")

    flight_data.to_csv(f"data/{results['Flight ID'][0]}.csv", index=False)

    # Save the updated data back to the JSON file
    updated_data.to_json(json_file_path, orient="records", lines=True, index=False)


def calculate_phase_evaluation_values(flight_data, phase, start_index, stop_index, flight_phase_timestamps, results):
    """
    Calculate various evaluation metrics for a specific flight phase or the total flight.
    Parameters:
    -----------
    flight_data : pandas.DataFrame
        DataFrame containing flight data with columns such as "SimTime", "Lateral Offset", "Approach Cone",
        "Tank mass [kg]", "Angle to Port", "THC.x", "THC.y", "THC.z", "RHC.x", "RHC.y", "RHC.z", "COG Vel.x [m]",
        "Ideal Approach Vel", "COG Pos.x [m]", "COG Pos.y [m]", "COG Pos.z [m]", "Rot Angle.x [deg]",
        "Rot Angle.y [deg]", "Rot Angle.z [deg]", "Rot. Rate.x [deg/s]", "Rot. Rate.y [deg/s]", "Rot. Rate.z [deg/s]".
    phase : str
        The flight phase for which the evaluation metrics are being calculated.
    start_index : int
        The index in flight_phase_timestamps indicating the start of the phase.
    stop_index : int
        The index in flight_phase_timestamps indicating the end of the phase.
    flight_phase_timestamps : list
        List of timestamps corresponding to different phases of the flight.
    results : pandas.DataFrame
        DataFrame to store the calculated evaluation metrics.
    Returns:
    --------
    total_flight_errors : dict
        Dictionary containing lists of timestamps where errors occurred for the "Total" phase. Keys are
        "{controller}.{coordinate}" and values are lists of timestamps.
    """
    total_flight_errors = {}

    # Calculation for "Start_{phase}"
    if f"Start_{phase}" in results.columns:
        results[f"Start_{phase}"] = flight_phase_timestamps[start_index]

    # calculation for "Duration_{phase}"
    if f"Duration_{phase}" in results.columns:
        results[f"Duration_{phase}"] = flight_phase_timestamps[stop_index] - flight_phase_timestamps[start_index]

    # calculation for "OutOfCone_{phase}"
    if f"OutOfCone_{phase}" in results.columns:
        start_condition = (
            (flight_data["Lateral Offset"] > flight_data["Approach Cone"])
            & (
                (
                    flight_data["Lateral Offset"].shift(periods=1, fill_value=0)
                    <= flight_data["Approach Cone"].shift(periods=1, fill_value=0)
                )
                | (flight_data["SimTime"] == flight_phase_timestamps[start_index])
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        stop_condition = (
            (flight_data["Lateral Offset"] <= flight_data["Approach Cone"])
            & (
                (
                    flight_data["Lateral Offset"].shift(periods=1, fill_value=0)
                    > flight_data["Approach Cone"].shift(periods=1, fill_value=0)
                )
                | (flight_data["SimTime"] == flight_phase_timestamps[stop_index])
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        (start_steering_timestamps, stop_steering_timestamps) = start_stop_condition_evaluation(
            flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
        )

        results[f"OutOfCone_{phase}"] = sum(
            [stop_steering_timestamps[i] - start_steering_timestamps[i] for i in range(len(start_steering_timestamps))]
        )

    # calculation for "AboveClosingVel_{phase}"
    if f"AboveClosingVel_{phase}" in results.columns:
        start_condition = (
            (flight_data["COG Vel.x [m]"] < flight_data["Ideal Approach Vel"])
            & (
                (
                    flight_data["COG Vel.x [m]"].shift(periods=1, fill_value=0)
                    >= flight_data["Ideal Approach Vel"].shift(periods=1, fill_value=0)
                )
                | (flight_data["SimTime"] == flight_phase_timestamps[start_index])
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        stop_condition = (
            (flight_data["COG Vel.x [m]"] >= flight_data["Ideal Approach Vel"])
            & (
                (
                    flight_data["COG Vel.x [m]"].shift(periods=1, fill_value=0)
                    < flight_data["Ideal Approach Vel"].shift(periods=1, fill_value=0)
                )
                | (flight_data["SimTime"] == flight_phase_timestamps[stop_index])
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        (start_steering_timestamps, stop_steering_timestamps) = start_stop_condition_evaluation(
            flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
        )

        results[f"AboveClosingVel_{phase}"] = sum(
            [stop_steering_timestamps[i] - start_steering_timestamps[i] for i in range(len(start_steering_timestamps))]
        )

    # calculation for "Fuel_{phase}"
    if f"Fuel_{phase}" in results.columns:
        results[f"Fuel_{phase}"] = (
            flight_data[flight_data["SimTime"] == flight_phase_timestamps[start_index]].iloc[0]["Tank mass [kg]"]
            - flight_data[flight_data["SimTime"] == flight_phase_timestamps[stop_index]].iloc[0]["Tank mass [kg]"]
        )

    # Calculation for "LatOffsetAtStart_{phase}"
    if f"LatOffsetAtStart_{phase}" in results.columns:
        results[f"LatOffsetAtStart_{phase}"] = flight_data[
            flight_data["SimTime"] == flight_phase_timestamps[start_index]
        ].iloc[0]["Lateral Offset"]

    # calculation for "NoVisTime_{phase}"
    start_condition = (
        (flight_data["Angle to Port"] > 7.5)
        & (
            (flight_data["Angle to Port"].shift(periods=1, fill_value=0) <= 7.5)
            | (flight_data["SimTime"] == flight_phase_timestamps[start_index])
        )
    ) & (
        (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
        & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
    )

    stop_condition = (
        (flight_data["Angle to Port"] <= 7.5)
        & (
            (flight_data["Angle to Port"].shift(periods=1, fill_value=0) > 7.5)
            | (flight_data["SimTime"] == flight_phase_timestamps[stop_index])
        )
    ) & (
        (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
        & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
    )

    (start_steering_timestamps, stop_steering_timestamps) = start_stop_condition_evaluation(
        flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
    )

    results[f"NoVisTime_{phase}"] = sum(
        [stop_steering_timestamps[i] - start_steering_timestamps[i] for i in range(len(start_steering_timestamps))]
    )

    # calculation for "{controller}{coordinate}_{phase}" and "{controller}{coordinate}AvgTime_{phase}"
    for controller in ["THC", "RHC"]:
        for coordinate in ["x", "y", "z"]:
            if f"{controller}.{coordinate}_{phase}" not in results.columns:
                continue

            start_condition = (
                (flight_data[f"{controller}.{coordinate}"] != 0)
                & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
            ) & (
                (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
                & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
            )

            stop_condition = (
                (flight_data[f"{controller}.{coordinate}"] == 0)
                & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) != 0)
            ) & (
                (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
                & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
            )

            # calculation for "{controller}{coordinate}_{phase}"
            results[f"{controller}{coordinate}_{phase}"] = (start_condition).sum()

            # calculation for "{controller}{coordinate}AvgTime_{phase}"
            (start_steering_timestamps, stop_steering_timestamps) = start_stop_condition_evaluation(
                flight_data,
                start_condition,
                stop_condition,
                start_index,
                stop_index,
                flight_phase_timestamps,
            )

            if len(start_steering_timestamps) != 0:
                results[f"{controller}{coordinate}AvgTime_{phase}"] = np.mean(
                    [
                        stop_steering_timestamps[i] - start_steering_timestamps[i]
                        for i in range(len(start_steering_timestamps))
                    ]
                )
            else:
                results[f"{controller}{coordinate}AvgTime_{phase}"] = 0

    # calculation for "THCxErr_{phase}" and "THCxIndErr_{phase}"
    flight_errors = flight_data[
        (
            (
                # Further Acceleration despite being already above Ideal Approach Velocity towards station
                (flight_data["COG Vel.x [m]"] < flight_data["Ideal Approach Vel"])
                & (flight_data["THC.x"] < 0)
                & (flight_data["THC.x"].shift(periods=1, fill_value=0) == 0)
            )
            | (
                # Acceleration above ideal Approach Velocity towards station
                (flight_data["COG Vel.x [m]"] < flight_data["Ideal Approach Vel"])
                & (flight_data["THC.x"] < 0)
                & (
                    flight_data["COG Vel.x [m]"].shift(periods=1, fill_value=0)
                    >= flight_data["Ideal Approach Vel"].shift(periods=1, fill_value=0)
                )
            )
            | (
                # Acceleration away from the station
                (flight_data["COG Vel.x [m]"] > 0)
                & (flight_data["THC.x"] > 0)
                & (flight_data["THC.x"].shift(periods=1, fill_value=0) == 0)
            )
        )
        & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )
    ]

    results[f"THCxErr_{phase}"] = len(flight_errors)

    if phase == "Total":
        total_flight_errors["THC.x"] = flight_errors["SimTime"].to_list()

    # calculation for "THCxIndErr_{phase}"
    if f"THCxIndErr_{phase}" in results.columns:
        results[f"THCxIndErr_{phase}"] = len(flight_errors[flight_errors[["THC.y", "THC.z"]].any(axis=1)])

    # calculation for "{controller}{coordinate}Err_{phase}" and "{controller}{coordinate}IndErr_{phase}" except THC.x
    for coordinate in ["x", "y", "z"]:
        for controller, value_name in {
            "THC": f"COG Pos.{coordinate} [m]",
            "RHC": f"Rot Angle.{coordinate} [deg]",
        }.items():
            if controller == "THC" and coordinate == "x":
                # see previous calculations
                continue
            if controller == "RHC":
                start_condition = (
                    (
                        # leaving zero offset with maneuver
                        (flight_data[value_name] == 0)
                        & (flight_data[f"{controller}.{coordinate}"] != 0)
                    )
                    | (
                        # increasing offset with maneuver positive direction
                        (flight_data[value_name] > 0)
                        & (flight_data[f"{controller}.{coordinate}"] > 0)
                        # & (flight_data[f"Rot. Rate.{coordinate} [deg/s]"] >= 0)       #consider usage analog to THC, but then change also stop condition
                        & (
                            (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
                            | (flight_data[value_name].shift(periods=1, fill_value=0) <= 0)
                        )
                    )
                    | (
                        # increasing offset with maneuver negative direction
                        (flight_data[value_name] < 0)
                        & (flight_data[f"{controller}.{coordinate}"] < 0)
                        # & (flight_data[f"Rot. Rate.{coordinate} [deg/s]"] <= 0)       #consider usage analog to THC, but then change also stop condition
                        & (
                            (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
                            | (flight_data[value_name].shift(periods=1, fill_value=0) >= 0)
                        )
                    )
                ) & (
                    (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
                    & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
                )

                stop_condition = (
                    (
                        (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) != 0)
                        & (flight_data[value_name].shift(periods=1, fill_value=0) == 0)
                    )
                    | (
                        (flight_data[value_name] > 0)
                        & (flight_data[f"{controller}.{coordinate}"] <= 0)
                        & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) > 0)
                        & (flight_data[value_name].shift(periods=1, fill_value=0) > 0)
                    )
                    | (
                        (flight_data[value_name] < 0)
                        & (flight_data[f"{controller}.{coordinate}"] >= 0)
                        & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) < 0)
                        & (flight_data[value_name].shift(periods=1, fill_value=0) < 0)
                    )
                ) & (
                    (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
                    & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
                )
            elif controller == "THC":
                start_condition = (
                    (
                        # leaving zero offset with maneuver
                        (flight_data[value_name] == 0)
                        & (flight_data[f"{controller}.{coordinate}"] != 0)
                    )
                    | (
                        # increasing offset with maneuver positive direction
                        # breaking (decreasing velocity in the current direction) is not considered as error
                        (flight_data[value_name] > 0)
                        & (flight_data[f"{controller}.{coordinate}"] > 0)
                        & (flight_data[f"COG Vel.{coordinate} [m]"] >= 0)
                        & (
                            (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
                            | (flight_data[value_name].shift(periods=1, fill_value=0) <= 0)
                            | (flight_data[f"COG Vel.{coordinate} [m]"].shift(periods=1, fill_value=0) < 0)
                        )
                    )
                    | (
                        # increasing offset with maneuver negative direction
                        # breaking (decreasing velocity in the current direction) is not considered as error
                        (flight_data[value_name] < 0)
                        & (flight_data[f"{controller}.{coordinate}"] < 0)
                        & (flight_data[f"COG Vel.{coordinate} [m]"] <= 0)
                        & (
                            (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
                            | (flight_data[value_name].shift(periods=1, fill_value=0) >= 0)
                            | (flight_data[f"COG Vel.{coordinate} [m]"].shift(periods=1, fill_value=0) > 0)
                        )
                    )
                ) & (
                    (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
                    & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
                )

                stop_condition = (
                    (
                        (flight_data[value_name] != 0)
                        & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) != 0)
                        & (flight_data[value_name].shift(periods=1, fill_value=0) == 0)
                    )
                    | (
                        (flight_data[value_name] > 0)
                        & (flight_data[f"{controller}.{coordinate}"] <= 0)
                        & (flight_data[f"COG Vel.{coordinate} [m]"] >= 0)
                        & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) > 0)
                        & (flight_data[value_name].shift(periods=1, fill_value=0) > 0)
                        & (flight_data[f"COG Vel.{coordinate} [m]"].shift(periods=1, fill_value=0) >= 0)
                    )
                    | (
                        (flight_data[value_name] < 0)
                        & (flight_data[f"{controller}.{coordinate}"] >= 0)
                        & (flight_data[f"COG Vel.{coordinate} [m]"] <= 0)
                        & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) < 0)
                        & (flight_data[value_name].shift(periods=1, fill_value=0) < 0)
                        & (flight_data[f"COG Vel.{coordinate} [m]"].shift(periods=1, fill_value=0) <= 0)
                    )
                ) & (
                    (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
                    & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
                )

            flight_errors = flight_data[start_condition]

            if phase == "Total":
                total_flight_errors[f"{controller}.{coordinate}"] = flight_errors["SimTime"].to_list()

            # calculation for "{controller}{coordinate}Err_{phase}"
            results[f"{controller}{coordinate}Err_{phase}"] = len(flight_errors)

            # calculation for "{controller}{coordinate}IndErr_{phase}"
            if f"{controller}{coordinate}IndErr_{phase}" in results.columns:
                if controller == "THC":
                    other_controller_axis = ["THC.y", "THC.z"]
                else:
                    other_controller_axis = ["RHC.x", "RHC.y", "RHC.z"]

                other_controller_axis.remove(f"{controller}.{coordinate}")

                results[f"{controller}{coordinate}IndErr_{phase}"] = len(
                    flight_errors[flight_errors[other_controller_axis].any(axis=1)]
                )

            # calculation for "Fuel_on_Error", could be changed to be phase specific
            # stop conditions not perfect for RHC (Rework possible, see als start_stop_condition_evaluation())
            if f"Fuel_on_Error_{phase}" in results.columns:
                (start_steering_timestamps, stop_steering_timestamps) = start_stop_condition_evaluation(
                    flight_data,
                    start_condition,
                    stop_condition,
                    start_index,
                    stop_index,
                    flight_phase_timestamps,
                    f"{controller}.{coordinate}",
                )

                results[f"Fuel_on_Error_{phase}"] = results[f"Fuel_on_Error_{phase}"] + sum(
                    [
                        flight_data[flight_data["SimTime"] == start_steering_timestamps[i]].iloc[0]["Tank mass [kg]"]
                        - flight_data[flight_data["SimTime"] == stop_steering_timestamps[i]].iloc[0]["Tank mass [kg]"]
                        for i in range(len(start_steering_timestamps))
                    ]
                )

    # calculation for "CombJoy_{phase}" and "CombJoyTime_{phase}"
    if f"CombJoy_{phase}" and "CombJoyTime_{phase}" in results.columns:
        start_condition = (
            (
                flight_data[["THC.x", "THC.y", "THC.z"]].any(axis=1)
                & flight_data[["RHC.x", "RHC.y", "RHC.z"]].any(axis=1)
            )
            & (
                (flight_data[["THC.x", "THC.y", "THC.z"]].shift(periods=1, fill_value=0) == 0).all(axis=1)
                | (flight_data[["RHC.x", "RHC.y", "RHC.z"]].shift(periods=1, fill_value=0) == 0).all(axis=1)
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        stop_condition = (
            (
                (flight_data[["THC.x", "THC.y", "THC.z"]] == 0).all(axis=1)
                | (flight_data[["RHC.x", "RHC.y", "RHC.z"]] == 0).all(axis=1)
            )
            & (
                flight_data[["THC.x", "THC.y", "THC.z"]].shift(periods=1, fill_value=0).any(axis=1)
                & flight_data[["RHC.x", "RHC.y", "RHC.z"]].shift(periods=1, fill_value=0).any(axis=1)
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        # calculation for "CombJoy_{phase}"
        results[f"CombJoy_{phase}"] = (start_condition).sum()

        # calculation for "CombJoyTime_{phase}"
        (start_steering_timestamps, stop_steering_timestamps) = start_stop_condition_evaluation(
            flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
        )

        results[f"CombJoyTime_{phase}"] = sum(
            [stop_steering_timestamps[i] - start_steering_timestamps[i] for i in range(len(start_steering_timestamps))]
        )

    # calculation for "CombJoy{controller}yz_{phase}" and "CombJoy{controller}yzTime_{phase}"
    for controller in ["THC", "RHC"]:
        if f"CombJoy{controller}yz_{phase}" or "CombJoy{controller}yzTime_{phase}" not in results.columns:
            continue

        start_condition = (
            ((flight_data[f"{controller}.y"] != 0) & (flight_data[f"{controller}.z"] != 0))
            & (
                (flight_data[f"{controller}.y"].shift(periods=1, fill_value=0) == 0)
                | (flight_data[f"{controller}.z"].shift(periods=1, fill_value=0) == 0)
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        stop_condition = (
            ((flight_data[f"{controller}.y"] == 0) | (flight_data[f"{controller}.z"] == 0))
            & (
                (flight_data[f"{controller}.y"].shift(periods=1, fill_value=0) != 0)
                & (flight_data[f"{controller}.z"].shift(periods=1, fill_value=0) != 0)
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        # calculation for "CombJoy{controller}yz_{phase}"
        results[f"CombJoy{controller}yz_{phase}"] = (start_condition).sum()

        # calculation for "CombJoy{controller}yzTime_{phase}"
        (start_steering_timestamps, stop_steering_timestamps) = start_stop_condition_evaluation(
            flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
        )

        results[f"CombJoy{controller}yzTime_{phase}"] = sum(
            [stop_steering_timestamps[i] - start_steering_timestamps[i] for i in range(len(start_steering_timestamps))]
        )

    # calculation for "CombJoy{controller}xyz_{phase}" and "CombJoy{controller}xyzTime_{phase}"
    for controller in ["THC", "RHC"]:
        if f"CombJoy{controller}xyz_{phase}" or "CombJoy{controller}xyzTime_{phase}" not in results.columns:
            continue

        start_condition = (
            (flight_data[[f"{controller}.y", f"{controller}.z"]].any(axis=1) & (flight_data[f"{controller}.x"] != 0))
            & (
                (flight_data[f"{controller}.x"].shift(periods=1, fill_value=0) == 0)
                | (flight_data[[f"{controller}.y", f"{controller}.z"]].shift(periods=1, fill_value=0) == 0).all(axis=1)
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        stop_condition = (
            (
                (flight_data[f"{controller}.x"] == 0)
                | (flight_data[[f"{controller}.y", f"{controller}.z"]] == 0).all(axis=1)
            )
            & (
                flight_data[[f"{controller}.y", f"{controller}.z"]].shift(periods=1, fill_value=0).any(axis=1)
                & (flight_data[f"{controller}.x"].shift(periods=1, fill_value=0) != 0)
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        # calculation for "CombJoy{controller}xyz_{phase}"
        results[f"CombJoy{controller}xyz_{phase}"] = (start_condition).sum()

        # calculation for "CombJoy{controller}xyzTime_{phase}"
        (start_steering_timestamps, stop_steering_timestamps) = start_stop_condition_evaluation(
            flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
        )

        results[f"CombJoy{controller}xyzTime_{phase}"] = sum(
            [stop_steering_timestamps[i] - start_steering_timestamps[i] for i in range(len(start_steering_timestamps))]
        )

    # calculation for PSD values for {controller}.{coordinate}_{phase}
    for controller in ["THC", "RHC"]:
        for coordinate in ["x", "y", "z"]:

            filtered_flight_data = flight_data[
                (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
                & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
            ]

            N = len(filtered_flight_data)
            yf = np.fft.fft(filtered_flight_data[f"{controller}.{coordinate}"])
            psd = np.abs(yf) ** 2 / N

            results[f"{controller}{coordinate}PSD_{phase}"] = np.mean(psd)

    # calculation for Average and rms values
    for result_name, column_name in {
        "LatOff": "Lateral Offset",
        "ApprVel": "COG Vel.x [m]",
        "LatVel": "Lateral Velocity",
        "Roll": "Rot Angle.x [deg]",
        "Yaw": "Rot Angle.y [deg]",
        "Pitch": "Rot Angle.z [deg]",
        "RollRate": "Rot. Rate.x [deg/s]",
        "YawRate": "Rot. Rate.y [deg/s]",
        "PitchRate": "Rot. Rate.z [deg/s]",
    }.items():
        filtered_flight_data = flight_data[
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        ]

        if f"{result_name}Avg_{phase}" in results.columns:
            results[f"{result_name}Avg_{phase}"] = filtered_flight_data[column_name].mean()

        if f"{result_name}Rms_{phase}" in results.columns:
            results[f"{result_name}Rms_{phase}"] = (filtered_flight_data[column_name] ** 2).mean() ** 0.5

    return total_flight_errors


def evaluate_flight_phases(flight_data, flight_phase_timestamps, results):
    """
    Evaluates different phases of a flight based on provided flight data and timestamps, and updates the results dictionary.
    Args:
        flight_data (DataFrame): The flight data containing various parameters recorded during the flight.
        flight_phase_timestamps (list): A list of timestamps indicating the start and end of different flight phases.
        results (dict): A dictionary to store the evaluation results.
        save_dir (str): The directory where the evaluation results will be saved.
        overwrite (bool, optional): Flag indicating whether to overwrite existing results file. Defaults to True.
    Returns:
        None
    """
    start_index = 0
    stop_index = 1

    for phase in ["Align", "Appr", "FA", "Total"]:
        calculate_phase_evaluation_values(flight_data, phase, start_index, stop_index, flight_phase_timestamps, results)

        if phase != "FA":
            start_index += 1
            stop_index += 1
        else:
            start_index = 0

    # calculate exceptions
    results["Time_Dock"] = flight_phase_timestamps[3]
    results["LatOffsetAt_Dock"] = flight_data[flight_data["SimTime"] == flight_phase_timestamps[3]].iloc[0][
        "Lateral Offset"
    ]

    export_data(results, flight_data)
