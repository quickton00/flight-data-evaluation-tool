import pandas as pd
import numpy as np
import pylab
import scipy.stats as stats
from scipy.stats import chi2
from scipy.stats import shapiro, normaltest, anderson
from sklearn.preprocessing import PowerTransformer, QuantileTransformer


def is_normal(data, alpha=0.05):
    """Check normality using Shapiro-Wilk, D’Agostino’s K^2, and Anderson-Darling tests"""
    _, p1 = shapiro(data)  # Shapiro-Wilk test
    _, p2 = normaltest(data)  # D’Agostino’s K^2 test
    res = anderson(data)  # Anderson-Darling test

    # Check if any of the tests reject the null hypothesis of normality
    return (p1 > alpha) or (p2 > alpha) or (res.statistic < res.critical_values[2])


def is_zero_inflated(data, alpha=0.05):
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


def is_count_metric(data):
    """Check if the data is a count metric (non-negative integers)"""
    return np.issubdtype(data.dtype, np.integer) and (data >= 0).all() and (data == data.astype(int)).all()


def transform_data(data, transformer_type, method="yeo-johnson"):
    """Transform data using PowerTransformer"""
    if transformer_type == "power":
        pt = PowerTransformer(method=method)
        return pd.Series(pt.fit_transform(data.values.reshape(-1, 1)).flatten(), index=data.index), pt
    elif transformer_type == "quantile":
        # Set n_quantiles to min(1000, number of samples) to avoid warning
        n_quantiles = min(100, len(data))
        qt = QuantileTransformer(output_distribution="normal", n_quantiles=n_quantiles)
        return pd.Series(qt.fit_transform(data.values.reshape(-1, 1)).flatten(), index=data.index), qt
    else:
        raise ValueError("Invalid transform type. Use 'power' or 'quantile'.")


def tier_metric(raw_metric, alpha=0.05):
    mean = raw_metric.mean()
    std = raw_metric.std()

    # cut outliers greater than 3 std
    metric = raw_metric[lambda value: (value >= mean - 3 * std) & (value <= mean + 3 * std)]

    if is_zero_inflated(metric, alpha):
        # TODO: include zeros in second part of hurdle model data,
        # e.g. for high zero inflation no excellent tier in non-zero data

        # zero inflation detected
        metric = metric[metric > 0]  # remove zeros for power transformation

    if len(metric) == 0 or is_normal(metric, alpha):
        return "normal", metric, None

    for method in ["box-cox", "yeo-johnson"]:
        if (method == "box-cox" and (metric <= 0).any()) or metric.eq(metric.iloc[0]).all():
            continue

        metric_power, transformer = transform_data(metric, transformer_type="power", method=method)

        if is_normal(metric_power, alpha):
            return "normal", metric_power, transformer

    # check if metric is quantile transformable if power transform fails
    quantile_metric, transformer = transform_data(metric, transformer_type="quantile")

    if is_normal(quantile_metric, alpha):
        return "normal", quantile_metric, transformer

    if is_count_metric(raw_metric):
        return "count-non-normal", raw_metric, None
    else:
        return "non-normal", raw_metric, None


def tier_data():

    json_file_path = "src/flight_data_evaluation_tool/flight_data.json"

    # Load database
    database = pd.read_json(json_file_path, orient="records", lines=True, convert_dates=False)

    # TODO: switch to phase wise evaluation, currently only align phase

    regex_filter = "Appr|FA|Total|Flight ID|Dock|Date|Scenario|Manually modified Phases"

    database = database[database.columns.drop(list(database.filter(regex=regex_filter)))]

    test_row = database.iloc[-1]

    counter = {"normal": 0, "non-normal": 0, "count-non-normal": 0}

    for column in database:
        print(column)
        dist_type, metric, transformer = tier_metric(database[column])

        counter[dist_type] += 1

        if dist_type == "normal":
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
        elif dist_type == "non-normal" or dist_type == "count-non-normal":
            # visual inspection via Q-Q plot
            # stats.probplot(metric, dist="norm", plot=pylab)
            # pylab.show()

            current_value = test_row[column]

            if current_value <= metric.nsmallest(round(len(metric) * 0.023 + 0.5)).values[-1]:
                print("Excellent")
            elif current_value <= metric.nsmallest(round(len(metric) * 0.159 + 0.5)).values[-1]:
                print("Good")
            elif current_value <= metric.nsmallest(round(len(metric) * 0.841 + 0.5)).values[-1]:
                print("Normal")
            elif current_value <= metric.nsmallest(round(len(metric) * 0.977 + 0.5)).values[-1]:
                print("Poor")
            else:
                print("Very Poor")

        else:
            raise ValueError("Invalid distribution type. Use 'normal', 'non-normal' or 'count-non-normal'.")

    print(counter)


if __name__ == "__main__":
    tier_data()
