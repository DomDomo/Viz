from vega_datasets import data
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

# Convert columns to numbers and add units to each of the indicators
for column in source.columns[1:]:
    # Convert the data types to numbers
    source[column] = pd.to_numeric(source[column],
                                   errors='coerce')
    unit = units[column]
    if unit in simplified_units:
        source.rename(
            columns={column: f"{column} ({simplified_units[unit]})"}, inplace=True)


indicators = list(source.columns)[1:]

life_satisfaction = 'Life satisfaction (average score)'

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

base = alt.Chart(source).mark_circle(size=100).encode(
    y=alt.Y(life_satisfaction, scale=alt.Scale(domain=(0, 10)))
).properties(
    width=300,
    height=200
)

my_indicators = {
    "Household net wealth ($)": (50000, 1000000),
    "Employment rate (%)": (20, 100),
    "Quality of support network (%)": (70, 100),
    "Educational attainment (%)": (20, 100),
    "Feeling safe walking alone at night (%)": (20, 100),
    "Self-reported health (%)": (20, 100),
}


def get_correct_domain(indi):
    has_custom = my_indicators.get(indi, False)

    if has_custom:
        return alt.X(indi, scale=alt.Scale(domain=has_custom))

    return alt.X(indi)


charts = []
for indi in my_indicators.keys():
    chart1 = base.transform_filter(
        alt.datum[indi] != None
    ).encode(
        x=get_correct_domain(indi),
        shape='Country:N',
        opacity=alt.condition(click_countries, alt.value(1), alt.value(0.2)),
        tooltip=['Country:N', f'{life_satisfaction}:Q',
                 f'{indi}:Q']
    ).resolve_scale(
        color='independent'
    ).add_params(
        click_countries
    ).interactive()

    charts.append(chart1)


scatters = alt.vconcat(
    alt.hconcat(*charts[:3]),
    alt.hconcat(*charts[3:]),
    title='Life Satisfaction compared to other Indicators'
)

# Reshape the data to be: (Country | Indicator | Value)
source = source.melt(
    id_vars='Country', var_name='Indicator', value_name='Value')

# Remove rows with missing values
source = source.dropna(subset=['Value'])

# Add a Unit column
# source['Unit'] = source['Indicator'].apply(
#     lambda x: x[x.find("(")+1:x.find(")")])

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

# mcv = (chart | new_map) | scatters


mcv = alt.vconcat(
    alt.hconcat(scatters),
    alt.hconcat(chart, new_map),
)


mcv.save("JustChart.html")
