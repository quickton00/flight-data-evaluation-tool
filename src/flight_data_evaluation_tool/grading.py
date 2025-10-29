"""
Flight performance grading and statistical analysis module.

This module provides comprehensive functionality for grading flight performance
through statistical analysis, data normalization, and multi-criteria decision
analysis (MCDA). It includes methods for checking data distribution normality,
handling zero-inflated data, applying power and quantile transformations, and
calculating performance tiers based on historical flight data.
"""

import pandas as pd
import numpy as np
import json
import os
import sys
import scipy.stats as stats
from scipy.stats import chi2
from scipy.stats import shapiro, normaltest, anderson
from sklearn.preprocessing import PowerTransformer, QuantileTransformer
from crispyn import weighting_methods as mcda_weights

try:
    from helper.thesis import compare_weighting_methods_and_rank
except ImportError:
    pass


def is_normal(data, alpha=0.05):
    """
    Check if data follows a normal distribution using multiple statistical tests.

    This function employs three different normality tests: Shapiro-Wilk,
    D'Agostino's K-squared, and Anderson-Darling. Data is considered normal
    if any of these tests fail to reject the null hypothesis of normality.

    :param data: The data to test for normality.
    :type data: array-like
    :param alpha: Significance level for hypothesis testing, defaults to 0.05.
    :type alpha: float, optional
    :return: True if data appears to be normally distributed, False otherwise.
    :rtype: bool

    .. note::
       The function uses a logical OR across all three tests, providing a more
       lenient assessment of normality. Data is considered normal if ANY test
       suggests normality.
    """
    _, p1 = shapiro(data)  # Shapiro-Wilk test
    _, p2 = normaltest(data)  # D’Agostino’s K^2 test
    res = anderson(data)  # Anderson-Darling test

    # Check if any of the tests reject the null hypothesis of normality
    return (p1 > alpha) or (p2 > alpha) or (res.statistic < res.critical_values[2])


def is_zero_inflated(data, alpha=0.05):
    """
    Test if data exhibits zero-inflation using the Jan van den Broek test.

    :param data: The data to test for zero-inflation.
    :type data: array-like
    :param alpha: Significance level for the hypothesis test, defaults to 0.05.
    :type alpha: float, optional
    :return: True if the data is zero-inflated, False otherwise.
    :rtype: bool

    .. note::
       If all values in the data are zero, the function returns True immediately.
       The test uses a chi-square distribution with 1 degree of freedom.
    """
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
    """
    Check if data represents a count metric (non-negative integers).

    :param data: The data to check.
    :type data: array-like
    :return: True if the data is a count metric, False otherwise.
    :rtype: bool
    """
    return np.issubdtype(data.dtype, np.integer) and (data >= 0).all() and (data == data.astype(int)).all()


def transform_data(data, transformer_type, method="yeo-johnson"):
    """
    Transform data using power or quantile transformation for normalization.

    This function applies either a power transformation (Box-Cox or Yeo-Johnson)
    or quantile transformation to make the data more normally distributed.

    :param data: The data to transform.
    :type data: pandas.Series or array-like
    :param transformer_type: Type of transformation - either 'power' or 'quantile'.
    :type transformer_type: str
    :param method: For power transformation, either 'box-cox' or 'yeo-johnson',
                  defaults to 'yeo-johnson'.
    :type method: str, optional
    :return: Tuple containing the transformed data as pandas Series and the fitted
            transformer object.
    :rtype: tuple(pandas.Series, object)
    :raises ValueError: If transformer_type is not 'power' or 'quantile'.

    .. note::
       - Box-Cox transformation requires all positive values
       - Yeo-Johnson transformation works with any real values
       - Quantile transformation uses min(100, n_samples) quantiles to avoid warnings
    """
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
    """
    Classify a metric's distribution and apply appropriate transformation if needed.

    This function analyzes a metric to determine its distribution type (normal,
    zero-inflated, count-based, or non-normal) and applies transformations to
    achieve normality when possible. It handles outliers by filtering values
    beyond 3 standard deviations.

    :param raw_metric: The raw metric data to classify and potentially transform.
    :type raw_metric: pandas.Series or array-like
    :param alpha: Significance level for statistical tests, defaults to 0.05.
    :type alpha: float, optional
    :return: Tuple containing:
            - distribution_type (str): Type of distribution ('normal', 'zero-inflated',
              'count-non-normal', or 'non-normal')
            - metric (pandas.Series): Cleaned or original metric data
            - transformer (object or None): Fitted transformer if transformation was applied
            - zero_inflated (bool): Flag indicating if data is zero-inflated
    :rtype: tuple

    .. note::
       The function attempts transformations in this order:
       1. Check for zero-inflation and count metrics
       2. Check for natural normality
       3. Try Box-Cox transformation (if all values > 0)
       4. Try Yeo-Johnson transformation
       5. Try quantile transformation
       6. Fall back to non-normal classification
    """
    mean = raw_metric.mean()
    std = raw_metric.std()

    # cut outliers greater than 3 std
    metric = raw_metric[lambda value: (value >= mean - 3 * std) & (value <= mean + 3 * std)]

    if is_zero_inflated(metric, alpha) and is_count_metric(metric):
        return "zero-inflated", metric, None, True

    if len(metric) == 0 or len(set(metric)) == 1:
        return "non-normal", raw_metric, None, False

    if is_normal(metric, alpha):
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


