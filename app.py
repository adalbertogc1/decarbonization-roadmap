import json
import numpy as np
import plotly.graph_objects as go

# Load decarbonization_info.json file
with open('decarbonization_info.json', 'r') as file:
    decarbonization_data = json.load(file)

# Load conversion factors.json file
with open('emission_factors.json', 'r') as file:
    conversion_factors = json.load(file)

########## Script for end uses forecast ########

# Extract current year, end-uses, and future years data
current_year = decarbonization_data['current_conditions']['year']
end_uses = decarbonization_data['current_conditions']['end_uses']
future_years = decarbonization_data['future_years']

# Initialize stacked bar plot data
years = list(range(current_year, 2051))
end_uses_total = {end_use: [end_uses[end_use]['EUI']] * (2050 - current_year + 1) for end_use in end_uses if not end_uses[end_use]['EUI'] <= 0}

# Apply future reductions to each end-use from current year until 2050
for year_data in future_years:
    future_year = year_data['year']
    reduction = year_data['end_uses_reduction']
    for end_use in end_uses:
        if end_uses[end_use]['EUI'] <= 0.0:
                continue
        reduction_value = reduction[end_use] / 100
        for i in range(future_year - current_year, len(years)):
            end_uses_total[end_use][i] *= (1 + reduction_value)

########## Script for carbon decarbonization roadmap  ##########

# Initialize lists to store emissions samples and uncertainty per year
emissions_samples_per_year = {year: [] for year in range(current_year, 2051)}
total_emissions_per_year = {year: 0 for year in range(current_year, 2051)}
reduction = None
reduction_uncertainty = None

# Iterate over years, interpolate per year using pad method
for year in range(current_year, 2051):
    if year == current_year:
        # Current year
        for end_use in end_uses:
            # Skip if EUI is not present
            if end_uses[end_use]['EUI'] <= 0.0:
                continue
            # Extract emission factor and conversion factor for the end use
            primary_energy = end_uses[end_use]['primary_energy']
            emission_factor = conversion_factors[primary_energy]['emission_factors'][str(year)]
            conversion_factor = conversion_factors[primary_energy]['conversion_factor']

            # Calculate emissions for each sampling
            adjusted_end_use = end_uses[end_use]['EUI']
            adjusted_uncertainty = (end_uses[end_use]['uncertainty']**2)**0.5
            samples = np.random.normal(loc=adjusted_end_use, scale=adjusted_uncertainty, size=1000)
            emissions_per_sample = samples * emission_factor * conversion_factor

            # Append emissions per sample to emissions samples list for the year
            emissions_samples_per_year[year].extend(emissions_per_sample)

            # Calculate total emissions for the year by taking into account uncertainty
            total_emissions = np.mean(emissions_per_sample)
            total_emissions_per_year[year] += total_emissions
    elif year in [year_data['year'] for year_data in future_years]:
        # Iterate over future years
        for year_data in future_years:
            future_year = year_data['year']
            if year == future_year:
                reduction = year_data['end_uses_reduction']
                reduction_uncertainty = year_data["end_uses_uncertainty"]
                for end_use in end_uses:
                    # Skip if EUI is not present
                    if end_uses[end_use]['EUI'] <= 0.0:
                        continue

                    # Extract emission factor and conversion factor for the end use
                    primary_energy = end_uses[end_use]['primary_energy']
                    emission_factor = conversion_factors[primary_energy]['emission_factors'][str(year)]
                    conversion_factor = conversion_factors[primary_energy]['conversion_factor']

                    # Calculate emissions for each sampling
                    adjusted_end_use = end_uses[end_use]['EUI'] + reduction[end_use]
                    adjusted_uncertainty = (end_uses[end_use]['uncertainty']**2 + reduction_uncertainty[end_use]**2)**0.5
                    samples = np.random.normal(loc=adjusted_end_use, scale=adjusted_uncertainty, size=1000)
                    emissions_per_sample = samples * emission_factor * conversion_factor

                    # Append emissions per sample to emissions samples list for the year
                    emissions_samples_per_year[year].extend(emissions_per_sample)

                    # Calculate total emissions for the year by taking into account uncertainty
                    total_emissions = np.mean(emissions_per_sample)
                    total_emissions_per_year[year] += total_emissions

    else:
        for end_use in end_uses:
            # Skip if EUI is not present
            if end_uses[end_use]['EUI'] <= 0.0:
                continue

            # Extract emission factor and conversion factor for the end use
            primary_energy = end_uses[end_use]['primary_energy']
            emission_factor = conversion_factors[primary_energy]['emission_factors'][str(year)]
            conversion_factor = conversion_factors[primary_energy]['conversion_factor']

            # Calculate emissions for each sampling 
            adjusted_end_use = end_uses[end_use]['EUI'] + (reduction[end_use] if reduction else 0.0)
            adjusted_uncertainty = (end_uses[end_use]['uncertainty']**2 + (reduction_uncertainty[end_use]**2 if reduction_uncertainty else 0.0))**0.5
            samples = np.random.normal(loc=adjusted_end_use, scale=adjusted_uncertainty, size=1000)
            emissions_per_sample = samples * emission_factor * conversion_factor

            # Append emissions per sample to emissions samples list for the year
            emissions_samples_per_year[year].extend(emissions_per_sample)

            # Calculate total emissions for the year by taking into account uncertainty
            total_emissions = np.mean(emissions_per_sample)
            total_emissions_per_year[year] += total_emissions

# Calculate total uncertainty per year as the standard deviation of total emissions samples
total_uncertainty_per_year = {year: np.std(emissions_samples) for year, emissions_samples in emissions_samples_per_year.items()}

# Create Plot stacked bar plot for Current and expected energy End Uses
fig = go.Figure()

# Add traces for end use forecast (stacked bar plot)
for end_use in end_uses_total:
    fig.add_trace(go.Bar(
        x=years,
        y=end_uses_total[end_use],
        name=end_use,
    ))


# Update layout for the first subplot
fig.update_layout(
    title='Energy End Uses and Decarbonization Roadmap',
    xaxis_title='Year',
    yaxis_title='Energy Consumption (kWh/m2/year)',
    yaxis=dict(title='Energy Consumption (kWh/m2/year)', side='left'),
    barmode='stack'  # Stacked bar plot mode
)

# Create a secondary y-axis for the second subplot
fig.update_layout(yaxis2=dict(title='Total Emissions (kg CO2e)', overlaying='y', side='right'))

# Add uncertainty as the width of the area on the secondary y-axis
fig.add_trace(go.Scatter(x=list(range(current_year, 2051)),
                         y=[mean - uncertainty for mean, uncertainty in zip(total_emissions_per_year.values(), total_uncertainty_per_year.values())],
                         mode='lines',
                         line=dict(width=0),
                         showlegend=False,
                         yaxis='y2'))  # Specify secondary y-axis

fig.add_trace(go.Scatter(x=list(range(current_year, 2051)),
                         y=[mean + uncertainty for mean, uncertainty in zip(total_emissions_per_year.values(), total_uncertainty_per_year.values())],
                         mode='lines',
                         fill='tonexty',
                         fillcolor='rgba(0,100,80,0.2)',
                         line=dict(width=0),
                         name='Predicted Total Emissions',
                         yaxis='y2'))  # Specify secondary y-axis

# Add trace for total emissions with uncertainty as the width of the area
fig.add_trace(go.Scatter(x=list(range(current_year, 2051)),
                         y=[70]*len(list(range(current_year, 2051))),
                         mode='lines',
                         line=dict(color='blue'),
                         name='2050 Emissions Target',
                         yaxis='y2'))


# Show plot
fig.show()
