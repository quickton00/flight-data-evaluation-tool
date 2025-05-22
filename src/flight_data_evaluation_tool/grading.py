import pandas as pd
import numpy as np
from scipy.stats import chi2
from scipy.stats import shapiro, normaltest, anderson
from sklearn.preprocessing import PowerTransformer, QuantileTransformer


def is_normal(data, alpha=0.05):
    """Check normality using Shapiro-Wilk, D’Agostino’s K^2, and Anderson-Darling tests"""
    _, p1 = shapiro(data)  # Shapiro-Wilk test
    _, p2 = normaltest(data)  # D’Agostino’s K^2 test
    res = anderson(data)  # Anderson-Darling test

    return (p1 > alpha) and (p2 > alpha) and (res.statistic < res.critical_values[2])


def is_zero_inflated(data, alpha):
    mean = data.mean()

    # check for zero inflation with Jan van der Broek test

    # Estimated probability of zero under Poisson
    p0_tilde = np.exp(-mean)

    # Count observed zeros
    n0 = np.sum(data == 0)
    n = len(data)

    if n0 == n:
        return True

    # Compute test statistic
    numerator = (n0 - n * p0_tilde) ** 2
    denominator = n * p0_tilde * (1 - p0_tilde) - n * mean * (p0_tilde**2)

    statistic = numerator / denominator

    # p-value from chi-square distribution with 1 degree of freedom
    p_value = chi2.sf(statistic, df=1)

    return p_value < alpha


def transform_data(data, transformer_type, method="yeo-johnson"):
    """Transform data using PowerTransformer"""
    if transformer_type == "power":
        pt = PowerTransformer(method=method)
        return pd.Series(pt.fit_transform(data.values.reshape(-1, 1)).flatten(), index=data.index), pt
    elif transformer_type == "quantile":
        # Set n_quantiles to min(1000, number of samples) to avoid warning
        n_quantiles = min(1000, len(data))
        qt = QuantileTransformer(output_distribution="normal", n_quantiles=n_quantiles)
        return pd.Series(qt.fit_transform(data.values.reshape(-1, 1)).flatten(), index=data.index), qt
    else:
        raise ValueError("Invalid transform type. Use 'power' or 'quantile'.")


def tier_data():

    json_file_path = "src/flight_data_evaluation_tool/flight_data.json"

    # Load database
    database = pd.read_json(json_file_path, orient="records", lines=True, convert_dates=False)

    # TODO: switch to phase wise evaluation, currently only align phase

    regex_filter = "Appr|FA|Total|Flight ID|Dock|Date|Scenario|Manually modified Phases"

    database = database[database.columns.drop(list(database.filter(regex=regex_filter)))]

    test_row = database.iloc[-1]

    normal_counter = 0
    non_normal_counter = 0

    for column in database:
        print(column)
        dist_type, metric, transformer = tier_metric(database[column])

        if dist_type == "normal":
            print(dist_type)
            normal_counter += 1
            print(test_row[column])

            if test_row[column] == 0:
                print("Excellent")
                continue

            if transformer:
                current_value = transformer.transform(test_row[column].reshape(1, -1))
            else:
                current_value = test_row[column]

            if current_value <= metric.mean() - 2 * metric.std():
                print("Excellent")
            elif current_value <= metric.mean() - metric.std():
                print("Good")
            elif current_value <= metric.mean() + metric.std():
                print("Normal")
            elif current_value <= metric.mean() + 2 * metric.std():
                print("Poor")
            else:
                print("Very Poor")
        elif dist_type == "non-normal":
            print(dist_type)
            non_normal_counter += 1
            print(test_row[column])

            print(metric.sort_values())

            current_value = test_row[column]

            # TODO: evtl auch kleiner gleich bei count metrics?

            if current_value < metric.nsmallest(round(len(metric) * 0.023 + 0.5)).values[-1]:
                print("Excellent")
            elif current_value < metric.nsmallest(round(len(metric) * 0.159 + 0.5)).values[-1]:
                print("Good")
            elif current_value < metric.nsmallest(round(len(metric) * 0.841 + 0.5)).values[-1]:
                print("Normal")
            elif current_value < metric.nsmallest(round(len(metric) * 0.977 + 0.5)).values[-1]:
                print("Poor")
            else:
                print("Very Poor")

        else:
            raise ValueError("Invalid distribution type. Use 'normal' or 'non-normal'.")

    print(f"Normal: {normal_counter}, Non-normal: {non_normal_counter}")


def tier_metric(metric, alpha=0.05):
    mean = metric.mean()
    std = metric.std()

    # cut outliers greater than 3 std
    metric = metric[lambda value: (value >= mean - 3 * std) & (value <= mean + 3 * std)]

    if is_zero_inflated(metric, alpha):
        # zero inflation detected
        metric = metric[lambda value: value > 0]

    if len(metric) == 0 or is_normal(metric, alpha):
        return "normal", metric, None

    for method in ["box-cox", "yeo-johnson"]:
        if method == "box-cox" and (metric <= 0).any():
            continue

        metric_power, transformer = transform_data(metric, transformer_type="power", method=method)

        if is_normal(metric_power):
            return "normal", metric_power, transformer

    # check if metric is quantile transformable if power transform fails
    quantile_metric, transformer = transform_data(metric, transformer_type="quantile")

    if is_normal(quantile_metric):
        return "normal", quantile_metric, transformer

    return "non-normal", metric, None


if __name__ == "__main__":
    tier_data()
