FROM prefecthq/prefect:3.2.7-python3.11

COPY requirements.txt .

RUN pip install -r requirements.txt --trusted-host pypi.python.org --no-cache-dir

COPY app /opt/prefect/app