def _resource_path(*relative_parts):
    """
    Return absolute path for both PyInstaller bundles and development environments.

    This helper function handles path resolution in both development and
    production (PyInstaller) environments by detecting the execution context
    and using the appropriate base directory.

    :param relative_parts: Path components to join to the base directory.
    :type relative_parts: tuple of str
    :return: Absolute path combining base directory with relative path components.
    :rtype: str

    .. note::
       When running as a PyInstaller bundle, uses sys._MEIPASS as the base directory.
       In development, uses the directory containing grading.py.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
    else:
        # folder where grading.py lives
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, *relative_parts)


def tier_data(test_row, phase):
    """
    Tier a single flight's performance metrics against historical database.

    This function loads the appropriate flight database, performs statistical
    analysis on each metric, and assigns performance tiers (Excellent, Good,
    Normal, Poor, Very Poor) based on how the test flight compares to historical
    performance data.

    :param test_row: pandas Series or dict containing the flight's metric values
                    to be evaluated. Must include 'Scenario' key.
    :type test_row: pandas.Series or dict
    :param phase: The flight phase to evaluate. Must be one of: 'Alignment Phase',
                 'Approach Phase', 'Final Approach Phase', or 'Total Flight'.
    :type phase: str
    :return: Tuple containing:
            - tiered_data (dict): Dictionary with tier names as keys and lists of
              metric dictionaries as values. Each metric dict contains value, mean,
              std, type, percentile, and borders.
            - metrics (dict): Dictionary mapping metric names to their cleaned data series.
            - required_database (pandas.DataFrame): The filtered database used for
              comparison (excluding optional columns).
    :rtype: tuple(dict, dict, pandas.DataFrame)
    :raises FileNotFoundError: If the database file for the scenario doesn't exist.

    The tier assignment is based on:

    - **Normal distributions**: Uses mean ± n*std boundaries (n = 1, 2)
    - **Non-normal distributions**: Uses percentile boundaries (2.3%, 15.9%, 84.1%, 97.7%)
    - **Zero-inflated**: Treated as non-normal with percentile boundaries

    .. note::
       Metrics marked as 'optional' in the results template are placed in the
       'Not Tierable' category and excluded from weight calculations.
    """
    phase_filter = {
        "Alignment Phase": "Appr|FA|Total|Dock",
        "Approach Phase": "Align|FA|Total|Dock",
        "Final Approach Phase": "Align|Appr|Total|Dock",
        "Total Flight": "Align|Appr|FA",
    }[phase]

    regex_filter = f"{phase_filter}|Flight ID|Date|Scenario|Manually modified Phases"

    # Use resource path instead of hardcoded src/...
    json_file_path = _resource_path("database", f"{test_row['Scenario']}_flight_data.json")

    if not os.path.exists(json_file_path):
        # Optional: second chance for legacy names or alt locations
        alt_path = _resource_path("database", f"{test_row['Scenario']}.json")
        if os.path.exists(alt_path):
            json_file_path = alt_path
        else:
            raise FileNotFoundError(f"Database file not found: {json_file_path}")

    # Load database
    database = pd.read_json(json_file_path, orient="records", lines=True, convert_dates=False)

    database = database[database.columns.drop(list(database.filter(regex=regex_filter)))]

    # Load parameter mapping file
    optional_columns = []
    mapping_file = r"src\flight_data_evaluation_tool\results_template.json"

    if getattr(sys, "frozen", False):  # Check if running in a PyInstaller bundle
        mapping_file = sys._MEIPASS  # type: ignore
        mapping_file = os.path.join(mapping_file, "results_template.json")
    with open(mapping_file, "r", encoding="utf-8") as f:
        parameter_mapping = json.load(f)
        parameter_mapping = parameter_mapping["columns"]
        parameter_mapping = {key: value for key, value in parameter_mapping.items() if value}

    # Identify optional columns
    for column in database.columns:
        if column in parameter_mapping and parameter_mapping[column].get("optional", False):
            optional_columns.append(column)

    # Filter out optional columns for weight calculation
    required_database = database.drop(columns=optional_columns)

    counter = {"normal": 0, "non-normal": 0, "count-non-normal": 0, "transform-normal": 0, "zero-inflated": 0}

    tiered_data = {"Excellent": [], "Good": [], "Normal": [], "Poor": [], "Very Poor": [], "Not Tierable": []}

    metrics = {}

    for column in database:
        dist_type, metric, transformer, zero_inflated = tier_metric(database[column])

        metrics[column] = metric

        current_value = test_row[column]

        data_obj = {
            column: {
                "Value": current_value,
                "Mean": metric.mean(),
                "Std": metric.std(),
                "Type": dist_type,
                "Percentile": "",
                "Borders": [],
            }
        }

        if column in optional_columns:
            tiered_data["Not Tierable"].append(data_obj)
            continue

        if not transformer:
            counter[dist_type] += 1
        else:
            counter["transform-normal"] += 1

        if dist_type == "normal" and not zero_inflated:

            tier_borders = [metric.mean() + i * metric.std() for i in [-2, -1, 1, 2]]
            tier_borders = [0 if border < 0 else border for border in tier_borders]

            data_obj[column]["Borders"] = tier_borders

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

        elif dist_type == "non-normal" or dist_type == "count-non-normal" or zero_inflated:
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

            data_obj[column]["Borders"] = tier_borders
            data_obj[column]["Percentile"] = percentile

        else:
            raise ValueError("Invalid distribution type. Use 'normal', 'non-normal'.")

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

    COMPARISON = False

    if phase == "Alignment Phase" and COMPARISON:
        # Export weighting comparison for Alignment Phase
        # Prepare types and alternative names (customize as needed)
        types = np.ones(len(required_database.columns), dtype=int)  # Create array of 1s

        compare_weighting_methods_and_rank(
            required_database, types, filename="alignment_phase_weighting_comparison.xlsx"
        )

    return tiered_data, metrics, required_database


def calculate_phase_weights(data):
    """
    Calculate importance weights for flight metrics using Gini weighting method.

    This function computes MCDA (Multi-Criteria Decision Analysis) weights that
    represent the relative importance of each metric in performance evaluation.
    Constant columns (no variation) receive zero weight.

    :param data: DataFrame containing flight metrics for weight calculation.
    :type data: pandas.DataFrame
    :return: pandas Series with metric names as index and their corresponding weights
            as values. Weights sum to 1.0. Constant columns have weight 0.0.
    :rtype: pandas.Series

    .. note::
       The Gini weighting method from the crispyn library is used, which assigns
       higher weights to metrics with greater variability and discriminatory power.
       Only columns with more than one unique value receive non-zero weights.
    """
    # Identify non constant columns
    variable_cols = data.columns[data.nunique() > 1]

    # Calculate weights only for variable columns
    if len(variable_cols) > 0:
        variable_data = data[variable_cols].to_numpy()
        variable_weights = mcda_weights.gini_weighting(variable_data)

    # Build full weight vector (zero for constant columns)
    weights = pd.Series(0.0, index=data.columns)
    weights[variable_cols] = variable_weights

    return weights
