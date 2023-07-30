import requests
import datetime
import os
import psycopg2
from datetime import datetime, timedelta
# from dotenv import load_dotenv
# load_dotenv()
from airflow import DAG 
from airflow.operators.python_operator import PythonOperator

dbname='postgres'
user='postgres'
password='postgres'
host = 'postgres'
port=5432

created_at_=datetime.utcnow().isoformat()
# task 1
def fetch_trending_tags():
    base_url = "https://api.stackexchange.com/2.3"
    # Keep the current date for each row in the fetched data
    created_at=datetime.utcnow().isoformat()

    # start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    # end_date = datetime.datetime.today().strftime('%Y-%m-%d')

    endpoint = "/tags"
    params = {
        "order": "desc",
        "sort": "popular",
        "site": "stackoverflow",
        # "key": api_key
        # "pagesize": 100
    }

    response = requests.get(base_url + endpoint, params=params)

    if response.status_code == 200:
        trending_tags_data = response.json()
        trending_tags = trending_tags_data["items"]

        # Add the 'created_at' timestamp to each row
        for tag in trending_tags:
            tag["created_at"] = created_at

        return trending_tags
    else:
        print("Failed to fetch trending tags:", response.status_code, response.text)
        return []

def load_data_to_postgres():
    connection_params = {
        'dbname': dbname,
        'user':user,
        'password':password,
        'host':host,
        'port':port 
        }

    try:
        conn = psycopg2.connect(**connection_params)
        cursor = conn.cursor()
        print('fetchinG Data for ',created_at_)
        trending_tags = fetch_trending_tags()
        print('Fetching Done')
        for tag in trending_tags:
            # Modify this part to match your table schema and column names
            sql = "INSERT INTO trending_tags (tag_name, tag_count, created_at) VALUES (%s, %s, %s)"
            data = sql,(tag["name"], tag["count"], tag["created_at"])
            cursor.execute(sql, (tag["name"], tag["count"], tag["created_at"]))
            print('executed',data)

        conn.commit()
        conn.close()

    except psycopg2.Error as e:
        print(f"Error: {e}")
        # Handle any exception or error, e.g., log the error or send an alert


# load_data_to_postgres()

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 7, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG('trending_tags_ingestion',
         schedule_interval='@hourly',
         default_args=default_args,
         catchup=False) as dag:

    # Task to fetch trending tags
    # fetch_trending_tags_task = PythonOperator(
    #     task_id='fetch_trending_tags',
    #     python_callable=fetch_trending_tags
    # )

    # Task to load data into PostgreSQL
    load_data_to_postgres_task = PythonOperator(
        task_id='load_data_to_postgres',
        python_callable=load_data_to_postgres,
        op_args=[],
        provide_context=True,
    )

    # Define task dependencies
    # fetch_trending_tags_task >> load_data_to_postgres_task

    load_data_to_postgres_task
