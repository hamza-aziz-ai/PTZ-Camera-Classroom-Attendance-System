import os
import sys
import threading
import time
import requests
import psycopg2
from psycopg2 import sql
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security.api_key import APIKeyQuery
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Ensure the parent directory is on the path for module imports.
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from parameters import (
    POSTGRESQL_HOST,
    POSTGRESQL_PORT,
    POSTGRESQL_DATABASE,
    LECTURE_TIMES,
    PTZ_CAMS
)
from custom_logging import api_logger

# Read PostgreSQL credentials from the environment.
POSTGRESQL_USERNAME = os.environ.get("POSTGRES_USER")
POSTGRESQL_PASSWORD = os.environ.get("POSTGRES_PASSWORD")

API_KEY = os.environ.get("API_KEY")

# Database configuration for PostgreSQL.
DB_CONFIG = {
    'dbname': POSTGRESQL_DATABASE,
    'user': POSTGRESQL_USERNAME,
    'password': POSTGRESQL_PASSWORD,
    'host': POSTGRESQL_HOST,
    'port': POSTGRESQL_PORT
}

app = FastAPI()

# API Key dependency using FastAPI's APIKeyQuery.
api_key_query = APIKeyQuery(name="api_key")

def get_api_key(api_key: str = Depends(api_key_query)) -> bool:
    """
    Dependency to validate the provided API key.
    """
    if api_key == API_KEY:
        api_logger.info("API key authentication successful.")
        return True
    else:
        api_logger.error("Invalid API key provided.")
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid API Key")

def fetch_data_as_dict(cursor: psycopg2.extensions.cursor) -> List[Dict[str, Any]]:
    """
    Convert cursor results into a list of dictionaries.

    Args:
        cursor: psycopg2 cursor after executing a query.

    Returns:
        List of dictionaries mapping column names to their values.
    """
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    api_logger.error(f"HTTP Exception {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP Exception", "detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    api_logger.error(f"Unhandled Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)},
    )

def parse_date(date_str: str) -> Tuple[datetime, str]:
    """
    Parse the input date string (expected in 'DD-MM-YYYY').
    Returns a tuple: (datetime object, formatted date 'YYYY-MM-DD').
    """
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        api_logger.warning("Invalid date format")
        raise HTTPException(status_code=400, detail="Invalid date format. Please use 'DD-MM-YYYY'.")
    if dt.date() > datetime.now().date():
        api_logger.warning("Future dates are not available.")
        raise HTTPException(
            status_code=400,
            detail="Future dates are not allowed. Please provide a past or present date."
        )
    return dt, dt.strftime("%Y-%m-%d")


