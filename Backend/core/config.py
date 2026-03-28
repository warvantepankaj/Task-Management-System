import os
from dotenv import load_dotenv
from pathlib import Path

ENV_PATH = Path(
    "C:\\Pankaj's Space\\Projects\\FAST-API\\Task_Management_System\\Backend\\.env"
)
load_dotenv(ENV_PATH)

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

DB_NAME=os.getenv("DATABASE_NAME")
DB_USER=os.getenv("DATABASE_USER")
DB_PASSWORD=os.getenv("DATABASE_PASSWORD")
DB_HOST=os.getenv("DATABASE_HOST")
DB_PORT=os.getenv("DATABASE_PORT")

if not DB_PASSWORD:
    raise RuntimeError("DB_PASSWORD is not set in environment")
