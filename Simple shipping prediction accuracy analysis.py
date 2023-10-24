#The below code is a simplified way to find the accuracy of your initial predictions after you've made numerous updated predictions based on your new analysis or maybe something changed in your database
#ChatG

# Import required libraries
from zipfile import ZipFile
import os
import pandas as pd
from pandas.tseries.offsets import BDay
import matplotlib.pyplot as plt
import seaborn as sns

# Define file paths for prediction CSV files
prediction_filepaths = ["path/to/csv_1.csv", "path/to/csv_2.csv", "path/to/csv_3.csv", "path/to/csv_4.csv", "path/to/csv_5.csv", "path/to/csv_6.csv"]

# Read prediction CSVs into DataFrames
prediction_dataframes = [pd.read_csv(filepath, parse_dates=['Predicted Date', 'Order Date']) for filepath in prediction_filepaths]

# Combine prediction DataFrames
unified_prediction_df = pd.concat(prediction_dataframes, ignore_index=True)

# Load historic sales data
historic_sales_df = pd.read_csv("path/to/historic_sales.csv", parse_dates=['OrderDate', 'ShipDate'])

# Function to clean 'Planned Ship From DC' column
def clean_planned_ship_col(value):
    if pd.isnull(value) or 'TBD' in value:
        return None, None
    elif '-' in value:
        dates = value.split('-')
        start_date = pd.to_datetime(dates[0].strip(), errors='coerce')
        end_date = pd.to_datetime(dates[1].strip(), errors='coerce')
        return start_date, end_date
    else:
        date = pd.to_datetime(value.strip(), errors='coerce')
        return date, date

# Apply cleaning function to new columns
unified_prediction_df['Planned Ship Start Date'], unified_prediction_df['Planned Ship End Date'] = \
    zip(*unified_prediction_df['Planned Ship From DC'].map(clean_planned_ship_col))

# Merge historic and predicted data
combined_df = pd.merge(
    unified_prediction_df,
    historic_sales_df,
    left_on=['Order Number', 'Position Number'],
    right_on=['OrderNum', 'PositionNum'],
    how='inner'
)

# Get the first predicted date for each order and position
first_predicted_dates = combined_df.groupby(['Order Number', 'Position Number'])['Predicted Date'].min().reset_index()

# Merge to get first prediction details
first_predictions_df = pd.merge(
    combined_df,
    first_predicted_dates,
    on=['Order Number', 'Position Number', 'Predicted Date'],
    how='inner'
)

# Business day offset for date adjustments, we thought it was okay to be 1 business day off, adjust this as necessary
business_day_offset = BDay(1)

# Function to calculate shipment accuracy
def calculate_accuracy(row):
    start_date = row['Planned Ship Start Date'] - business_day_offset
    end_date = row['Planned Ship End Date'] + business_day_offset
    return start_date <= row['ShipDate'] <= end_date

# Apply accuracy calculation
first_predictions_df['Is Accurate'] = first_predictions_df.apply(calculate_accuracy, axis=1)

# Function to calculate days off for each prediction
def calculate_days_off(row):
    if row['Is Accurate']:
        return 0
    elif row['ShipDate'] < row['Planned Ship Start Date']:
        return (row['Planned Ship Start Date'] - row['ShipDate']).days
    else:
        return (row['ShipDate'] - row['Planned Ship End Date']).days

# Apply days off calculation
first_predictions_df['Days Off'] = first_predictions_df.apply(calculate_days_off, axis=1)

# Filter out worst 5% based on 'Days Off'
threshold_value = first_predictions_df['Days Off'].quantile(0.95)
filtered_df = first_predictions_df[first_predictions_df['Days Off'] <= threshold_value]

# Distribution plot for 'Days Off'
sns.set(style="whitegrid")
plt.figure(figsize=(10, 6))
sns.histplot(filtered_df['Days Off'], kde=True, bins=12)
plt.title('Distribution of Number of Days Off Our Predictions Are vs The Actual Ship Date')
plt.xlabel('Number of Days We Are Off')
plt.ylabel('Number of Order Lines')
plt.show()

# Annotated distribution plot for 'Days Off'
plt.figure(figsize=(10, 6))
ax = sns.histplot(filtered_df['Days Off'], kde=True, bins=12)
plt.title('Distribution of Number of Days Off Our Predictions Are vs The Actual Ship Date')
plt.xlabel('Number of Days We Are Off')
plt.ylabel('Number of Order Lines')
total = len(filtered_df['Days Off'])
for p in ax.patches:
    height = p.get_height()
    ax.text(p.get_x() + p.get_width() / 2., height + 3, '{:1.2f}%'.format((height / total) * 100), ha="center")
plt.show()

# Save the final DataFrame
filtered_df.to_csv("path/to/output_file.csv", index=False)
