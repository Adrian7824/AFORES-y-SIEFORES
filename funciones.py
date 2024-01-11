'''
The functions are for calculating the returns and storing the 
results for graphs and tables
'''
from datetime import timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import pandas as pd


def adjust_to_business_day(dt, datos):
    """
    Adjusts a date to the nearest previous business day if it's not in the dataset.
    """
    while dt not in datos.index:
        dt -= timedelta(days=1)
    return dt


def subtract_years_adjusted(dt, years, datos):
    """
    Subtracts years from a date and adjusts to the nearest previous business day.
    """
    try:
        adjusted_date = dt.replace(year=dt.year - years)
    except ValueError:
        if dt.month == 2 and dt.day == 29:
            adjusted_date = dt.replace(year=dt.year - years, day=28)
        else:
            raise
    return adjust_to_business_day(adjusted_date, datos)


def get_business_days_within_6_months(dt, datos):
    """
    Get a list of business days between dt and dt - 6 months from the dataset.
    """
    six_months_ago = dt - pd.DateOffset(months=6)
    adjusted_start = adjust_to_business_day(six_months_ago, datos)
    return datos[adjusted_start:dt].index.tolist()


def calculate_return(datos, t, siefore, n):
    """
    Calculate the return, adjusting for business days.
    """
    if n not in [3, 5, 10]:
        raise ValueError("n must be 3, 5, or 10.")
    look_back_date = subtract_years_adjusted(t, n, datos)
    return ((datos.loc[t, siefore] / datos.loc[look_back_date, siefore]) ** (360 / (n * 360))) - 1


def calculate_weighted_returns(datos, p, n):
    """
    Calculate weighted average returns for all siefores.
    """
    results = {}
    for siefore in datos.columns:
        time = get_business_days_within_6_months(datos.index[-1], datos)
        weighted_sum = sum(weight * sum(calculate_return(datos, t, siefore,
                           n[i]) for t in time) / len(time) for i, weight in enumerate(p))
        results[siefore] = round(weighted_sum * 100, 2)

    return pd.DataFrame(list(results.items()), columns=['Siefore', 'Weighted Average Return'])


# Function to calculate returns for each siefore and for n = 3, 5, and 10 years, then store them in DataFrames
def calculate_and_store_returns(datos):
    """
    Calculate returns for each siefore for n = 3, 5, and 10 years and store them in separate DataFrames.

    :param datos: DataFrame with dates as index and siefores as columns.
    :return: Dictionary of DataFrames, each DataFrame contains returns for a specific siefore.
    """
    siefores_returns = {}
    n_values = [3, 5, 10]

    for siefore in datos.columns:
        time = get_business_days_within_6_months(datos.index[-1], datos)
        returns_data = {n: [] for n in n_values}

        for t in time:
            for n in n_values:
                return_value = calculate_return(datos, t, siefore, n)
                returns_data[n].append(return_value)

        siefores_returns[siefore] = pd.DataFrame(returns_data, index=time)

    return siefores_returns


def plot_line_graphs(returns_dict):
    """
    Plot line graphs for the returns data in the dictionary of DataFrames.

    :param returns_dict: Dictionary of DataFrames, each containing returns for a specific siefore.
    """
    for siefore, df in returns_dict.items():
        plt.figure(figsize=(10, 6))
        for column in df.columns:
            plt.plot(df.index, df[column], label=f'{column} Años')

        # Format the x-axis to show months
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator())

        plt.title(f'Retornos en el tiempo de {siefore}')
        plt.xlabel('Fecha')
        plt.ylabel('Retorno')
        plt.legend()
        plt.grid(True)
        plt.show()


def load_and_process_excel(sheet_name, sheet_name_inv):
    """
    Load and process Excel data for a given sheet name.

    :param sheet_name: Name of the sheet to be loaded from the Excel files.
    :return: Processed DataFrame.
    """
    # Load data from Excel files
    # Note: The file paths need to be adjusted to the actual location of your Excel files
    precio = pd.read_excel(
        './Datos/precios_de_bolsa_de_las_siefores.xls', sheet_name=sheet_name, skiprows=1)
    try:
        precio = precio.set_index('FECHA').fillna(0)
    except KeyError:
        precio = precio.set_index('Fecha').fillna(0)



    # The file path or sheet name might need to be adjusted depending on the specific Excel file structure
    inv = pd.read_excel('./Datos/Inversiones_cuadro_cartera.xlsx',
                        sheet_name=sheet_name_inv, skiprows=4, skipfooter=3)
    inv = inv.iloc[:, 1:]

    # Fill forward NaN values
    inv[inv.columns[0]] = inv[inv.columns[0]].ffill()

    # Create a MultiIndex from the first two columns
    index = pd.MultiIndex.from_tuples(
        list(zip(inv.iloc[:, 0], inv.iloc[:, 1])))
    inv.set_index(index, inplace=True)

    # Drop the first two columns used for the MultiIndex
    inv = inv.drop(columns=inv.columns[:2])

    return precio, inv


