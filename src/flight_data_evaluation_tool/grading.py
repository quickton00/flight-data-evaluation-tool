import pandas as pd
from scipy.stats import shapiro, normaltest, anderson
from sklearn.preprocessing import PowerTransformer


def is_normal(data, alpha=0.05):
    """Check normality using Shapiro-Wilk, D’Agostino’s K^2, and Anderson-Darling tests"""
    _, p1 = shapiro(data)  # Shapiro-Wilk test
    _, p2 = normaltest(data)  # D’Agostino’s K^2 test
    res = anderson(data)  # Anderson-Darling test

    return (p1 > alpha) and (p2 > alpha) and (res.statistic < res.critical_values[2])


def tier_data():

    json_file_path = "src/flight_data_evaluation_tool/flight_data.json"

    # Load database
    database = pd.read_json(json_file_path, orient="records", lines=True, convert_dates=False)

    # TODO: switch to phase wise evaluation, currently only align phase

    database = database[
        database.columns.drop(
            list(database.filter(regex="Appr|FA|Total|Flight ID|Dock|Date|Scenario|Manually modified Phases"))
        )
    ]

    normal_counter = 0
    non_normal_counter = 0

    for column in database:
        result = tier_metric(database[column])

        if result == "normal":
            normal_counter += 1
        else:
            non_normal_counter += 1

    print(f"Normal: {normal_counter}")
    print(f"Non-normal: {non_normal_counter}")


def tier_metric(metric):
    mean = metric.mean()
    std = metric.std()

    # cut outliers greater than 3 std
    metric = metric[lambda value: (value >= mean - 3 * std) & (value <= mean + 3 * std)]

    # check if metric is normal
    if is_normal(metric):
        return "normal"

    # check if metric is transformable
    pt = PowerTransformer(method="yeo-johnson")
    metric = pd.Series(pt.fit_transform(metric.values.reshape(-1, 1)).flatten(), index=metric.index)

    if is_normal(metric):
        return "normal"
    else:
        return "non-normal"


if __name__ == "__main__":
    tier_data()
