import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import chi2
from scipy.stats import shapiro, normaltest, anderson
from sklearn.preprocessing import PowerTransformer


def is_normal(data, alpha=0.05):
    """Check normality using Shapiro-Wilk, D’Agostino’s K^2, and Anderson-Darling tests"""
    _, p1 = shapiro(data)  # Shapiro-Wilk test
    _, p2 = normaltest(data)  # D’Agostino’s K^2 test
    res = anderson(data)  # Anderson-Darling test

    return (p1 > alpha) and (p2 > alpha) and (res.statistic < res.critical_values[2])


def is_count_data(data):
    """Check if data is count data (non-negative integers)"""
    return all(isinstance(x, int) and x >= 0 for x in data)


def transform_data(data, method):
    """Transform data using PowerTransformer"""
    pt = PowerTransformer(method=method)
    return pd.Series(pt.fit_transform(data.values.reshape(-1, 1)).flatten(), index=data.index)


def tier_count_metric(metric, alpha=0.05):
    mean = metric.mean()

    # check for zero inflation with Jan van der Broek test

    # Estimated probability of zero under Poisson
    p0_tilde = np.exp(-mean)

    # Count observed zeros
    n0 = np.sum(metric == 0)
    n = len(metric)

    if n0 == n:
        plt.hist(metric)
        plt.show()

        return "count zero-inflated-non normal"

    # Compute test statistic
    numerator = (n0 - n * p0_tilde) ** 2
    denominator = n * p0_tilde * (1 - p0_tilde) - n * mean * (p0_tilde**2)

    statistic = numerator / denominator

    # p-value from chi-square distribution with 1 degree of freedom
    p_value = chi2.sf(statistic, df=1)

    if p_value < alpha:
        # zero inflation detected
        metric = metric[lambda value: value > 0]

        if is_normal(metric, alpha):
            return "count zero-inflated normal"

        # check if metric is transformable
        metric = transform_data(metric, method="box-cox")

        if is_normal(metric):
            return "count zero-inflated normal"
        else:
            plt.hist(metric)
            plt.show()

            return "count zero-inflated-non normal"

    else:
        # no zero inflation
        if is_normal(metric, alpha):
            return "count normal"

        metric = transform_data(metric, method="yeo-johnson")

        if is_normal(metric):
            return "count normal"
        else:
            plt.hist(metric)
            plt.show()

            return "count non-normal"


def tier_continuous_metric(metric, alpha=0.05):
    if is_normal(metric, alpha):
        return "continuous normal"

    # check if metric is transformable
    metric = transform_data(metric, method="yeo-johnson")

    if is_normal(metric):
        return "continuous normal"
    else:
        plt.hist(metric)
        plt.show()

        return "continuous non-normal"


def tier_data():

    json_file_path = "src/flight_data_evaluation_tool/flight_data.json"

    # Load database
    database = pd.read_json(json_file_path, orient="records", lines=True, convert_dates=False)

    # TODO: switch to phase wise evaluation, currently only align phase

    database = database[
        database.columns.drop(
            list(database.filter(regex="Align|FA|Total|Flight ID|Dock|Date|Scenario|Manually modified Phases"))
        )
    ]

    counter = {
        "continuous normal": 0,
        "continuous non-normal": 0,
        "count zero-inflated normal": 0,
        "count zero-inflated-non normal": 0,
        "count normal": 0,
        "count non-normal": 0,
    }

    for column in database:
        print(column)
        result = tier_metric(database[column])

        counter[result] += 1

    print(counter)


def tier_metric(metric):
    mean = metric.mean()
    std = metric.std()

    # cut outliers greater than 3 std
    metric = metric[lambda value: (value >= mean - 3 * std) & (value <= mean + 3 * std)]

    if is_count_data(metric):
        return tier_count_metric(metric)
    else:
        return tier_continuous_metric(metric)


if __name__ == "__main__":
    tier_data()
