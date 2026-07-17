# This script sets up a connection to a MySQL database using SQLAlchemy.

import os
from sqlalchemy import create_engine
from dotenv  import load_dotenv

# Load environment variables from a .env file
load_dotenv()
DB_USER = os.getenv("MYSQL_USER")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
DB_HOST = os.getenv("MYSQL_HOST")
DB_PORT = os.getenv("MYSQL_PORT")
DB_NAME = os.getenv("MYSQL_DATABASE")
VIEW_NAME = os.getenv("MYSQL_VIEW_NAME")  # This can be a table or view name in your MySQL database

# Construct the database URL for SQLAlchemy
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


engine = create_engine(
    DATABASE_URL,
    echo=False,        # Set to True to log SQL queries
    pool_pre_ping=True # Checks if the connection is still alive
)

"""
Function to load data from a MySQL view in chunks which will be used for ingestion into a vector database.

This is useful for large datasets that cannot be loaded into memory all at once.

"""

def load_view(view_name: str, chunk_size: int = 1000):
    query = f"SELECT * FROM `{view_name}`"

    return pd.read_sql(
        query,
        engine,
        chunksize=chunk_size
    )