# helper function to recalculate the database when implementation of evaluation parameters changes
# for development purposes only

import os
import sys
import yaml
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from flight_data_evaluation_tool.evaluation import evaluate_flight_phases


def rebuild_database(database_path=r"data"):
    json_file_path = "src/flight_data_evaluation_tool/flight_data.json"
    yaml_file_path = r"src\flight_data_evaluation_tool\results_template.yaml"

    results_json = pd.read_json(json_file_path, orient="records", lines=True, convert_dates=False)

    with open(yaml_file_path, "r") as f:
        yaml_config = yaml.safe_load(f)

    for column in yaml_config["columns"]:
        if column not in results_json.columns:
            results_json[column] = None  # Add missing columns with default value `None`

    for column in results_json.columns:
        if column not in yaml_config["columns"]:
            results_json = results_json.drop(columns=column)

    for file in os.listdir(database_path):
        flight_data = pd.read_csv(os.path.join(database_path, file), float_precision="round_trip")

        results = results_json[results_json["Flight ID"] == os.path.splitext(file)[0]].reset_index(drop=True)

        phases = [results["Start_Align"][0], results["Start_Appr"][0], results["Start_FA"][0], results["Time_Dock"][0]]

        evaluate_flight_phases(
            flight_data,
            phases,
            results,
        )


if __name__ == "__main__":
    rebuild_database()
