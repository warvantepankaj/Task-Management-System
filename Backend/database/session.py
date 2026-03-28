import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import Depends
from core.config import (
    DB_PASSWORD,
    DB_USER,
    DB_NAME,
    DB_HOST,
    DB_PORT,
)


def get_db():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    try:
        yield conn
    finally:
        conn.close()
