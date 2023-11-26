import pandas as pd
import altair as alt
import geopandas as gpd

# Load the data
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

# Reshape the data to be: (Country | Indicator | Value)
source = source.melt(
    id_vars='Country', var_name='Indicator', value_name='Value')

# Remove rows with missing values
source = source.dropna(subset=['Value'])

# Add a Unit column
# source['Unit'] = source['Indicator'].apply(
#     lambda x: x[x.find("(")+1:x.find(")")])

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
    # padding={"left": 35, "top": 5, "right": 5, "bottom": 5}
).transform_filter(
    indicator_select
).add_params(
    indicator_select
).add_params(
    click_countries
)


url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
countries_shape = gpd.read_file(url)  # zipped shapefile
countries_shape = countries_shape[['NAME', 'CONTINENT', 'ISO_A3', 'geometry']]

countries_shape = countries_shape.rename(columns={'NAME': 'Country'})
countries_shape['Country'] = countries_shape['Country'].replace(
    'United States of America', 'United States')
countries_shape['Country'] = countries_shape['Country'].replace(
    'Turkey', 'Türkiye')


# Data generators for the background
sphere = alt.sphere()
graticule = alt.graticule()

basemap = alt.layer(
    alt.Chart(sphere).mark_geoshape(fill='white'),
    alt.Chart(graticule).mark_geoshape(stroke='LightGray', strokeWidth=0.5)
)

background = (
    alt.Chart(countries_shape)
    .mark_geoshape(fill='#D3D3D3')
)

# Filter the source data to include only the rows for the 'Life satisfaction' indicator
source_filtered = source[source['Indicator'] == life_satisfaction]

choropleth = (
    alt.Chart(countries_shape)
    .mark_geoshape()
    .transform_lookup(
        lookup='Country',
        from_=alt.LookupData(data=source_filtered, key='Country',
                             fields=['Value'])
    )
    .encode(
        color=alt.Color('Value:Q', legend=alt.Legend(
            orient='none',
            legendX=180, legendY=380,
            direction='horizontal',
            gradientLength=350)),
        opacity=alt.condition(click_countries, alt.value(1), alt.value(0.2)),
        tooltip=[
            alt.Tooltip('Country:N', title='Country'),
            alt.Tooltip('Value:Q', title='Life satisfaction'),
        ]
    )
    .add_params(
        click_countries
    )
)

map = background + choropleth

new_map = (basemap + map).project(
    "equalEarth"
).properties(
    width=850,
    height=450
).resolve_scale(
    color='independent'
)

mcv = new_map | chart

mcv.save('JustChart.html')
