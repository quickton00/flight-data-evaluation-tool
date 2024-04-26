import matplotlib.pyplot as plt
import pandas as pd
import math

def plot_values(x_values: pd.DataFrame, y_values: pd.DataFrame, title: str, x_label: str, y_label: str, plot_names=None):
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
    :param plot_names: parameter to rename plots via a dictionary, defaults to None
    :type plot_names: dict, optional
    """

    plt.figure(figsize=(20, 12))  # Set figure size (width, height)

    if isinstance(y_values, pd.DataFrame):
        for column_name, column_data in y_values.items():
            if plot_names is not None:
                column_name = plot_names[column_name]

            plt.plot(x_values.tolist(), column_data.tolist(), marker='', linestyle='-', linewidth=0.5, label=column_name)

    else:
        plt.plot(x_values.tolist(), y_values.tolist(), marker='', linestyle='-', linewidth=0.5, label=y_values.name)    # better without usin pandas series

    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend(loc='upper right')
    plt.grid(linestyle='--', linewidth=0.5)



if __name__ == "__main__":
    # Open the log file
    with open(r"C:\Users\Admin\Downloads\SoyuzData\Data Flights\1st week ITA\FDL-2022-11-10-12-56-04_15Dima_ITA_0000.log", 'r') as file:
    #with open(r"C:\Users\Admin\Downloads\SoyuzData\Data Flights\3rd week ITB\FDL-2022-11-24-14-10-48_15Dima_ITB_0000.log", 'r') as file:

        lines = file.readlines()

        data = []

        # Iterate over each line in the file
        for line in lines:
            if line.startswith("#"):
                continue
            if line.startswith('SimTime'):
                columns = map(str.strip, line.split(';'))
                columns = filter(None, columns)
                continue

            # Split the line using ';' as delimiter
            values = map(str.strip, line.split(';'))
            values = filter(None, values)
            values = [float(value) for value in values]
            data.append(values)

    data_frame = pd.DataFrame(data, columns=columns)

    # calculate additional value sets
    # lateral offset off Port Position from x-Axis
    data_frame['Lateral Offset'] = (data_frame['Port Pos.y [m]']**2 + data_frame['Port Pos.z [m]']**2)**0.5

    # data set for ideal aproach velocity
    data_frame['Ideal Approach Vel'] = -data_frame['COG Pos.x [m]']/200                                         # via CoG, maybe use Port for consistency?
    data_frame.loc[data_frame['COG Pos.x [m]'] < 20, 'Ideal Approach Vel'] = -0.1                               # via CoG, maybe use Port for consistency?

    # data set to draw approach cone in plots
    data_frame['Approach Cone'] = data_frame['Port Pos.x [m]']*math.tan(10*math.pi/180)

    # data set fot the max allowed rotational angle
    data_frame.loc[data_frame['COG Pos.x [m]'] < 20, 'Max Rot Angle'] = 1.5

    # data set for the may allowed rotaional velocity
    data_frame.loc[data_frame['COG Pos.x [m]'] < 20, 'Max Rot Velocity'] = 0.15


    # plot translational offset (Port to Port)
    fig = plot_values(data_frame['SimTime'],
                data_frame[['Port Pos.x [m]', 'Port Pos.y [m]', 'Port Pos.z [m]', 'Lateral Offset']],
                'Translational Offset Port-Vessel/Port-Station',  'Simulation time (s)', 'Translational Offset (m)',
                {'Port Pos.x [m]': 'Trans. Offset X', 'Port Pos.y [m]': 'Trans. Offset Y', 'Port Pos.z [m]': 'Trans. Offset Z', 'Lateral Offset': 'Lateral Offset'})

    plt.fill_between(data_frame['SimTime'].tolist(), data_frame['Approach Cone'].tolist(), (data_frame['Approach Cone']*-1).tolist(), color='#d3d3d3', label='Lateral Approach Cone')
    plt.legend(loc='upper right')

    # plot translational velocity (CoG Vessel)
    plot_values(data_frame['SimTime'], data_frame[['COG Vel.x [m]', 'COG Vel.y [m]', 'COG Vel.z [m]', 'Ideal Approach Vel']], 'Translational Velocity (CoG Vessel)', 'Simulation time (s)', 'Translational Velocity (m/s)')

    # plot rotaional angles
    plot_values(data_frame['SimTime'],
                data_frame[['Rot Angle.x [deg]', 'Rot Angle.y [deg]', 'Rot Angle.z [deg]']],
                'Angular Position of the Vessel', 'Simulation time (s)', 'Rotational Angle (°)',
                {'Rot Angle.x [deg]': 'Roll Position', 'Rot Angle.y [deg]': 'Yaw Position', 'Rot Angle.z [deg]': 'Pitch Position'})

    plt.fill_between(data_frame['SimTime'].tolist(), data_frame['Max Rot Angle'].tolist(), (data_frame['Max Rot Angle']*-1).tolist(), color='#d3d3d3', label='Max Rotaional Angle')
    plt.legend(loc='upper right')

    # plot rotational rates
    plot_values(data_frame['SimTime'],
                data_frame[['Rot. Rate.x [deg/s]', 'Rot. Rate.y [deg/s]', 'Rot. Rate.Z [deg/s]']], 'Rotation Velocities', 'Simulation time (s)', 'Rotational Rate (°/s)',
                {'Rot. Rate.x [deg/s]': 'Roll Rate', 'Rot. Rate.y [deg/s]': 'Yaw Rate', 'Rot. Rate.Z [deg/s]': 'Pitch Rate'})

    plt.fill_between(data_frame['SimTime'].tolist(), data_frame['Max Rot Velocity'].tolist(), (data_frame['Max Rot Velocity']*-1).tolist(), color='#d3d3d3', label='Max Rot Velocity')
    plt.legend(loc='upper right')

    # plot translational controller inputs
    plot_values(data_frame['SimTime'], data_frame[['THC.x', 'THC.y', 'THC.z']], 'THC',  'Simulation time (s)', 'Translational Controller Inputs')

    # plot rotaional controller inputs
    plot_values(data_frame['SimTime'], data_frame[['RHC.x', 'RHC.y', 'RHC.z']], 'RHC',  'Simulation time (s)', 'Rotational Controller Inputs')

    # plot tank mass over time
    plot_values(data_frame['SimTime'], data_frame['Tank mass [kg]'], 'Tank Mass over Simulation Time', 'Simulation Time', 'Tank Mass (kg)')

    plt.show()  # Display the plot