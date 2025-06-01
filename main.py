#step 1: importing python libraries and modules

import os
import subprocess
from google.cloud import storage, bigquery
import kaggle
#import zipfile
import shutil
import pandas as pd



#step 2: configuration variables

GCP_PROJECT_ID = 'de-1st-project' 
GCS_BUCKET_NAME = 'ani_test_bucket' 
GCS_DESTINATION_BLOB_NAME = 'raw/Customers_TEST1.csv' 
#LOCAL_CSV_PATH_IN_CONTAINER = '/app/data/Customers_TEST1.csv'
# This creates the full GCS URI that BigQuery will use to load data.
GCS_URI_FOR_BIGQUERY_LOAD = f"gs://{GCS_BUCKET_NAME}/{GCS_DESTINATION_BLOB_NAME}"
BIGQUERY_DATASET_ID = 'CTEST1'
BIGQUERY_TABLE_ID = 'CT'
#location of dbt project and dbt profiles in the Docker container
DBT_PROJECT_DIR_IN_CONTAINER = '/app/dbt_project/test_project_bq'
DBT_PROFILES_DIR_IN_CONTAINER = '/app/dbt_profiles'

#kaggle variables
KAGGLE_USERNAME = os.environ.get('KAGGLE_USERNAME')
KAGGLE_KEY = os.environ.get('KAGGLE_KEY')
KAGGLE_DATASET_ID = "datascientistanna/customers-dataset"
YOUR_KAGGLE_CSV_FILENAME = "Customers.csv" 

# This is a temporary directory inside the container where the Kaggle dataset will be downloaded and unzipped.
# This directory is cleaned up after the pipeline runs.
TEMP_DOWNLOAD_DIR = "/tmp/kaggle_data" 



#step3: functions for the pipeline


def clean_csv_columns(input_path, output_path):
    print(f"Cleaning column names in {input_path}...")
    df = pd.read_csv(input_path)

    # Define a mapping for problematic column names
    column_rename_map = {
        'Annual Income ($)': 'Annual_Income_USD',
        'Spending Score (1-100)': 'Spending_Score_1_100' # Example for another possible problematic column
    }

    # Rename columns using the map
    df.rename(columns=column_rename_map, inplace=True)

    # Optional: A more general cleanup for any other special characters in column names
    # This replaces any character that is NOT a letter, number, or underscore with an underscore.
    df.columns = df.columns.str.replace(r'[^a-zA-Z0-9_]', '_', regex=True).str.strip('_')

    # Save the cleaned DataFrame to a new CSV file
    df.to_csv(output_path, index=False)
    print(f"Cleaned CSV saved to {output_path}")
    return output_path

#function to download the kaggle dataset
def download_kaggle_dataset(dataset_id, download_path, csv_filename):
    print(f"Authenticating Kaggle for dataset: {dataset_id}")
    os.environ['KAGGLE_USERNAME'] = KAGGLE_USERNAME
    os.environ['KAGGLE_KEY'] = KAGGLE_KEY
    kaggle.api.authenticate()

 # 1. Ensure the download directory exists before downloading
    os.makedirs(download_path, exist_ok=True)

    # 2. Use the Kaggle API to directly download and unzip
    # This function handles finding, downloading the zip, and unzipping it into the 'path'
    kaggle.api.dataset_download_files(dataset_id, path=download_path, unzip=True)

    print(f"Downloaded Kaggle dataset '{dataset_id}' and unzipped to {download_path}")


    downloaded_csv_path = os.path.join(download_path, csv_filename)
    if not os.path.exists(downloaded_csv_path):
        # This part helps debug if the CSV name is wrong or nested in a folder
        print(f"Error: Expected CSV file '{csv_filename}' not found after download/unzip in {download_path}.")
        print("Files found in download directory:")
        for root, dirs, files in os.walk(download_path):
            for file in files:
                print(os.path.relpath(os.path.join(root, file), download_path))
        raise FileNotFoundError(f"Expected CSV file '{csv_filename}' not found. Please check 'YOUR_KAGGLE_CSV_FILENAME' variable.")

    print(f"Kaggle dataset '{dataset_id}' downloaded and '{csv_filename}' extracted to {downloaded_csv_path}")
    return downloaded_csv_path



#function to upload the file from the container's local filesystem to the bucket
def upload_to_gcs(bucket_name, source_file_path, destination_blob_name):
    storage_client = storage.Client(project=GCP_PROJECT_ID)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    print(f"File uploaded successfully to gs://{bucket_name}/{destination_blob_name}.")

