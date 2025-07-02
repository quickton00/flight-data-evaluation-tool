import pandas as pd
import numpy as np
import pylab
import scipy.stats as stats
from scipy.stats import chi2
from scipy.stats import shapiro, normaltest, anderson
from sklearn.preprocessing import PowerTransformer, QuantileTransformer
from crispyn import weighting_methods as mcda_weights


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

    if is_zero_inflated(metric, alpha) and is_count_metric(metric):
        return "zero-inflated", metric, None, True

    if len(metric) == 0 or is_normal(metric, alpha):
        return "normal", metric, None, False

    for method in ["box-cox", "yeo-johnson"]:
        if (method == "box-cox" and (metric <= 0).any()) or metric.eq(metric.iloc[0]).all():
            continue

        metric_power, transformer = transform_data(metric, transformer_type="power", method=method)

        if is_normal(metric_power, alpha):
            return "normal", metric, transformer, False

    # check if metric is quantile transformable if power transform fails
    quantile_metric, transformer = transform_data(metric, transformer_type="quantile")

    if is_normal(quantile_metric, alpha):
        return "normal", metric, transformer, False

    if is_count_metric(raw_metric):
        return "count-non-normal", raw_metric, None, False

    return "non-normal", raw_metric, None, False


def tier_data(test_row, phase):
    phase_filter = {
        "Alignment Phase": "Appr|FA|Total|Dock",
        "Approach Phase": "Align|FA|Total|Dock",
        "Final Approach Phase": "Align|Appr|Total|Dock",
        "Total Flight": "Align|Appr|FA",
    }[phase]

    regex_filter = f"{phase_filter}|Flight ID|Date|Scenario|Manually modified Phases"

    json_file_path = f"src/flight_data_evaluation_tool/database/{test_row["Scenario"]}_flight_data.json"

    # Load database
    database = pd.read_json(json_file_path, orient="records", lines=True, convert_dates=False)

    database = database[database.columns.drop(list(database.filter(regex=regex_filter)))]

    weights = pd.DataFrame(
        [calculate_phase_weights(database)],
        columns=database.columns,
    )

    counter = {"normal": 0, "non-normal": 0, "count-non-normal": 0, "zero-inflated": 0}

    tiered_data = {"Excellent": [], "Good": [], "Normal": [], "Poor": [], "Very Poor": []}

    metrics = {}

    for column in database:
        dist_type, metric, transformer, zero_inflated = tier_metric(database[column])

        metrics[column] = metric

        counter[dist_type] += 1

        if dist_type == "normal" and not zero_inflated:
            current_value = test_row[column]

            tier_borders = [metric.mean() + i * metric.std() for i in [-2, -1, 1, 2]]

            data_obj = {
                column: {
                    "Value": current_value,
                    "Mean": metric.mean(),
                    "Std": metric.std(),
                    "Type": dist_type,
                    "Weight": weights[column].iloc[0],
                    "Percentile": "",
                    "Borders": tier_borders,
                }
            }

            if current_value == 0:
                tiered_data["Excellent"].append(data_obj)
                continue

            if transformer:
                current_value = transformer.transform(np.array(test_row[column]).reshape(-1, 1))[0][0]
                metric = transformer.transform(metric.values.reshape(-1, 1)).flatten()
                tier_borders = [metric.mean() + i * metric.std() for i in [-2, -1, 1, 2]]
                data_obj[column]["trans_Value"] = current_value
                data_obj[column]["Borders"] = tier_borders
                metrics[column] = metric

            # TODO: should not be the transformed metric be displayed when we have a transformer?

            if current_value <= tier_borders[0]:
                tiered_data["Excellent"].append(data_obj)
            elif current_value <= tier_borders[1]:
                tiered_data["Good"].append(data_obj)
            elif current_value <= tier_borders[2]:
                tiered_data["Normal"].append(data_obj)
            elif current_value <= tier_borders[3]:
                tiered_data["Poor"].append(data_obj)
            else:
                tiered_data["Very Poor"].append(data_obj)
        elif dist_type == "non-normal" or dist_type == "count-non-normal" or zero_inflated:
            # visual inspection via Q-Q plot
            # stats.probplot(metric, dist="norm", plot=pylab)
            # pylab.show()

            current_value = test_row[column]

            sorted_metric = metric.sort_values(ignore_index=True)

            try:
                percentile = sorted_metric[sorted_metric <= current_value].index[-1] / len(sorted_metric)
            except IndexError:
                percentile = 0.0

            tier_borders = [
                sorted_metric.nsmallest(round(len(sorted_metric) * 0.023 + 0.5)).values[-1],
                sorted_metric.nsmallest(round(len(sorted_metric) * 0.159 + 0.5)).values[-1],
                sorted_metric.nsmallest(round(len(sorted_metric) * 0.841 + 0.5)).values[-1],
                sorted_metric.nsmallest(round(len(sorted_metric) * 0.977 + 0.5)).values[-1],
            ]

            data_obj = {
                column: {
                    "Value": current_value,
                    "Mean": metric.mean(),
                    "Std": metric.std(),
                    "Type": dist_type,
                    "Weight": weights[column].iloc[0],
                    "Percentile": percentile,
                    "Borders": tier_borders,
                }
            }

            if current_value <= tier_borders[0]:
                tiered_data["Excellent"].append(data_obj)
            elif current_value <= tier_borders[1]:
                tiered_data["Good"].append(data_obj)
            elif current_value <= tier_borders[2]:
                tiered_data["Normal"].append(data_obj)
            elif current_value <= tier_borders[3]:
                tiered_data["Poor"].append(data_obj)
            else:
                tiered_data["Very Poor"].append(data_obj)

        else:
            raise ValueError("Invalid distribution type. Use 'normal', 'non-normal' or 'count-non-normal'.")

    # print(counter)

    return tiered_data, metrics


def calculate_phase_weights(data):
    # Identify non constant columns
    variable_cols = data.columns[data.nunique() > 1]

    # Calculate weights only for variable columns
    if len(variable_cols) > 0:
        variable_data = data[variable_cols].to_numpy()
        variable_weights = mcda_weights.critic_weighting(variable_data)

    # Build full weight vector (zero for constant columns)
    weights = pd.Series(0.0, index=data.columns)
    weights[variable_cols] = variable_weights

    return weights