@app.get("/lecture_data", response_model=Dict[str, Any])
def get_lecture_data(lecture_id: int, lecture_date: str, classroom_name: str, is_authorized: bool = Depends(get_api_key)) -> Dict[str, Any]:
    """
    Fetch all data from attendance_log, lecture_summary, student_detection_count,
    and distinct person_ids for students and faculty for a given lecture_id and lecture_date.

    Time fields are formatted in 12-hour format and face_matching_distance is formatted
    to 3 decimal places with a leading zero if applicable.
    """
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid API Key")
    try:
        dt, postgres_lecture_date = parse_date(lecture_date)
        year = dt.year

        results = {}

        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # Fetch data from lecture_summary partition with formatted lecture_start_time and lecture_end_time.
                cursor.execute(
                    f"""
                    SELECT to_char(lecture_start_time, 'HH12:MI:SS AM') as lecture_start_time,
                           to_char(lecture_end_time, 'HH12:MI:SS AM') as lecture_end_time,
                           detected_student_count, recognized_student_count, recognized_faculty_count, attendance_valid 
                    FROM lecture_summary_{year} 
                    WHERE lecture_id = %s AND lecture_date = %s AND classroom_name = %s;
                    """,
                    (lecture_id, postgres_lecture_date, classroom_name)
                )
                lecture_summary_data = fetch_data_as_dict(cursor)

                # Fetch distinct student person_ids.
                cursor.execute(
                    f"""
                    SELECT DISTINCT person_id 
                    FROM attendance_log_{year} 
                    WHERE lecture_id = %s AND classroom_name = %s AND recognition_date = %s AND role = 'student';
                    """,
                    (lecture_id, classroom_name, postgres_lecture_date)
                )
                distinct_student_ids_data = fetch_data_as_dict(cursor)

                # Fetch distinct faculty person_ids.
                cursor.execute(
                    f"""
                    SELECT DISTINCT person_id 
                    FROM attendance_log_{year} 
                    WHERE lecture_id = %s AND classroom_name = %s AND recognition_date = %s AND role = 'faculty';
                    """,
                    (lecture_id, classroom_name, postgres_lecture_date)
                )
                distinct_faculty_ids_data = fetch_data_as_dict(cursor)

                # Convert the list of dicts to flat lists of person_ids.
                students = [row["person_id"] for row in distinct_student_ids_data]
                faculties = [row["person_id"] for row in distinct_faculty_ids_data]

                # Combine lecture_summary with faculties and students.
                if lecture_summary_data:
                    # Assuming one record is returned.
                    lecture_summary_record = lecture_summary_data[0]
                else:
                    lecture_summary_record = {}
                lecture_summary_record["faculties"] = faculties
                lecture_summary_record["students"] = students

                results["lecture_summary"] = lecture_summary_record

                # Fetch data from attendance_log partition with formatted recognition_time and face_matching_distance.
                cursor.execute(
                    f"""
                    SELECT person_id, 
                           to_char(recognition_time, 'HH12:MI:SS AM') as recognition_time,
                           ltrim(to_char(face_matching_distance, '9999990.000')) as face_matching_distance,
                           role 
                    FROM attendance_log_{year} 
                    WHERE lecture_id = %s AND recognition_date = %s AND classroom_name = %s;
                    """,
                    (lecture_id, postgres_lecture_date, classroom_name)
                )
                results["attendance_log"] = fetch_data_as_dict(cursor)

                # Fetch data from student_detection_count partition with formatted detection_time.
                cursor.execute(
                    f"""
                    SELECT detection_count, to_char(detection_time, 'HH12:MI:SS AM') as detection_time
                    FROM student_detection_count_{year} 
                    WHERE lecture_id = %s AND detection_date = %s AND classroom_name = %s;
                    """,
                    (lecture_id, postgres_lecture_date, classroom_name)
                )

                results["student_detection_count"] = fetch_data_as_dict(cursor)

        api_logger.info(f"Data successfully retrieved for lecture_id {lecture_id} on {lecture_date}.")
        return results

    except HTTPException as he:
        raise he
    except Exception as e:
        api_logger.error(f"Error fetching lecture data: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


def get_current_lecture(recognition_time_str: str) -> Optional[int]:
    """
    Determine the current lecture based on the recognition time.

    LECTURE_TIMES should be a dict mapping lecture_id to a tuple of
    (lecture_start_time, lecture_end_time) in "HH:MM" format.

    Args:
        recognition_time_str: Time string in "HH:MM:SS" format.

    Returns:
        The lecture_id if found, otherwise None.
    """
    try:
        recognition_time = datetime.strptime(recognition_time_str, "%H:%M:%S").time()
    except ValueError as ve:
        api_logger.error(
            f"Invalid time format for recognition_time: {recognition_time_str}. Expected HH:MM:SS. {ve}"
        )
        return None

    for lecture_id, (start_str, end_str) in LECTURE_TIMES.items():
        lecture_start = datetime.strptime(start_str, "%H:%M:%S").time()
        lecture_end = datetime.strptime(end_str, "%H:%M:%S").time()
        if lecture_start <= recognition_time <= lecture_end:
            return lecture_id
    return None

def process_attendance_data(rows) -> List[Dict[str, Any]]:
    payload = list()

    for row in rows:
        record = {
            "entity": row.get("person_id"),
            "classroom_name": row.get("classroom_name"),
            "cam_ip": row.get("camera_ip"),
            "date": (row.get("recognition_date").strftime("%d-%m-%Y")
                     if hasattr(row.get("recognition_date"), "strftime")
                     else row.get("recognition_date")),
            "time": (row.get("recognition_time").strftime("%H:%M:%S")
                     if hasattr(row.get("recognition_time"), "strftime")
                     else row.get("recognition_time")),
            "similarity": float(row.get("face_matching_distance", 0))
        }
        payload.append(record)

    return payload

@app.post("/manual_attendance_update", response_model=Dict[str, Any])
def manual_attendance_update(lecture_id: int, lecture_date: str, classroom_name: str, is_authorized: bool = Depends(get_api_key)):
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid API Key")

    payload = list()
    try:
        dt, postgres_lecture_date = parse_date(lecture_date)
        year = dt.year

        partition_table = f"attendance_log_{year}"

        # Fetch attendance_log rows for this classroom.
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                query = sql.SQL("""
                        SELECT * FROM {} 
                        WHERE lecture_id = %s AND recognition_date = %s AND classroom_name = %s;
                    """).format(sql.Identifier(partition_table))
                cursor.execute(query, (lecture_id, postgres_lecture_date, classroom_name))
                rows = fetch_data_as_dict(cursor)

        # Convert rows into payload format.
        payload = process_attendance_data(rows)
        # Create recognition object to be sent to API
        recognition_object = {"recognition": payload}

        # Get the API endpoint for this classroom.
        endpoint = PTZ_CAMS[classroom_name]["sim_attendance_api_endpoint"]
        if not endpoint:
            return {"message": f"No API endpoint configured for classroom {classroom_name}."}

        # Post the payload to the classroom's API endpoint.
        if payload:
            response = requests.post(url=endpoint, json=recognition_object, timeout=60)
            if response.status_code == 200:
                resp_json = response.json()
                status = resp_json.get("data", {}).get("status", "")
                if "Status:Attendance Successfully Marked" in status:
                    # Update attendance_valid flag in lecture_summary for this classroom.
                    with psycopg2.connect(**DB_CONFIG) as conn:
                        with conn.cursor() as cursor:
                            update_query = """
                                UPDATE lecture_summary
                                SET attendance_valid = true
                                WHERE lecture_id = %s AND lecture_date = %s AND classroom_name = %s;
                            """
                            cursor.execute(update_query, (lecture_id, postgres_lecture_date, classroom_name))
                        conn.commit()
                    return {
                        "message": f"Attendance marked successfully for lecture {lecture_id}, classroom {classroom_name} on {lecture_date}.",
                        "recognition": payload
                    }
                elif "Status:Faculty Code Miss Match" in status:
                    return {
                        "message": f"Attendance not marked for lecture {lecture_id}, classroom {classroom_name} on {lecture_date}: Faculty Code Miss Match.",
                        "recognition": payload
                    }
                else:
                    return {
                        "message": f"Unexpected response status for classroom {classroom_name}",
                        "Status": status,
                        "recognition": payload
                    }
            else:
                return {
                    "message": f"Failed to post attendance data for classroom {classroom_name}.",
                    "Status code": response.status_code,
                    "Response": response.text,
                    "recognition": payload
                }
        else:
            return {
                "message": f"No attendance data to post for lecture {lecture_id} of classroom {classroom_name} for date {lecture_date}",
                "recognition": payload
            }

    except Exception as e:
        return {
            "exception": f"Error in sending attendance data for classroom {classroom_name}: {e}",
            "recognition": payload
        }


def send_attendance_data_for_classroom(classroom_name: str) -> None:
    """
    Fetch attendance_log data for a specific classroom for the current lecture,
    convert each row into the required payload format, and send the data to the
    classroom's configured API endpoint. If attendance is marked successfully,
    update the corresponding lecture_summary record's attendance_valid flag.

    Args:
        classroom_name: The name of the classroom.
    """
    try:
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        current_year = now.year

        # Determine the current lecture slot.
        lecture_id = get_current_lecture(current_time)
        if lecture_id is None:
            api_logger.error(f"No valid lecture slot found for current time, {classroom_name}.")
            return

        partition_table = f"attendance_log_{current_year}"
        payload = []

        # Fetch attendance_log rows for this classroom.
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                query = sql.SQL("""
                    SELECT * FROM {} 
                    WHERE lecture_id = %s AND recognition_date = %s AND classroom_name = %s;
                """).format(sql.Identifier(partition_table))
                cursor.execute(query, (lecture_id, current_date, classroom_name))
                rows = fetch_data_as_dict(cursor)

        # Convert rows into payload format.
        payload = process_attendance_data(rows)
        # Create recognition object to be sent to API
        recognition_object = {"recognition": payload}

        # Get the API endpoint for this classroom.
        endpoint = PTZ_CAMS[classroom_name]["sim_attendance_api_endpoint"]
        if not endpoint:
            api_logger.error(f"No API endpoint configured for classroom {classroom_name}. Skipping.")
            return

        if payload:
            # Post the payload to the classroom's API endpoint.
            response = requests.post(url=endpoint, json=recognition_object, timeout=60)
            if response.status_code == 200:
                resp_json = response.json()
                status = resp_json.get("data", {}).get("status", "")
                if "Status:Attendance Successfully Marked" in status:
                    # Update attendance_valid flag in lecture_summary for this classroom.
                    with psycopg2.connect(**DB_CONFIG) as conn:
                        with conn.cursor() as cursor:
                            update_query = """
                                UPDATE lecture_summary
                                SET attendance_valid = true
                                WHERE lecture_id = %s AND lecture_date = %s AND classroom_name = %s;
                            """
                            cursor.execute(update_query, (lecture_id, current_date, classroom_name))
                        conn.commit()
                    api_logger.info(f"Attendance marked successfully for lecture {lecture_id}, classroom {classroom_name} on {current_date}.")
                elif "Status:Faculty Code Miss Match" in status:
                    api_logger.info(f"Attendance not marked for lecture {lecture_id}, classroom {classroom_name} on {current_date}: Faculty Code Miss Match.")
                else:
                    api_logger.error(f"Unexpected response status for classroom {classroom_name}: {status}")
            else:
                api_logger.error(f"Failed to post attendance data for classroom {classroom_name}. Status code: {response.status_code}, Response: {response.text}")
        else:
            api_logger.info(f"No attendance data to post for lecture {lecture_id} of classroom {classroom_name} for date {current_date}")

    except Exception as e:
        api_logger.error(f"Error in sending attendance data for classroom {classroom_name}: {e}")


def start_scheduler() -> BackgroundScheduler:
    """
    Start a background scheduler that runs a separate job for each classroom.

    For every classroom defined in CLASSROOM_API_ENDPOINTS, a job is scheduled to
    run every minute that calls send_attendance_data_for_classroom.

    Returns:
        The running BackgroundScheduler instance.
    """
    scheduler = BackgroundScheduler()
    for classroom_name in PTZ_CAMS.keys():
        trigger = CronTrigger(minute="*/5", hour="9-17")
        scheduler.add_job(send_attendance_data_for_classroom, trigger, args=[classroom_name])
        api_logger.info(f"Scheduled attendance data job for classroom: {classroom_name} between 9 AM and 5 PM.")
    scheduler.start()
    return scheduler

if __name__ == "__main__":
    import uvicorn
    # Start background scheduler.
    scheduler = start_scheduler()

    # Run FastAPI application.
    uvicorn.run(app, host="0.0.0.0", port=8000)
