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


def calculate_phase_evaluation_values(flight_data, phase, counter, flight_phase_timestamps, results):
    if f"Start_{phase}" in results.columns:
        results[f"Start_{phase}"] = flight_phase_timestamps[counter]

    if f"Duration_{phase}" in results.columns:
        results[f"Duration_{phase}"] = flight_phase_timestamps[counter + 1] - flight_phase_timestamps[counter]

    if f"Fuel_{phase}" in results.columns:
        results[f"Fuel_{phase}"] = (
            flight_data[flight_data["SimTime"] == flight_phase_timestamps[counter]].iloc[0]["Tank mass [kg]"]
            - flight_data[flight_data["SimTime"] == flight_phase_timestamps[counter + 1]].iloc[0]["Tank mass [kg]"]
        )

    if f"LatOffsetAtStart_{phase}" in results.columns:
        results[f"LatOffsetAtStart_{phase}"] = flight_data[
            flight_data["SimTime"] == flight_phase_timestamps[counter]
        ].iloc[0]["Lateral Offset"]


def evaluate_flight_phases(flight_data, flight_phase_timestamps):
    results = create_dataframe_template_from_yaml()

    counter = 0
    for phase in ["Align", "Appr", "FA", "Total"]:
        calculate_phase_evaluation_values(flight_data, phase, counter, flight_phase_timestamps, results)
        counter += 1

    # calculate exceptions
    results["Time_Dock"] = flight_phase_timestamps[3]
    results["LatOffsetAt_Dock"] = flight_data[flight_data["SimTime"] == flight_phase_timestamps[3]].iloc[0][
        "Lateral Offset"
    ]
    # calculate_phase_durations(flight_data, phases, results)

    results["OutOfCone_Align"]  # ToDo, Function maybe good?
    results["OutOfCone_Appr"]  # ToDo
    results["OutOfCone_FA"]  # ToDo

    print(results)
    print(results["Fuel_Align"])
