from importlib import metadata
from flask import Flask, request, render_template, send_from_directory
import pandas as pd
import os
from data_utils import fetch_data_from_api, scrape_metadata, visualize_data
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/visualizations'  # Folder to save visualizations

@app.route('/')
def index():
    clear_visualizations_folder()  # Clear the visualizations folder
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    dataset_name = request.form['query'].replace(' ', '-').lower()
    data = fetch_data_from_api(dataset_name)
    metadata = scrape_metadata(dataset_name) 
    
    if data.empty:
        return "No data found for the given dataset."

    data_description = data.describe(include='all').to_html(classes='table table-striped', justify='center')

    filenames = visualize_data(data, dataset_name)
    
    return render_template('results.html', dataset_name=dataset_name, filenames=filenames, metadata=metadata, data_description=data_description)

@app.route('/static/visualizations/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def clear_visualizations_folder():
    folder_path = app.config['UPLOAD_FOLDER']
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)  # Remove the folder and its contents
        os.makedirs(folder_path)  # Recreate the folder
        
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)

