# Helper methods to write the master's thesis

import openpyxl
import pandas as pd
from crispyn import weighting_methods as mcda_weights
import numpy as np
import os
import matplotlib.pyplot as plt


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


def create_ideal_distribution_image(filename="normal_distribution_tiers.png", output_dir="temp"):
    """
    Creates and saves an ideal normal distribution with tier borders.

    Parameters:
    -----------
    filename : str
        Name of the output file
    output_dir : str
        Directory where the image will be saved

    Returns:
    --------
    str
        Path to the saved image
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    # Generate standard normal distribution
    x = np.linspace(-4, 4, 1000)
    y = 1 / (np.sqrt(2 * np.pi)) * np.exp(-0.5 * x**2)

    # Plot the curve
    ax.plot(x, y, "k-", lw=2)

    # Define tier borders - using standard deviations for demonstration
    borders = [-2, -1, 1, 2]

    # Define tier colors
    tier_colors = {
        "Excellent": "#015220",
        "Good": "#1AA260",
        "Normal": "#f38200",
        "Poor": "#E55451",
        "Very Poor": "#C40717",
    }

    # Fill areas between borders with tier colors
    all_borders = [-4] + borders + [4]
    colors = list(tier_colors.values())

    # Fill each section with appropriate tier color
    for i in range(len(all_borders) - 1):
        section_min = all_borders[i]
        section_max = all_borders[i + 1]
        section_x = np.linspace(section_min, section_max, 100)
        section_y = 1 / (np.sqrt(2 * np.pi)) * np.exp(-0.5 * section_x**2)
        ax.fill_between(section_x, section_y, alpha=0.3, color=colors[i])

    # Add vertical lines for borders
    for border in borders:
        ax.axvline(border, color="black", linestyle="--", lw=1)

    # Add labels and title
    ax.set_title("Ideal Metric Distribution with Tier Borders")
    # Set custom ticks for x-axis
    ticks = [-2, -1, 0, 1, 2]
    labels = [
        r"$\mu-2\sigma$",
        r"$\mu-\sigma$",
        r"$\mu$",
        r"$\mu+\sigma$",
        r"$\mu+2\sigma$",
    ]
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Probability Density")

    # Annotate tier names
    tier_names = list(tier_colors.keys())
    tier_positions = [-2.75, -1.5, 0, 1.5, 2.75]  # Very Poor  # Poor  # Normal  # Good  # Excellent

    for i, (name, pos) in enumerate(zip(tier_names, tier_positions)):
        y_pos = 0.05  # Position for the text
        ax.text(pos, y_pos, name, ha="center", fontweight="bold", color=colors[i])

    # Remove unnecessary spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Save the figure
    fig_path = os.path.join(output_dir, filename)
    fig.savefig(fig_path, dpi=100, bbox_inches="tight")
    plt.close(fig)

    return fig_path


if __name__ == "__main__":
    create_ideal_distribution_image()
