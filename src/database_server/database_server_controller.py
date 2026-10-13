#!/usr/bin/env python3
"""
Main FastAPI script for the Database Microservice.
Implements endpoints for recognition and count entries using an MVC design.
"""

import os
import sys
from typing import Any, Dict

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

# Adjust the path if necessary based on your project structure.
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

# Import the refactored MVC classes.
from postgresql_database_ingestion import DatabaseModel, RecognitionController  # Adjust module name as needed.
from parameters import POSTGRESQL_HOST, POSTGRESQL_PORT, POSTGRESQL_DATABASE, DATABASE_PORT
from custom_logging import database_server_logger

# Define the database configuration.
DB_CONFIG = {
    'dbname': POSTGRESQL_DATABASE,
    'user': os.environ.get("POSTGRES_USER"),
    'password': os.environ.get("POSTGRES_PASSWORD"),
    'host': POSTGRESQL_HOST,
    'port': POSTGRESQL_PORT
}

app = FastAPI()


class RecognitionEntry(BaseModel):
    """
    Pydantic model for recognition entry data.
    """
    current_date: str
    current_time: str
    results: Dict[str, Any]


class CountEntry(BaseModel):
    """
    Pydantic model for count entry data.
    """
    current_date: str
    current_time: str
    results: Dict[str, int]


# Create a DatabaseModel instance and a RecognitionController instance.
db_model = DatabaseModel(DB_CONFIG)
recognition_controller = RecognitionController(db_model)


def process_recognition_entry(data: RecognitionEntry) -> None:
    """
    Process recognition entry data and store it in PostgreSQL.

    Args:
        data (RecognitionEntry): The recognition entry data.
    """
    try:
        database_server_logger.info(
            f"Processing recognition entry for {data.current_date} at {data.current_time}"
        )
        recognition_controller.process_recognition_data(
            data.current_date, data.current_time, data.results
        )
    except Exception as e:
        database_server_logger.error(f"Error processing recognition entry: {e}")


def process_count_entry(data: CountEntry) -> None:
    """
    Process count entry data and store it in PostgreSQL.

    Args:
        data (CountEntry): The count entry data.
    """
    try:
        database_server_logger.info(
            f"Processing count entry for {data.current_date} at {data.current_time}"
        )
        recognition_controller.process_detection_count(
            data.current_date, data.current_time, data.results
        )
    except Exception as e:
        database_server_logger.error(f"Error processing count entry: {e}")


@app.post("/recognition_entry")
async def recognition_entry(data: RecognitionEntry, background_tasks: BackgroundTasks):
    """
    Endpoint to handle recognition entry data.

    Args:
        data (RecognitionEntry): Recognition entry payload.
        background_tasks (BackgroundTasks): Background task manager.

    Returns:
        dict: Acknowledgement message.
    """
    database_server_logger.info(
        f"Received recognition entry for {data.current_date} at {data.current_time}"
    )
    background_tasks.add_task(process_recognition_entry, data)
    return {"message": "OK"}


@app.post("/count_entry")
async def count_entry(data: CountEntry, background_tasks: BackgroundTasks):
    """
    Endpoint to handle count entry data.

    Args:
        data (CountEntry): Count entry payload.
        background_tasks (BackgroundTasks): Background task manager.

    Returns:
        dict: Acknowledgement message.
    """
    database_server_logger.info(
        f"Received count entry for {data.current_date} at {data.current_time}"
    )
    background_tasks.add_task(process_count_entry, data)
    return {"message": "OK"}


if __name__ == "__main__":
    import uvicorn

    try:
        # Initialize the database, unified tables, and partitions.
        db_model = DatabaseModel(DB_CONFIG)
        db_model.initialize_database_and_partitions()
    except Exception as e:
        database_server_logger.error(f"Error during database initialization: {e}")
    database_server_logger.info(f"Starting FastAPI server on port {DATABASE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=DATABASE_PORT)
