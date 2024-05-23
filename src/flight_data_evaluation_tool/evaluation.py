# methods to create the datapoints for evaluation

import pandas as pd
import yaml
import numpy as np


def create_dataframe_template_from_yaml(yaml_file=r"src\flight_data_evaluation_tool\results_template.yaml"):
    with open(yaml_file, "r") as f:
        config = yaml.safe_load(f)

    # Extract columns from the loaded YAML
    columns = config["columns"]

    # Create an empty DataFrame with defined columns and data types
    df_template = pd.DataFrame(columns=columns, index=[0])

    return df_template


def calculate_steering_start_stop(
    flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
):
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

    return (start_steering_timestamps, stop_steering_timestamps)


def export_data(flight_data, save_path):
    flight_data.transpose().to_csv(save_path, sep="\t", index=True)
    # flight_data.to_csv(save_path, sep=";", index=False, na_rep="NI")


def calculate_phase_evaluation_values(flight_data, phase, start_index, stop_index, flight_phase_timestamps, results):
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
                flight_data["Lateral Offset"].shift(periods=1, fill_value=0)
                <= flight_data["Approach Cone"].shift(periods=1, fill_value=0)
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        stop_condition = (
            (flight_data["Lateral Offset"] <= flight_data["Approach Cone"])
            & (
                flight_data["Lateral Offset"].shift(periods=1, fill_value=0)
                > flight_data["Approach Cone"].shift(periods=1, fill_value=0)
            )
        ) & (
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        )

        (start_steering_timestamps, stop_steering_timestamps) = calculate_steering_start_stop(
            flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
        )

        results[f"OutOfCone_{phase}"] = sum(
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

    # calculation for "{controller}{coordinate}_{phase}" and "{controller}{coordinate}AvgTime_{phase}"
    for controller in ["THC", "RHC"]:
        for coordinate in ["x", "y", "z"]:
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
            (start_steering_timestamps, stop_steering_timestamps) = calculate_steering_start_stop(
                flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
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

    # calculation for "THCxErr_{phase}" and "THCxIndErr_{phase}" except x
    # flight_errors = flight_data[
    #     (
    #         (
    #             (flight_data["COG Vel.x [m]"] > flight_data["Ideal Approach Vel"])
    #             & (flight_data[f"THC.x"] != 0)
    #             & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
    #         )
    #         | (
    #             (flight_data[value_name] > 0)
    #             & (flight_data[f"{controller}.{coordinate}"] > 0)
    #             & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
    #         )
    #         | (
    #             (flight_data[value_name] < 0)
    #             & (flight_data[f"{controller}.{coordinate}"] < 0)
    #             & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
    #         )
    #     )
    #     & (
    #         (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
    #         & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
    #     )
    # ]

    # results[f"{controller}{coordinate}Err_{phase}"] = len(flight_errors)

    # # calculation for "{controller}{coordinate}IndErr_{phase}"
    # if controller == "THC":
    #     other_controller_axis = ["THC.y", "THC.z"]
    # else:
    #     other_controller_axis = ["RHC.x", "RHC.y", "RHC.z"]

    # other_controller_axis.remove(f"{controller}.{coordinate}")

    # results[f"{controller}{coordinate}IndErr_{phase}"] = len(
    #     flight_errors[flight_errors[other_controller_axis].any(axis=1)]
    # )

    # ToDo
    # check the following calculation, could be wrong because some axes are inverted
    # calculation for "{controller}{coordinate}Err_{phase}" and "{controller}{coordinate}IndErr_{phase}" except THC.x
    for coordinate in ["x", "y", "z"]:
        for controller, value_name in {
            "THC": f"COG Pos.{coordinate} [m]",
            "RHC": f"Rot Angle.{coordinate} [deg]",
        }.items():
            if not (controller == "THC" and coordinate == "x"):
                flight_errors = flight_data[
                    (
                        (
                            (flight_data[value_name] == 0)
                            & (flight_data[f"{controller}.{coordinate}"] != 0)
                            & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
                        )
                        | (
                            (flight_data[value_name] > 0)
                            & (flight_data[f"{controller}.{coordinate}"] > 0)
                            & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
                        )
                        | (
                            (flight_data[value_name] < 0)
                            & (flight_data[f"{controller}.{coordinate}"] < 0)
                            & (flight_data[f"{controller}.{coordinate}"].shift(periods=1, fill_value=0) == 0)
                        )
                    )
                    & (
                        (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
                        & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
                    )
                ]

                # calculation for "{controller}{coordinate}Err_{phase}"
                results[f"{controller}{coordinate}Err_{phase}"] = len(flight_errors)

                # calculation for "{controller}{coordinate}IndErr_{phase}"
                if controller == "THC":
                    other_controller_axis = ["THC.y", "THC.z"]
                else:
                    other_controller_axis = ["RHC.x", "RHC.y", "RHC.z"]

                other_controller_axis.remove(f"{controller}.{coordinate}")

                results[f"{controller}{coordinate}IndErr_{phase}"] = len(
                    flight_errors[flight_errors[other_controller_axis].any(axis=1)]
                )

    # calculation for "CombJoy_{phase}" and "CombJoyTime_{phase}"
    start_condition = (
        (flight_data[["THC.x", "THC.y", "THC.z"]].any(axis=1) & flight_data[["RHC.x", "RHC.y", "RHC.z"]].any(axis=1))
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
    (start_steering_timestamps, stop_steering_timestamps) = calculate_steering_start_stop(
        flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
    )

    results[f"CombJoyTime_{phase}"] = sum(
        [stop_steering_timestamps[i] - start_steering_timestamps[i] for i in range(len(start_steering_timestamps))]
    )

    # calculation for "CombJoy{controller}yz_{phase}" and "CombJoy{controller}yzTime_{phase}"
    for controller in ["THC", "RHC"]:
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
        (start_steering_timestamps, stop_steering_timestamps) = calculate_steering_start_stop(
            flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
        )

        results[f"CombJoy{controller}yzTime_{phase}"] = sum(
            [stop_steering_timestamps[i] - start_steering_timestamps[i] for i in range(len(start_steering_timestamps))]
        )

    # calculation for "CombJoy{controller}xyz_{phase}" and "CombJoy{controller}xyzTime_{phase}"
    for controller in ["THC", "RHC"]:
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
        (start_steering_timestamps, stop_steering_timestamps) = calculate_steering_start_stop(
            flight_data, start_condition, stop_condition, start_index, stop_index, flight_phase_timestamps
        )

        results[f"CombJoy{controller}xyzTime_{phase}"] = sum(
            [stop_steering_timestamps[i] - start_steering_timestamps[i] for i in range(len(start_steering_timestamps))]
        )

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
        "PitchRate": "Rot. Rate.Z [deg/s]",
    }.items():
        filtered_flight_data = flight_data[
            (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
            & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
        ]

        results[f"{result_name}Avg_{phase}"] = filtered_flight_data[column_name].mean()

        results[f"{result_name}Rms_{phase}"] = (filtered_flight_data[column_name] ** 2).mean() ** 0.5


def evaluate_flight_phases(flight_data, flight_phase_timestamps):
    results = create_dataframe_template_from_yaml()

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

    results["NoVisTime_Total"]  # ToDo
    results["Fuel_on_Error"]  # ToDo

    print(results.isna().sum(axis=1))

    export_data(results, r"C:\Users\Admin\Desktop\EvaluationResults.txt")
