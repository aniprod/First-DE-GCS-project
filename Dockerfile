# step 1: Choose a base image
FROM python:3.9-slim-buster



# step2: Set the working directory inside the container
WORKDIR /app



# step 3: Copy the requirements.txt file and install Python dependencies
#    A 'requirements.txt' file lists all Python packages:
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt



#step 4: Copy the rest of your application code and dbt project files
#    The '.' on the left means "everything in the current local directory"
#    The '.' on the right means "to the current working directory (/app) inside the container"
COPY . .



#step 5: Define the command to run when the container starts
#    This tells Cloud Run (or Docker) what to execute to start your pipeline
CMD ["python", "main.py"]