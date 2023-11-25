import pandas as pd
import altair as alt
import geopandas as gpd

source = pd.read_excel('OECD_Data.xlsx')

# Convert the units row (row 1) into a dictionary
units = source.iloc[0].to_dict()

# Create a dictionary for simplified names of the units
simplified_units = {
    "Percentage": "%",
    "Ratio": "ratio",
    "US Dollar": "$",
    "Average score": "average score",
    "Years": "years",
    "Micrograms per cubic metre": "µg/m³",
    "Hours": "hours"
}

# Remove the units row from the source data
source = source.iloc[1:]

# Reset the DataFrame index
source.reset_index(drop=True, inplace=True)

# Add units to each of the indicators
for column in source.columns:
    unit = units[column]
    if unit in simplified_units:
        source.rename(
            columns={column: f"{column} ({simplified_units[unit]})"}, inplace=True)

source = source.melt(
    id_vars='Country', var_name='Indicator', value_name='Value')

source = source.dropna(subset=['Value'])

life_satisfaction = "Life satisfaction (average score)"

# Create a dropdown selection menu for the Indicator
indicator_dropdown = alt.binding_select(
    options=source['Indicator'].unique().tolist(),
    name="Indicator: "
)

indicator_select = alt.selection_point(
    fields=['Indicator'],
    bind=indicator_dropdown,
    name='Select',
    value=life_satisfaction
)

click_countries = alt.selection_point(fields=["Country"])

# Create the bar chart
chart = alt.Chart(source).mark_bar().encode(
    x=alt.X('Country:N', sort='-y', axis=alt.Axis(labelAngle=-45)),
    y=alt.Y('Value:Q', title='', axis=alt.Axis(
        format=',.0f')),
    color=alt.Color('Value:Q', scale=alt.Scale(
        scheme='yellowgreenblue'), legend=None),
    opacity=alt.condition(click_countries, alt.value(1), alt.value(0.2)),
    tooltip=[alt.Tooltip('Country:N'), alt.Tooltip(
        'Indicator:N'), alt.Tooltip('Value:Q', format=',')],
).properties(
    width=750,
    height=300,
    padding={"left": 35, "top": 5, "right": 5, "bottom": 5}
).transform_filter(
    indicator_select
).add_params(
    indicator_select
).add_params(
    click_countries
)

chart.save('JustChart.html')