#function to create/update a BigQuery dataset and load data from GCS into a table 
def create_or_update_bigquery_table(dataset_id, table_id, gcs_uri):
    print(f"Loading data from {gcs_uri} to BigQuery table {dataset_id}.{table_id}.")
    bigquery_client = bigquery.Client(project=GCP_PROJECT_ID)
    dataset_ref = bigquery_client.dataset(dataset_id)    

#check if dataset exists, create if it doesn't
    try:
      bigquery_client.get_dataset(dataset_ref)
      print(f" BigQuery dataset {dataset_id} already exists")
    except:
      dataset = bigquery.Dataset(dataset_ref)
      dataset.location = 'EU' #dataset location must match dbt profile and source?
      bigquery_client.create_dataset(dataset)
      print(f"BigQuery Dataset {dataset_id} created.")


#Configure the BigQuery load job
    job_configuration = bigquery.LoadJobConfig(
      source_format=bigquery.SourceFormat.CSV,
      skip_leading_rows= 1,
      autodetect=True,
      write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
) 

#Execute the load job
    load_job = bigquery_client.load_table_from_uri(gcs_uri, dataset_ref.table(table_id), job_config=job_configuration)
    load_job.result()
    print(f'Data loaded to bigQuery table {dataset_id}.{table_id}')


#dbt transformation
def run_dbt_transformations():
  print(f'Running dbt transformation from {DBT_PROFILES_DIR_IN_CONTAINER}')
  try:
        dbt_command = [
    'dbt',
    'run',
    '--profile', BIGQUERY_DATASET_ID,
    '--project-dir', DBT_PROJECT_DIR_IN_CONTAINER,
    '--profiles-dir', DBT_PROFILES_DIR_IN_CONTAINER
        ]
        result = subprocess.run(dbt_command, capture_output=True, text=True, check=True)
        print (result.stdout)
  except subprocess.CalledProcessError as e:
      print('dbt run failed')
      print(e.stdout)
      print(e.stderr)
      raise e #Reraise the exception to indicate failure
  except Exception as e1:
      print(f'An unexpected error occured during dbt run: {e1}')
      raise e1
  


  #step4: main execution block

def main():
    #try:
        # Basic check to ensure the CSV file exists where we expect it inside the container.
        #if not os.path.exists(LOCAL_CSV_PATH_IN_CONTAINER):
            #raise FileNotFoundError(f"CSV file not found inside container at {LOCAL_CSV_PATH_IN_CONTAINER}. "
                                    #"Ensure it's copied correctly by the Dockerfile.")


     try:
        # 1. Download Kaggle Dataset to a local temporary path inside the container
        # This calls the new function and gets the path to the extracted CSV.
        local_csv_file_path = download_kaggle_dataset(
            KAGGLE_DATASET_ID, 
            TEMP_DOWNLOAD_DIR, 
            YOUR_KAGGLE_CSV_FILENAME
        )

           # 2. Clean CSV Columns BEFORE uploading to GCS
        # This function takes the *already downloaded* local_raw_csv_path
        # It reads it, renames columns, and writes a *NEW* cleaned CSV file
        # to a *different* path (e.g., /tmp/kaggle_data/cleaned_Customers.csv)
        cleaned_csv_path = clean_csv_columns(
          local_csv_file_path, # This is the path to the original, downloaded CSV
          os.path.join(TEMP_DOWNLOAD_DIR, f"cleaned_{YOUR_KAGGLE_CSV_FILENAME}") # This is the path for the NEW, cleaned CSV
        )
        # At this point, you have TWO files locally:
        # - The original: /tmp/kaggle_data/Customers.csv
        # - The cleaned: /tmp/kaggle_data/cleaned_Customers.csv (which is cleaned_csv_path)

        #  Upload the CSV to GCS
        upload_to_gcs(GCS_BUCKET_NAME, cleaned_csv_path, GCS_DESTINATION_BLOB_NAME)

        # Load data from GCS into a BigQuery table
        create_or_update_bigquery_table(BIGQUERY_DATASET_ID, BIGQUERY_TABLE_ID, GCS_URI_FOR_BIGQUERY_LOAD)

        #  Run dbt transformations
        run_dbt_transformations()

        print("Pipeline executed successfully!")
     except Exception as e2:
        print(f"Pipeline failed: {e2}")
        raise # Re-raise the exception to signal failure to Cloud Run
     finally:
         if os.path.exists(TEMP_DOWNLOAD_DIR):
            shutil.rmtree(TEMP_DOWNLOAD_DIR)
            print(f"Cleaned up temporary directory: {TEMP_DOWNLOAD_DIR}")

#step5: execute the main function but only when the script is ececuted directly and not imported as a module
if __name__ == '__main__':
    main()
