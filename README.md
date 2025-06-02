# Python-fundamentals
My first data engineering project!

Step 1: Programatically download a dataset from kaggle via API. Clean up the headers from special characters.

Step 2: Programatically upload it in a GCS bucket

Step 3: Create a BigQuery Dataset

Step 4: Run transformations on the data using dbt

Step 5: Automate the pipeline using Cloud Run. The pipeline runs every 2 days.


The pipeline leverages the following services:
**Google Cloud Storage (GCS)**: Stores the raw CSV file.
**BigQuery**: Data warehouse for raw data and dbt transformed views.
**dbt (data build tool)**: For defining and executing data transformations.
**Cloud Run (Job)**:Serverless compute platform for executing the Python script and dbt transformations as a single, containerized batch job.
**Cloud Scheduler**: Managed cron service to trigger the Cloud Run Job on a schedule.



Airflow resources from Panos:

https://dev.to/markbdsouza/apache-airflow-for-beginners-16o
 
https://theaisummer.com/apache-airflow-tutorial/
 
https://blog.adnansiddiqi.me/using-apache-airflow-etl-to-fetch-and-analyze-btc-data/
 
https://www.franciscoyira.com/post/data-pipelines-cloud-intro-airflow-docker/

installing-airflow-on-the-windows-subsystem-for-linux 
