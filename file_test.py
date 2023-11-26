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


indicators = list(source.columns)[1:]

indicator_dropdown = alt.binding_select(options=indicators, name="Indicator: ")

indicator_param = alt.param(value=indicators[0], bind=indicator_dropdown)

click = alt.selection_point(encodings=['x'])

color_scale = alt.condition(
    click,
    alt.Color('y:Q', scale=alt.Scale(scheme='yellowgreenblue'), legend=None),
    alt.value('lightgray')
)

# Source of the cartography background
url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
countries_shape = gpd.read_file(url)  # zipped shapefile
countries_shape = countries_shape[['NAME', 'CONTINENT', 'ISO_A3', 'geometry']]

countries_shape = countries_shape.rename(columns={'NAME': 'Country'})

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

click_countries = alt.selection_multi(fields=["Country"])

life_satisfaction = 'Life satisfaction (average score)'

choropleth = (
    alt.Chart(countries_shape)
    .mark_geoshape()
    .transform_lookup(
        lookup='Country',
        from_=alt.LookupData(data=source, key='Country',
                             fields=[life_satisfaction])
    )
    .encode(
        color=alt.Color(f"{life_satisfaction}:Q", legend=alt.Legend(
            orient='none',
            legendX=180, legendY=380,
            direction='horizontal',
            gradientLength=350)),
        opacity=alt.condition(click_countries, alt.value(1), alt.value(0.2)),
        tooltip=[
            alt.Tooltip('NAME:N', title='Country'),
            alt.Tooltip(f'{life_satisfaction}:Q'),
        ]
    )
    .add_params(
        click_countries
    )
)

map = background + choropleth


new_chart = alt.Chart(source).mark_bar().encode(
    x=alt.X('Country:N', sort='-y', axis=alt.Axis(labelAngle=-45), title=''),
    y=alt.Y('y:Q', title=''),
    color=alt.Color('y:Q', scale=alt.Scale(
        scheme='yellowgreenblue'), legend=None),
    opacity=alt.condition(click_countries, alt.value(1), alt.value(0.2)),
    tooltip='tooltip:N',
).properties(
    width=800,
    height=400
).transform_calculate(
    y=f'datum[{indicator_param.name}]'  # Variable Y axis
).transform_calculate(
    tooltip='datum.Country + ": " + format(datum.y, ",")'
).transform_filter(
    'isValid(datum.y)'  # Removes NaN values
).add_params(
    indicator_param  # Add dropdown parameter
).add_params(
    click_countries  # Add dropdown parameter
)

color_map = new_chart | (
    basemap + map).project("equalEarth").properties(width=700, height=400)

color_map.save('JustChart.html')
