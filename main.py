#step 1: importing python libraries and modules

import os
import subprocess
from google.cloud import storage, bigquery



#step 2: configuration variables

GCP_PROJECT_ID = 'de-1st-project' 
GCS_BUCKET_NAME = 'ani_test_bucket' 
GCS_DESTINATION_BLOB_NAME = 'raw/Customers_TEST1.csv' 
LOCAL_CSV_PATH_IN_CONTAINER = '/app/data/Customers_TEST1.csv'
# This creates the full GCS URI that BigQuery will use to load data.
GCS_URI_FOR_BIGQUERY_LOAD = f"gs://{GCS_BUCKET_NAME}/{GCS_DESTINATION_BLOB_NAME}"
BIGQUERY_DATASET_ID = 'CTEST1'
BIGQUERY_TABLE_ID = 'CT'
#location of dbt project and dbt profiles in the Docker container
DBT_PROJECT_DIR_IN_CONTAINER = '/app/dbt_project/test_project_bq'
DBT_PROFILES_DIR_IN_CONTAINER = '/app/dbt_profiles'



#step3: functions for the pipeline

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
  


  #step4: main executipon block

def main():
    try:
        # Basic check to ensure the CSV file exists where we expect it inside the container.
        if not os.path.exists(LOCAL_CSV_PATH_IN_CONTAINER):
            raise FileNotFoundError(f"CSV file not found inside container at {LOCAL_CSV_PATH_IN_CONTAINER}. "
                                    "Ensure it's copied correctly by the Dockerfile.")

        #  Upload the CSV to GCS
        upload_to_gcs(GCS_BUCKET_NAME, LOCAL_CSV_PATH_IN_CONTAINER, GCS_DESTINATION_BLOB_NAME)

        # Load data from GCS into a BigQuery table
        create_or_update_bigquery_table(BIGQUERY_DATASET_ID, BIGQUERY_TABLE_ID, GCS_URI_FOR_BIGQUERY_LOAD)

        #  Run dbt transformations
        run_dbt_transformations()

        print("Pipeline executed successfully!")
    except Exception as e2:
        print(f"Pipeline failed: {e2}")
        raise # Re-raise the exception to signal failure to Cloud Run


#step5: execute the main function but only when the script is ececuted directly and not imported as a module
if __name__ == '__main__':
    main()
