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

indicators = source['Indicator'].unique().tolist()

# Create a dropdown selection menu for the Indicator
indicator_dropdown = alt.binding_select(
    options=indicators,
    name="Indicator: "
)

indicator_select = alt.selection_point(
    fields=['Indicator'],
    bind=indicator_dropdown,
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
    title="Bar Chart of OECD Indicators by Country",
    width=750,
    height=400,
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

legend = alt.Legend(
    title=life_satisfaction,
    orient='none',
    legendX=200, legendY=380,
    direction='horizontal',
    gradientLength=400,
    values=list(range(5, 9))
)

# Filter the source data to include only the rows for the 'Life satisfaction' indicator
source_filtered = source[source['Indicator'] == life_satisfaction]

choropleth = (
    alt.Chart(countries_shape)
    .mark_geoshape()
    .transform_lookup(
        lookup='Country',
        from_=alt.LookupData(data=source_filtered, key='Country',
                             fields=['Value',
                                     'Indicator'])
    )
    .encode(
        color=alt.Color('Value:Q', legend=legend),
        opacity=alt.condition(click_countries, alt.value(1), alt.value(0.2)),
        tooltip=[
            alt.Tooltip('Country:N', title='Country'),
            alt.Tooltip('Indicator:N', title="Indicator"),
            alt.Tooltip('Value:Q', title="Value"),
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
    title="Interactive Global Map of Life Satisfaction",
    width=850,
    height=450
).resolve_scale(
    color='independent'
)

mcv = chart | new_map


brush = alt.selection_interval(resolve='global')

life_satisfaction = 'Life satisfaction (average score)'

base = alt.Chart(source).mark_circle(size=100).encode(
    y=life_satisfaction,
    color=alt.condition(brush, 'Origin', alt.ColorValue('gray'), legend=None)
).add_params(
    brush
).properties(
    width=250,
    height=250
)

charts = []

for i in range(len(indicators)):
    # sub = source.dropna(subset = [indicators[num], life_satisfaction], inplace=False)

    # # Calculate the distance of each point from the origin (0,0), adding a small constant to avoid taking the square root of 0
    # sub['distance'] = (source[life_satisfaction])**2 + (source[indicators[i]])**2

    chart1 = base.transform_filter(
        (alt.datum[indicators[i]] != 0) & (alt.datum[life_satisfaction] != 0)
    ).encode(
        x=indicators[i],
        # color=alt.Color('distance:Q', scale=alt.Scale(scheme='viridis'), legend=None),
        # color=alt.Color(f'{life_satisfaction}:Q', scale=alt.Scale(scheme='blues'), legend=None),
        tooltip=['Country:N', f'{life_satisfaction}:Q', f'{indicators[i]}:Q']
    )

    charts.append(chart1)


alt.vconcat(
    alt.hconcat(*charts[:4]),
    alt.hconcat(*charts[4:8]),
    alt.hconcat(*charts[8:12]),
    alt.hconcat(*charts[12:]),
    title='Index of Multiple Deprivation Dashboard'
)

mcv.save('JustChart.html')
