# helper function to recalculate the database when implementation of evaluation parameters changes
# for development purposes only

import os
import sys
import json
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from flight_data_evaluation_tool.evaluation import evaluate_flight_phases


def rebuild_database(database_path=r"data"):
    """
    Rebuilds the flight database by processing and evaluating flight data against predefined templates.
    This function reads flight data from a JSON file and compares it against a YAML template,
    ensuring all required columns are present. It then processes each flight data CSV file in
    the specified database directory, matching it with the corresponding JSON data using the
    flight ID, and evaluates flight phases.
    Args:
        database_path (str, optional): Path to the directory containing flight data CSV files.
            Defaults to "data".
    Notes:
        - The function reads flight data from 'flight_data.json' and configuration from 'results_template.yaml'
        - Missing columns from the YAML template are added to the data with None values
        - Columns not specified in the YAML template are removed from the data
        - Each CSV file in the database directory is processed and evaluated using the evaluate_flight_phases function
        - Flight phases are extracted from the results data for evaluation
    """

    # json_file_path = "src/flight_data_evaluation_tool/flight_data.json"
    template_file_path = r"src\flight_data_evaluation_tool\results_template.json"

    base_path = "src/flight_data_evaluation_tool/database"

    json_file_paths = os.listdir(base_path)

    for json_file_path in json_file_paths:
        if not json_file_path.endswith(".json"):
            continue

        print(f"Processing file: {json_file_path}")

        scenario = json_file_path.split("_")[0]
        scenario_database_path = os.path.join(database_path, scenario)

        json_file_path = os.path.join(base_path, json_file_path)

        results_json = pd.read_json(json_file_path, orient="records", lines=True, convert_dates=False)

        with open(template_file_path, "r") as f:
            results_template = json.load(f)

        for column in results_template["columns"]:
            if column not in results_json.columns:
                results_json[column] = None  # Add missing columns with default value `None`

        for column in results_json.columns:
            if column not in results_template["columns"]:
                results_json = results_json.drop(columns=column)

        for file in os.listdir(scenario_database_path):
            flight_data = pd.read_csv(os.path.join(scenario_database_path, file), float_precision="round_trip")

            results = results_json[results_json["Flight ID"] == os.path.splitext(file)[0]].reset_index(drop=True)

            phases = [
                results["Start_Align"][0],
                results["Start_Appr"][0],
                results["Start_FA"][0],
                results["Time_Dock"][0],
            ]

            evaluate_flight_phases(
                flight_data,
                phases,
                results,
            )


if __name__ == "__main__":
    rebuild_database()
