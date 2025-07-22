# Helper methods to write the master's thesis

import openpyxl
import pandas as pd
from crispyn import weighting_methods as mcda_weights


def compare_weighting_methods_and_rank(data, types, filename="weighting_comparison.xlsx"):
    """
    Compare all weighting methods and create a ranking for all flight metrics.
    Results are saved to an Excel file.
    """

    weighting_methods_set = [
        mcda_weights.entropy_weighting,
        mcda_weights.critic_weighting,
        mcda_weights.gini_weighting,
        mcda_weights.merec_weighting,
        mcda_weights.stat_var_weighting,
        mcda_weights.idocriw_weighting,
        mcda_weights.angle_weighting,
        mcda_weights.coeff_var_weighting,
    ]

    matrix = data.to_numpy()
    cols = data.columns

    df_weights = pd.DataFrame(index=cols)

    for weight_type in weighting_methods_set:
        if weight_type.__name__ in ["cilos_weighting", "idocriw_weighting", "angle_weighting", "merec_weighting"]:
            weights = weight_type(matrix, types)
        else:
            weights = weight_type(matrix)

        method_name = weight_type.__name__[:-10].upper().replace("_", " ")
        df_weights[method_name] = weights

    # Write all results to Excel
    with pd.ExcelWriter(filename) as writer:
        df_weights.to_excel(writer, sheet_name="Weights")

    print(f"Comparison results saved to {filename}")
