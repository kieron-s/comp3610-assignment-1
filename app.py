import streamlit as st
import pandas as pd
import plotly.express as px
import os 

@st.cache_data
def load_data():
    trip_path = "data/raw/yellow_tripdata_2024-01.parquet"
    zone_path = "data/raw/taxi_zone_lookup.csv"
    
    df = pd.read_parquet(trip_path)
    zones_df = pd.read_csv(zone_path)

    critical_columns = ['tpep_pickup_datetime', 'tpep_dropoff_datetime', 'PULocationID', 'DOLocationID', 'fare_amount']
    df = df.dropna(subset=critical_columns)
    df = df[(df['trip_distance'] > 0) & (df['fare_amount'] > 0) & (df['fare_amount'] <= 500) &
            (df['tpep_dropoff_datetime'] > df['tpep_pickup_datetime'])]
    
    df['tpep_pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime'])
    df['pickup_date'] = df['tpep_pickup_datetime'].dt.date
    df['pickup_hour'] = df['tpep_pickup_datetime'].dt.hour
    df['pickup_dayofweek'] = df['tpep_pickup_datetime'].dt.day_name()

    return df, zones_df

df, zones_df = load_data()

st.title('NYC Yellow Taxi Trips Dashboards - January 2024')
st.markdown('This dashboard analyzes ~3 million yellow taxi trips for January 2024, including pickups, fares, distances, payments and more.')

st.sidebar.header('Filters')
date_range = st.sidebar.date_input(
    "Date Range",
    value=(df['pickup_date'].min(), df['pickup_date'].max()),
    min_value=df['pickup_date'].min(),
    max_value=df['pickup_date'].max()
)

hour_range = st.sidebar.slider(
    "Hour Range (0-23)",
    0, 23, (0, 23)
)

payment_options = [1, 2, 3, 4, 5]
payment_labels = {1: "Credit card", 2: "Cash", 3: "No charge", 4: "Dispute", 5: "Unknown"}
selected_payments = st.sidebar.multiselect(
    "Payment Types",
    options=payment_options,
    format_func=lambda x: payment_labels[x],
    default=payment_options
)

filtered_df = df[
    (df['pickup_date'].between(date_range[0], date_range[1])) &
    (df['pickup_hour'].between(hour_range[0], hour_range[1])) &
    (df['payment_type'].isin(selected_payments))
]

st.header("Key Summary Metrics")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Trips", f"{len(filtered_df):,}")
col2.metric("Avg Fare", f"${filtered_df['fare_amount'].mean():.2f}")
col3.metric("Total Revenue", f"${filtered_df['total_amount'].sum():,.0f}")
col4.metric("Avg Distance", f"{filtered_df['trip_distance'].mean():.1f} mi")
col5.metric("Avg Duration", f"{(filtered_df['tpep_dropoff_datetime'] - filtered_df['tpep_pickup_datetime']).dt.total_seconds().mean() / 60:.1f} min")

tab1, tab2, tab3 = st.tabs(["Zones & Payments", "Fares & Distances", "Time Patterns"])

with tab1:
    top_zones = filtered_df.groupby('PULocationID').size().nlargest(10).reset_index(name='trip_count')
    top_zones = top_zones.merge(zones_df[['LocationID', 'Zone']], left_on='PULocationID', right_on='LocationID')
    fig1 = px.bar(top_zones, x='Zone', y='trip_count', title='Top 10 Busiest Pickup Zones')
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown("**Insight**: Airport zones and Manhattan locations like Midtown dominate, showing high travel demand from tourists in early 2024.")

    payment_counts = filtered_df['payment_type'].value_counts(normalize=True).reset_index(name='percentage')
    payment_counts['percentage'] *= 100
    payment_counts['payment_type'] = payment_counts['payment_type'].map(payment_labels)
    fig4 = px.pie(payment_counts, values='percentage', names='payment_type', title='Payment Type Breakdown')
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown("**Insight**: Credit cards account for ~75-80% of trips, highlighting the rapid shift to cashless payments in NYC taxis during this period.")

with tab2:
    hourly_fare = filtered_df.groupby('pickup_hour')['fare_amount'].mean().reset_index(name='avg_fare')
    fig2 = px.line(hourly_fare, x='pickup_hour', y='avg_fare', title='Average Fare by Hour of Day')
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("**Insight**: t, Fares are highest during early mornings which apparently is normal behaviour for taxi services, likely due to airport trips)")

    fig3 = px.histogram(filtered_df, x='trip_distance', nbins=50, title='Distribution of Trip Distances')
    fig3.update_layout(xaxis_range=[0, 30])
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown("**Insight**: Most trips are short, which is to be expected in a dense urban environment like NYC. However, there is a long tail of longer trips, likely to/from airports or outer boroughs.")

with tab3:
    weekly = filtered_df.groupby(['pickup_dayofweek', 'pickup_hour']).size().unstack(fill_value=0)
    fig5 = px.imshow(weekly, title='Trips by Day of Week and Hour', color_continuous_scale='YlOrRd')
    st.plotly_chart(fig5, use_container_width=True)
    st.markdown("**Insight**: Weekdays are structured around work hours 7am and 5pm, while weekends show more activity in the afternoons and evenings, reflecting leisure travel patterns.")