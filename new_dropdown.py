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

brush = alt.selection_interval(resolve='global', empty=True, clear=True)

color_scale = alt.condition(
    brush,
    alt.Color(f'{life_satisfaction}:Q', scale=alt.Scale(
        scheme='yellowgreenblue'), legend=None),
    alt.ColorValue('gray'),
)

base = alt.Chart(source).mark_circle(size=150).encode(
    y=alt.Y(life_satisfaction, scale=alt.Scale(domain=(4, 9))),
    color=color_scale
).properties(
    width=400,
    height=200
).add_params(
    brush
)

my_indicators = {
    "Household net wealth ($)": (50000, 1000000),
    "Employment rate (%)": (30, 100),
    "Quality of support network (%)": (75, 100),
    "Educational attainment (%)": (30, 100),
    "Feeling safe walking alone at night (%)": (30, 100),
    "Self-reported health (%)": (30, 100),
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
    )

    charts.append(chart1)


scatters = alt.vconcat(
    alt.hconcat(*charts[:3]),
    alt.hconcat(*charts[3:]),
    title='Life Satisfaction compared to other Indicators'
).resolve_scale(
    color='independent'
)

# Create a bar chart from the brush selection of the scatter plot
# Calculate aggregate statistics

oecd_total = source[source['Country'] ==
                    'OECD - Total'][life_satisfaction].iloc[0]


n = 21  # Replace with your desired maximum number of bars

bar_chart = alt.Chart(source).mark_bar().transform_filter(
    brush
).transform_calculate(
    adjusted_life_satisfaction='datum["{}"] - {}'.format(
        life_satisfaction, oecd_total),
    tooltip='datum.Country + ": " + (datum.adjusted_life_satisfaction > 0 ? "+" : "-") + format(abs(datum.adjusted_life_satisfaction), ",")'
).transform_window(
    rank='rank()',
    sort=[alt.SortField('adjusted_life_satisfaction', order='descending')]
).transform_filter(
    alt.datum.rank <= n
).encode(
    x=alt.X('adjusted_life_satisfaction:Q',
            title='Difference from OECD Life Satisfaction total'),
    y=alt.Y('Country:N', sort='-x'),
    color=alt.condition(
        alt.datum.adjusted_life_satisfaction > 0,
        alt.value('steelblue'),  # The color for positive differences
        alt.value('orange')  # The color for negative differences
    ),
    tooltip='tooltip:N'
).properties(
    width=200,
    height=450,
)

# Append the bar chart to the existing scatter plot
scatters |= bar_chart

scatters = scatters.resolve_scale(
    color='independent'
)

scatters.save("JustChart.html")

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