def plot_pie_chart(data, column_name):
    """
    Plot a pie chart for the specified column from a DataFrame.

    Parameters:
    data (DataFrame): The DataFrame containing the data to plot.
    column_name (str): The name of the column for which to plot the pie chart.
    """

    # Function to generate percentage labels
    def autopct_generator(pct, threshold):
        """
        Create a function to format the percentage labels on the pie chart.

        Parameters:
        pcts (iterable): An iterable of the percentage values.
        threshold (float): The minimum percentage value to display.

        Returns:
        function: A function that will format the percentage labels.
        """
        def inner_autopct(pct):
            return ('%.1f%%' % pct) if pct >= threshold else ''
        return inner_autopct

    # Function to create pie charts
    def create_pie(ax, category_data, threshold=2):
        """
        Create a pie chart on the given axis with the provided data.

        Parameters:
        ax (Axes): The matplotlib Axes object to draw the chart on.
        category_data (Series): The data for the pie chart slices.
        threshold (float): The threshold for displaying percentage labels.
        """
        # Filter out values that are exactly 0 after calculating the percentage
        pct_data = 100 * category_data / category_data.sum()
        category_data = category_data[pct_data > 0]
        pct_data = pct_data[pct_data > 0]

        labels = [label if pct >= threshold else '' for label,
                  pct in zip(category_data.index, pct_data)]
        autopct = autopct_generator(pct_data, threshold)

        wedges, texts, autotexts = ax.pie(
            category_data,
            labels=labels,
            autopct=autopct,
            startangle=140
        )

        # Create a list of labels for slices smaller than the threshold
        legend_labels = [f'{label}: {pct:.1f}%' for label, pct in zip(
            category_data.index, pct_data) if pct < threshold]
        legend_wedges = [wedge for wedge, pct in zip(
            wedges, pct_data) if pct < threshold]

        if legend_wedges:
            ax.legend(legend_wedges, legend_labels,
                      title=f"Inversiones < {threshold}%", loc="best", bbox_to_anchor=(1, 0, 0, 0))

        return wedges, texts, autotexts

    # Create figure and define GridSpec
    fig = plt.figure(figsize=(15, 12))
    gs = gridspec.GridSpec(2, 3, figure=fig)

    # Create pivoted DataFrame and filter out rows with zero value
    df = data.groupby(level=0).sum()
    filtered_df = df[df[column_name] != 0][column_name]

    # Large pie chart
    ax0 = fig.add_subplot(gs[0, 1:2])
    if not filtered_df.empty:
        create_pie(ax0, filtered_df)
        ax0.set_title(f'Inversiones de {column_name}', fontsize=25)
        ax0.axis('equal')
    else:
        ax0.axis('off')

    # Pie chart for "Gubernamental"
    ax1 = fig.add_subplot(gs[1, 0])
    gubernamental_data = data.loc['Gubernamental',
                                  column_name] if 'Gubernamental' in data.index else pd.Series()
    if not gubernamental_data.empty:
        create_pie(ax1, gubernamental_data)
        ax1.set_title('Gubernamental', fontsize=20)
        ax1.axis('equal')
    else:
        ax1.axis('off')

    # Pie chart for "Privados Nacionales"
    ax2 = fig.add_subplot(gs[1, 2])
    privados_data = data.loc['Privados Nacionales',
                             column_name] if 'Privados Nacionales' in data.index else pd.Series()
    if not privados_data.empty:
        create_pie(ax2, privados_data)
        ax2.set_title('Privados Nacionales', fontsize=20)
        ax2.axis('equal')
    else:
        ax2.axis('off')

    # Deactivate empty subplots
    for ax in [gs[0, 0], gs[1, 1]]:
        fig.add_subplot(ax).axis('off')

    # Display the chart
    plt.show()
