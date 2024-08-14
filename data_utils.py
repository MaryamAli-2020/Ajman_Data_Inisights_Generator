import datetime
import requests
import pandas as pd
import os
import plotly.express as px
from bs4 import BeautifulSoup
import json 
import re
from datetime import datetime

def fetch_data_from_api(dataset_name):
    # Construct the API URL
    url = f"https://data.ajman.ae/api/explore/v2.1/catalog/datasets/{dataset_name}/records?limit=-1"
    
    try:
        # Fetch data from the API
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        data = response.json()
        
        # Log the entire response for debugging
        print("API Response:", data)
        
        # Extract records from the response
        records = data.get('results', [])
        
        if not records:
            print("No records found in the response.")
            return pd.DataFrame()  # Return an empty DataFrame if no records
        
        # Normalize JSON records into a DataFrame
        df = pd.DataFrame(records)
        
        # Log the DataFrame for debugging
        # print("DataFrame:", df.head())
        
        return df

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error


def scrape_metadata(dataset_name):
    url = f'https://data.ajman.ae/explore/dataset/{dataset_name}/information/'
    
    try:
        # Fetch the web page
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract the description
        description_element = soup.select_one('.cat_description')
        description = description_element.get_text(strip=True, separator='\n') if description_element else 'N/A'
        print(f"Description: {description}")
        if description == 'N/A':
            description_element = soup.select_one('.ods-dataset-metadata-block__description p')
            description = description_element.get_text(strip=True) if description_element else 'N/A'

        
        # Find the div with the ctx-dataset-schema attribute
        dataset_div = soup.find('div', attrs={'ctx-dataset-schema': True})

        if dataset_div:
            # Extract the JSON string from the ctx-dataset-schema attribute
            ctx_dataset_schema = dataset_div.get('ctx-dataset-schema', '{}')
            # Clean up the JSON string by removing extra backslashes
            ctx_dataset_schema = ctx_dataset_schema.replace(r'\u2013', '-')  # Convert unicode dash
            ctx_dataset_schema = ctx_dataset_schema.replace(r'\\', '\\')  # Unescape backslashes

            print(f"Cleaned JSON string: {ctx_dataset_schema}")

            try:
                modified_pattern = r'"modified":\s*"([^"]*)"'
                records_count_pattern = r'"records_count":\s*(\d+)'
                theme_pattern = r'"theme":\s*\[(.*?)\]'

                # Extract values
                modified_match = re.search(modified_pattern, ctx_dataset_schema)
                records_count_match = re.search(records_count_pattern, ctx_dataset_schema)
                theme_match = re.search(theme_pattern, ctx_dataset_schema)

                # Store values in variables
                modified = modified_match.group(1) if modified_match else None
                records_count = int(records_count_match.group(1)) if records_count_match else None
                theme = theme_match.group(1) if theme_match else None

                modified = datetime.fromisoformat(modified)
                modified = modified.strftime("%B %d, %Y, %I:%M %p UTC")
                
            except json.JSONDecodeError as e:
                records_count = 'N/A'
                theme = 'N/A'
                modified = 'N/A'
        
        else:
            records_count = 'N/A'
            theme = 'N/A'
            modified = 'N/A'

        return {
            'num_records': records_count,
            'description': description,
            'last_modified': modified,
            'theme': theme
        }

    except requests.exceptions.RequestException as e:
        # print(f"Request failed: {e}")
        return {
            'num_records': 'N/A',
            'description': 'N/A',
            'last_modified': 'N/A',
            'theme': 'N/A'
        }

    
def convert_to_datetime(data):
    # Identify columns with keywords 'date' or 'time' in their names
    date_time_keywords = ['date', 'time']
    for col in data.columns:
        if any(keyword in col.lower() for keyword in date_time_keywords):
            try:
                data[col] = pd.to_datetime(data[col])
            except (ValueError, TypeError):
                print(f"Column {col} could not be converted to datetime.")
    return data

def visualize_data(data, dataset_name):
    if data.empty:
        print("No data to visualize.")
        return None

    # Convert columns with date/time keywords to datetime
    data = convert_to_datetime(data)

    num_cols = data.select_dtypes(include=['number']).columns
    cat_cols = data.select_dtypes(include=['object', 'category']).columns
    date_cols = data.select_dtypes(include=['datetime']).columns

    output_dir = 'static/visualizations'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Create an empty list to collect all plots
    figures = []
    filenames = []

    # Visualize numeric columns with histograms and scatter plots
    if not num_cols.empty:
        for idx, column in enumerate(num_cols):
            fig = px.histogram(data, x=column, title=f'Distribution of {column}')
            figures.append(fig)
        
        # Pairwise scatter plots if multiple numeric columns
        if len(num_cols) > 1:
            for i in range(len(num_cols)):
                for j in range(i+1, len(num_cols)):
                    fig = px.scatter(data, x=num_cols[i], y=num_cols[j],
                                     title=f'Scatter plot of {num_cols[i]} vs {num_cols[j]}')
                    figures.append(fig)

    # Visualize categorical columns with bar plots
    if not cat_cols.empty:
        for column in cat_cols:
            value_counts = data[column].value_counts()
            if not value_counts.empty:
                df_value_counts = value_counts.reset_index()
                df_value_counts.columns = [column, 'Count']
                fig = px.bar(df_value_counts, x=column, y='Count',
                             title=f'Count of {column}', labels={column: column, 'Count': 'Count'})
                figures.append(fig)

    # Create visualizations for date columns
    if not date_cols.empty:
        for column in date_cols:
            data_sorted = data.sort_values(by=column)
            fig = px.line(data_sorted, x=column, y=data_sorted.index, title=f'Trend of {column}')
            fig.update_layout(title=f'Trend of {column}', xaxis_title=column, yaxis_title='Index')
            figures.append(fig)

    # Save each figure as an HTML file
    for i, fig in enumerate(figures):
        filename = f'visualization_{dataset_name}_{i}.html'
        file_path = os.path.join(output_dir, filename)
        fig.write_html(file_path)
        filenames.append(filename)
    
    return filenames
