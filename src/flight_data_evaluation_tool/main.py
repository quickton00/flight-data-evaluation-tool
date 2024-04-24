import matplotlib.pyplot as plt
import pandas as pd

def plot_values(x_values: pd.DataFrame, y_values: pd.DataFrame, title: str, x_label: str, y_label: str):
    """
    Function to plot x-values against y-values.
    The y-values can either be one list or a dataframe of multiple columns.
    Each column will be displayed as a new curve.

    :param x_values: values for the x-axis
    :type x_values: pd.DataFrame
    :param y_values: values for the y-axis
    :type y_values: pd.DataFrame
    :param title: title of the plot
    :type title: str
    :param x_label: label for the x-axis
    :type x_label: str
    :param y_label: label for the y-axis
    :type y_label: str
    """

    plt.figure(figsize=(20, 12))  # Set figure size (width, height)

    if isinstance(y_values, pd.DataFrame):
        for column_name, column_data in y_values.items():
            plt.plot(x_values.tolist(), column_data.tolist(), marker='', linestyle='-', linewidth=0.5, label=column_name)
    else:
        plt.plot(x_values.tolist(), y_values.tolist(), marker='', linestyle='-', linewidth=0.5, label=y_values.name)    # better without usin pandas series

    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend(loc='upper right')
    plt.grid(linestyle='--', linewidth=0.5)


if __name__ == "__main__":

    # Define variables to store extracted values
    sim_times = []
    cog_positions = []
    port_positions = []
    cog_velocities = []
    port_velocities = []
    rot_angles = []
    rot_rates = []
    rot_rates_vlcs = []
    tank_masses = []
    thc = []
    rhc = []

    # Open the log file
    with open(r"C:\Users\Admin\Downloads\SoyuzData\Data Flights\1st week ITA\FDL-2022-11-09-14-24-52_14Jonida_ITA_0000.log", 'r') as file:
        lines = file.readlines()

        data = []

        # Iterate over each line in the file
        for line in lines:
            if line.startswith("#"):
                continue
            if line.startswith('SimTime'):
                columns = map(str.strip, line.split(';')[:-1])
                continue

            # Split the line using ';' as delimiter
            values = map(str.strip, line.split(';')[:-1])
            values = [float(value) for value in values]
            data.append(values)

    data_frame = pd.DataFrame(data, columns=columns)


    # convert into pandas data frames

    thc = pd.DataFrame(thc, columns=['x', 'y', 'z'])
    rhc = pd.DataFrame(rhc, columns=['x', 'y', 'z'])

    plot_values(data_frame['SimTime'], data_frame[['THC.x', 'THC.y', 'THC.z']], 'THC',  'Simulation time (s)', 'Translational Controller Inputs')
    plot_values(data_frame['SimTime'], data_frame[['RHC.x', 'RHC.y', 'RHC.z']], 'RHC',  'Simulation time (s)', 'Rotational Controller Inputs')
    plot_values(data_frame['SimTime'], data_frame['Tank mass [kg]'], 'Tank Mass over Simulation Time', 'Simulation Time', 'Tank Mass (kg)')

    plt.show()  # Display the plot