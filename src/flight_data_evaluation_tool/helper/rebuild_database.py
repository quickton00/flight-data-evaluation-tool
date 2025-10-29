"""
Database rebuilding utility for development purposes.

This module provides functionality to recalculate and update the flight database
when evaluation metric implementations change. It re-processes all flight data
files and updates the JSON database with newly calculated metrics.

.. warning::
   This is a development-only tool. Do not run in production without backup.
"""

import os
import sys
import json
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from flight_data_evaluation_tool.evaluation import evaluate_flight_phases


def rebuild_database(database_path=r"data"):
    """
    Rebuild the flight database by re-evaluating all stored flight data.

    This function iterates through all CSV flight data files in the database,
    re-calculates their evaluation metrics using the current implementation,
    and updates the corresponding JSON database files. Useful when metric
    calculation logic changes and historical data needs to be updated.

    :param database_path: Path to the directory containing scenario subdirectories
                         with flight data CSV files, defaults to 'data'.
    :type database_path: str, optional

    **Process:**

    1. Loads the results template to ensure all columns are present
    2. Iterates through each scenario's JSON database file
    3. For each flight in the scenario:

       - Loads the corresponding CSV flight data
       - Extracts phase timestamps from existing results
       - Re-evaluates the flight using current metric implementations
       - Updates the JSON database

    4. Handles errors gracefully, printing error messages and continuing

    .. warning::
       This operation modifies the flight database. Ensure you have backups before
       running. The function will skip any flights that cause errors during evaluation.

    .. note::
       The function automatically adds missing columns from the template and removes
       columns not in the template, ensuring database consistency.
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

            try:
                evaluate_flight_phases(
                    flight_data,
                    phases,
                    results,
                )
            except Exception as e:
                print(f"Error processing {file}: {e}")
                continue


if __name__ == "__main__":
    rebuild_database()
