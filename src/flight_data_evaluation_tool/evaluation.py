# methods to create the datapoints for evaluation

import pandas as pd
import yaml


def create_dataframe_template_from_yaml(yaml_file=r"src\flight_data_evaluation_tool\results_template.yaml"):
    with open(yaml_file, "r") as f:
        config = yaml.safe_load(f)

    # Extract columns from the loaded YAML
    columns = config["columns"]

    # Create an empty DataFrame with defined columns and data types
    df_template = pd.DataFrame(columns=columns, index=[0])

    return df_template


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

    # calculaion for "Fuel_{phase}"
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

    # calculation for "{controller}{coordinate}_{phase}"
    for controller in ["THC", "RHC"]:
        for coordinate in ["x", "y", "z"]:
            filtered_flight_data = flight_data[
                (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
                & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
            ]

            results[f"{controller}{coordinate}_{phase}"] = (
                (filtered_flight_data[f"{controller}.{coordinate}"] != 0)
                & (filtered_flight_data[f"{controller}.{coordinate}"].shift(periods=1) == 0)
            ).sum()

    # Calculation for "THC{coordinate}AvgTime_{phase}"
    # ToDo

    # calculation for "THCxErr_{phase}" and "THCxIndErr_{phase}" except x
    # ToDo

    # calculation for "{controller}{coordinate}Err_{phase}" and "{controller}{coordinate}IndErr_{phase}" except THC.x
    for coordinate in ["x", "y", "z"]:
        for controller, value_name in {
            "THC": f"COG Pos.{coordinate} [m]",
            "RHC": f"Rot Angle.{coordinate} [deg]",
        }.items():
            if not (controller == "THC" and coordinate == "x"):
                filtered_flight_data = flight_data[
                    (flight_data["SimTime"] >= flight_phase_timestamps[start_index])
                    & (flight_data["SimTime"] < flight_phase_timestamps[stop_index])
                ]

                flight_errors = filtered_flight_data[
                    (
                        (filtered_flight_data[value_name] == 0)
                        & (filtered_flight_data[f"{controller}.{coordinate}"] != 0)
                        & (filtered_flight_data[f"{controller}.{coordinate}"].shift(periods=1) == 0)
                    )
                    | (
                        (filtered_flight_data[value_name] > 0)
                        & (filtered_flight_data[f"{controller}.{coordinate}"] > 0)
                        & (filtered_flight_data[f"{controller}.{coordinate}"].shift(periods=1) == 0)
                    )
                    | (
                        (filtered_flight_data[value_name] < 0)
                        & (filtered_flight_data[f"{controller}.{coordinate}"] < 0)
                        & (filtered_flight_data[f"{controller}.{coordinate}"].shift(periods=1) == 0)
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
    # calculate_phase_durations(flight_data, phases, results)

    results["OutOfCone_Align"]  # ToDo, Function maybe good?
    results["OutOfCone_Appr"]  # ToDo
    results["OutOfCone_FA"]  # ToDo
    results["NoVisTime_Total"]

    print(results.isna().sum(axis=1))

    export_data(results, r"C:\Users\Admin\Desktop\EvaluationResults.txt")