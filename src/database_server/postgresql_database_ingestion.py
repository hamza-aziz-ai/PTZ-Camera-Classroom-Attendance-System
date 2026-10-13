#!/usr/bin/env python3
"""
Module for Database and Image Processing operations with an MVC-like structure.
"""

import os
import sys
import re
import base64
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict

import psycopg2
from psycopg2 import sql
import numpy as np
import cv2

# Ensure the parent directory is on the path for module imports.
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from parameters import (
    POSTGRESQL_HOST,
    POSTGRESQL_PORT,
    POSTGRESQL_DATABASE,
    SAME_CAM_TIME_ENTRY_THRESHOLD,
    INSTITUTE,
    PTZ_CAMS,
    LECTURE_TIMES  # Expected to be a dict, e.g., {1: ("09:00:00", "09:50:00"), ...}
)
from custom_logging import database_server_logger

# Read database credentials from the environment.
POSTGRESQL_USERNAME = os.environ.get("POSTGRES_USER")
POSTGRESQL_PASSWORD = os.environ.get("POSTGRES_PASSWORD")

# Main database configuration.
DB_CONFIG = {
    'dbname': POSTGRESQL_DATABASE,
    'user': POSTGRESQL_USERNAME,
    'password': POSTGRESQL_PASSWORD,
    'host': POSTGRESQL_HOST,
    'port': POSTGRESQL_PORT
}


#############################
# Model: Database Operations
#############################

class DatabaseModel:
    """
    Handles database operations including initialization, table creation,
    partition management, and data insertion.
    """
    def __init__(self, config: dict) -> None:
        """
        Initialize the DatabaseModel with the given configuration.

        Args:
            config (dict): Database configuration parameters.
        """
        self.config = config

    def get_connection(self) -> psycopg2.extensions.connection:
        """
        Establish and return a new database connection.

        Returns:
            psycopg2.extensions.connection: A new database connection.
        """
        return psycopg2.connect(**self.config)

    def ensure_database_exists(self) -> None:
        """
        Ensure that the target database exists. If not, create it.

        Raises:
            Exception: If there is an error during the operation.
        """
        try:
            # Connect to the default 'postgres' database.
            default_config = self.config.copy()
            default_config['dbname'] = 'postgres'
            conn = psycopg2.connect(**default_config)
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;",
                    (self.config['dbname'],)
                )
                if not cursor.fetchone():
                    database_server_logger.info(
                        f"Database '{self.config['dbname']}' does not exist. Creating it..."
                    )
                    cursor.execute(
                        sql.SQL("CREATE DATABASE {}").format(
                            sql.Identifier(self.config['dbname'])
                        )
                    )
            conn.close()
            database_server_logger.info(f"Database '{self.config['dbname']}' is ready.")
        except Exception as error:
            database_server_logger.error(f"Error ensuring database exists: {error}")
            raise

    @staticmethod
    def ensure_unified_tables_exist(cursor: psycopg2.extensions.cursor) -> None:
        """
        Create the base tables if they do not exist.

        Args:
            cursor (psycopg2.extensions.cursor): Database cursor.

        Raises:
            Exception: If table creation fails.
        """
        try:
            # Create lecture_summary table partitioned by lecture_date.
            create_lecture_summary_table_query = sql.SQL("""
                CREATE TABLE IF NOT EXISTS lecture_summary (
                    lecture_id INTEGER,
                    classroom_name TEXT,
                    lecture_date DATE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata')::date,
                    lecture_start_time TIME,
                    lecture_end_time TIME,
                    detected_student_count INTEGER DEFAULT 0,
                    recognized_student_count INTEGER DEFAULT 0,
                    recognized_faculty_count INTEGER DEFAULT 0,
                    attendance_valid BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (lecture_id, classroom_name, lecture_date)
                ) PARTITION BY RANGE (lecture_date);
            """)
            # Create student_detection_count table partitioned by detection_date.
            create_student_detection_count_table_query = sql.SQL("""
                CREATE TABLE IF NOT EXISTS student_detection_count (
                    lecture_id INTEGER,
                    classroom_name TEXT,
                    detection_date DATE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata')::date,
                    detection_time TIME DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata')::time,
                    detection_count INTEGER DEFAULT 0,
                    UNIQUE (lecture_id, classroom_name, detection_date, detection_time),
                    FOREIGN KEY (lecture_id, classroom_name, detection_date)
                        REFERENCES lecture_summary(lecture_id, classroom_name, lecture_date)
                ) PARTITION BY RANGE (detection_date);
            """)
            # Create attendance_log table partitioned by recognition_date.
            create_attendance_log_table_query = sql.SQL("""
                CREATE TABLE IF NOT EXISTS attendance_log (
                    id SERIAL,
                    person_id TEXT,
                    classroom_name TEXT,
                    camera_ip INET,
                    recognition_date DATE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata')::date,
                    recognition_time TIME DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata')::time,
                    face_matching_distance NUMERIC,
                    role TEXT,
                    lecture_id INTEGER,
                    PRIMARY KEY (id, classroom_name, recognition_date),
                    FOREIGN KEY (lecture_id, classroom_name, recognition_date) 
                        REFERENCES lecture_summary(lecture_id, classroom_name, lecture_date)
                ) PARTITION BY RANGE (recognition_date);
            """)
            # Execute table creation queries.
            cursor.execute(create_lecture_summary_table_query)
            cursor.execute(create_student_detection_count_table_query)
            cursor.execute(create_attendance_log_table_query)

            database_server_logger.info("Base tables are ensured.")
        except psycopg2.errors.DuplicateTable:
            database_server_logger.info("Base tables already exist. Skipping creation.")
        except Exception as error:
            database_server_logger.error(f"Error ensuring base tables existence: {error}")
            raise

    def execute_partition_query(self, query, params: tuple) -> None:
        """
        Execute a partition query using a separate autocommit connection.

        Args:
            query: SQL query to execute.
            params (tuple): Parameters for the SQL query.

        Raises:
            Exception: If query execution fails.
        """
        try:
            with psycopg2.connect(**self.config) as conn:
                conn.autocommit = True
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
        except Exception as e:
            raise Exception(f"Failed executing partition query: {query.as_string(conn)} with params {params}: {e}")

    def create_year_partition(self, base_table: str, current_year: int) -> None:
        """
        Create a partition for a base table for the specified year.

        Args:
            base_table (str): Name of the base table.
            current_year (int): Year for the partition.
        """
        partition_name = f"{base_table}_{current_year}"
        start_date = f"{current_year}-01-01"
        end_date = f"{current_year + 1}-01-01"
        query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} 
            PARTITION OF {} 
            FOR VALUES FROM (%s) TO (%s);
        """).format(sql.Identifier(partition_name), sql.Identifier(base_table))
        self.execute_partition_query(query, (start_date, end_date))

    def ensure_year_partitions_exist(self, current_year: int) -> None:
        """
        Ensure partitions exist for all relevant tables for a given year.

        Args:
            current_year (int): The year for which partitions are ensured.
        """
        try:
            for base_table in ['attendance_log', 'lecture_summary', 'student_detection_count']:
                self.create_year_partition(base_table, current_year)
            database_server_logger.info(f"Year partitions for {current_year} are ensured.")
        except Exception as error:
            database_server_logger.error(f"Error ensuring partitions for {current_year}: {error}")
            raise

    def initialize_database_and_partitions(self) -> None:
        """
        Initialize the database, create base tables, and ensure partitions exist.

        Raises:
            Exception: If initialization fails.
        """
        try:
            self.ensure_database_exists()
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    self.ensure_unified_tables_exist(cursor)
                conn.commit()
                current_year = datetime.now().year
                self.ensure_year_partitions_exist(current_year)
            database_server_logger.info("Database, unified tables, and partitions initialized successfully.")
        except Exception as error:
            database_server_logger.error(f"Error during database initialization: {error}")
            raise

    def get_lecture_time(self, lecture_id: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieve the lecture start and end times from the global LECTURE_TIMES.

        Args:
            lecture_id (int): Lecture identifier.

        Returns:
            Tuple[Optional[str], Optional[str]]: (lecture_start_time, lecture_end_time)
        """
        return LECTURE_TIMES.get(lecture_id, (None, None))

    def update_detection_count_atomic(
            self,
            cursor: psycopg2.extensions.cursor,
            lecture_id: int,
            classroom_name: str,
            lecture_date: str,
            detected_student_count: int
    ) -> None:
        """
        Atomically update the detected_student_count and lecture timing in lecture_summary.

        Args:
            cursor (psycopg2.extensions.cursor): Database cursor.
            lecture_id (int): Lecture identifier.
            classroom_name (str): Classroom name.
            lecture_date (str): Date in 'YYYY-MM-DD' format.
            detected_student_count (int): Aggregated detected student count.
        """
        lecture_start_time, lecture_end_time = self.get_lecture_time(lecture_id)
        update_query = sql.SQL("""
            UPDATE lecture_summary
            SET detected_student_count = %s,
                lecture_start_time = %s,
                lecture_end_time = %s
            WHERE lecture_id = %s AND classroom_name = %s AND lecture_date = %s;
        """)
        params = (detected_student_count, lecture_start_time, lecture_end_time,
                  lecture_id, classroom_name, lecture_date)
        cursor.execute(update_query, params)
        database_server_logger.info(
            f"Atomically updated detected count for lecture {lecture_id}, classroom {classroom_name} on {lecture_date} to {detected_student_count}."
        )

    def update_recognized_counts_atomic(
            self,
            cursor: psycopg2.extensions.cursor,
            lecture_id: int,
            classroom_name: str,
            lecture_date: str
    ) -> None:
        """
        Atomically update recognized counts and lecture timing in lecture_summary using subqueries on attendance_log.

        Args:
            cursor (psycopg2.extensions.cursor): Database cursor.
            lecture_id (int): Lecture identifier.
            classroom_name (str): Classroom name.
            lecture_date (str): Date in 'YYYY-MM-DD' format.
        """
        lecture_start_time, lecture_end_time = self.get_lecture_time(lecture_id)
        update_query = sql.SQL("""
            UPDATE lecture_summary
            SET recognized_student_count = (
                SELECT DISTINCT COUNT(DISTINCT person_id) FROM attendance_log
                WHERE lecture_id = %s AND classroom_name = %s AND recognition_date = %s AND role = 'student'
            ),
            recognized_faculty_count = (
                SELECT DISTINCT COUNT( DISTINCT person_id) FROM attendance_log
                WHERE lecture_id = %s AND classroom_name = %s AND recognition_date = %s AND role = 'faculty'
            ),
            lecture_start_time = %s,
            lecture_end_time = %s
            WHERE lecture_id = %s AND classroom_name = %s AND lecture_date = %s;
        """)
        params = (
            lecture_id, classroom_name, lecture_date,
            lecture_id, classroom_name, lecture_date,
            lecture_start_time, lecture_end_time,
            lecture_id, classroom_name, lecture_date
        )
        cursor.execute(update_query, params)
        database_server_logger.info(
            f"Atomically updated recognized counts for lecture {lecture_id}, classroom {classroom_name} on {lecture_date}."
        )

    def ensure_lecture_summary_exists(
            self,
            cursor: psycopg2.extensions.cursor,
            lecture_id: int,
            classroom_name: str,
            lecture_date: str
    ) -> None:
        """
        Ensure that a lecture_summary record exists; if not, insert a placeholder.

        Args:
            cursor (psycopg2.extensions.cursor): Database cursor.
            lecture_id (int): Lecture identifier.
            classroom_name (str): Classroom name.
            lecture_date (str): Date in 'YYYY-MM-DD' format.
        """
        select_query = sql.SQL("""
            SELECT 1 FROM lecture_summary
            WHERE lecture_id = %s
              AND classroom_name = %s
              AND lecture_date = %s;
        """)
        cursor.execute(select_query, (lecture_id, classroom_name, lecture_date))
        if not cursor.fetchone():
            insert_placeholder = sql.SQL("""
                INSERT INTO lecture_summary
                (lecture_id, classroom_name, lecture_date)
                VALUES (%s, %s, %s);
            """)
            try:
                cursor.execute(insert_placeholder, (lecture_id, classroom_name, lecture_date))
                database_server_logger.info(
                    f"Inserted placeholder lecture summary for lecture {lecture_id}, classroom {classroom_name} on {lecture_date}."
                )
            except Exception as error:
                database_server_logger.error(
                    f"Error inserting placeholder lecture summary for lecture {lecture_id}, classroom {classroom_name} on {lecture_date}: {error}"
                )

    def insert_student_detection_count(self, current_date: str, current_time: str, student_count_result: Dict[str, int]) -> None:
        """
        Insert detection counts and update lecture_summary.

        Args:
            current_date (str): Date in 'YYYY-MM-DD' format.
            current_time (str): Time in 'HH:MM:SS' format.
            student_count_result (Dict[str, int]): Mapping of classroom names to student counts.
        """
        try:
            lecture_id = RecognitionController.get_current_lecture(current_time)
            if lecture_id is None:
                database_server_logger.error("No valid lecture slot found for the current time.")
                return

            with self.get_connection() as conn:
                conn.autocommit = True
                with conn.cursor() as cursor:
                    current_year = datetime.strptime(current_date, "%Y-%m-%d").year
                    self.ensure_year_partitions_exist(current_year)

                    for classroom_name, student_count in student_count_result.items():
                        if student_count <= 0:
                            continue

                        self.ensure_lecture_summary_exists(cursor, lecture_id, classroom_name, current_date)

                        insert_query = sql.SQL("""
                            INSERT INTO student_detection_count (lecture_id, classroom_name, detection_date, detection_time, detection_count)
                            VALUES (%s, %s, %s, %s, %s);
                        """)
                        cursor.execute(insert_query, (lecture_id, classroom_name, current_date, current_time, student_count))
                        database_server_logger.info(
                            f"Inserted detection count for {classroom_name} on {current_date} at {current_time}."
                        )

                        # Aggregate final detection count using a frequency method.
                        aggregate_query = sql.SQL("""
                            WITH count_frequencies AS (
                                SELECT detection_count, COUNT(*) AS frequency
                                FROM student_detection_count
                                WHERE lecture_id = %s
                                  AND classroom_name = %s
                                  AND detection_date = %s
                                GROUP BY detection_count
                            ),
                            most_frequent AS (
                                SELECT detection_count
                                FROM count_frequencies
                                WHERE frequency = (SELECT MAX(frequency) FROM count_frequencies)
                            )
                            SELECT MAX(detection_count) AS final_detected_count
                            FROM most_frequent;
                        """)
                        cursor.execute(aggregate_query, (lecture_id, classroom_name, current_date))
                        final_detected_count = int(cursor.fetchone()[0])

                        # Update detected count (and lecture time) and recognized counts separately.
                        self.update_detection_count_atomic(cursor, lecture_id, classroom_name, current_date, final_detected_count)
                        self.update_recognized_counts_atomic(cursor, lecture_id, classroom_name, current_date)
                conn.commit()
        except Exception as error:
            database_server_logger.error(f"Error inserting student detection count: {error}")

    def insert_recognition_data(self, current_date: str, current_time: str, results: Dict[str, List[Tuple[str, float]]]) -> None:
        """
        Insert recognition data into attendance_log and update recognized counts.

        Args:
            current_date (str): Date in 'YYYY-MM-DD' format.
            current_time (str): Time in 'HH:MM:SS' format.
            results (Dict[str, List[Tuple[str, float]]]): Mapping of classroom names to recognition records.
        """
        try:
            current_year = datetime.strptime(current_date, "%Y-%m-%d").year
        except Exception as e:
            database_server_logger.error(f"Invalid date format for current_date: {current_date}. Error: {e}")
            return

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    self.ensure_year_partitions_exist(current_year)
                    lecture_id = RecognitionController.get_current_lecture(current_time)
                    if lecture_id is None:
                        database_server_logger.error("No valid lecture slot found for the current time.")
                        return

                    for classroom_name, records in results.items():
                        self.ensure_lecture_summary_exists(cursor, lecture_id, classroom_name, current_date)

                        for record in records:
                            person_id, face_matching_distance = record
                            camera_ip = PTZ_CAMS[classroom_name]["cam-ip"]

                            if INSTITUTE == "GLBITM":
                                faculty_pattern = re.compile(r'^GLBITM\d{4}$')
                                role = "faculty" if faculty_pattern.match(person_id) else "student"
                            elif INSTITUTE == "ABESIT":
                                student_pattern = re.compile(r'^\d{4}[A-Za-z]+?\d{3}$')
                                role = "student" if student_pattern.match(person_id) else "faculty"
                            else:
                                role = "student"

                            current_datetime = datetime.strptime(f"{current_date} {current_time}", "%Y-%m-%d %H:%M:%S")
                            threshold_datetime = current_datetime - timedelta(minutes=SAME_CAM_TIME_ENTRY_THRESHOLD)
                            time_threshold = threshold_datetime.strftime("%H:%M:%S")

                            select_query = sql.SQL("""
                                SELECT 1 FROM attendance_log
                                WHERE person_id = %s
                                  AND classroom_name = %s
                                  AND recognition_date = %s
                                  AND recognition_time >= %s;
                            """)
                            cursor.execute(select_query, (person_id, classroom_name, current_date, time_threshold))
                            if cursor.fetchone():
                                database_server_logger.warning(
                                    f"Skipping entry for {person_id} in classroom {classroom_name} "
                                    f"(entry exists within {SAME_CAM_TIME_ENTRY_THRESHOLD} minutes)."
                                )
                                continue

                            insert_query = sql.SQL("""
                                INSERT INTO attendance_log
                                (person_id, classroom_name, camera_ip, recognition_date, recognition_time, face_matching_distance, role, lecture_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                            """)
                            try:
                                cursor.execute(insert_query, (
                                    person_id, classroom_name, camera_ip, current_date, current_time,
                                    face_matching_distance, role, lecture_id
                                ))
                                database_server_logger.info(
                                    f"Inserted entry for {person_id} for lecture {lecture_id}, classroom {classroom_name}."
                                )
                            except Exception as error:
                                database_server_logger.error(
                                    f"Error inserting entry for {person_id} for lecture {lecture_id}, classroom {classroom_name}: {error}"
                                )
                        # After processing all records for this classroom, update recognized counts (and lecture time).
                        self.update_recognized_counts_atomic(cursor, lecture_id, classroom_name, current_date)
                conn.commit()
        except Exception as error:
            database_server_logger.error(f"Error while inserting recognition data: {error}")


#############################
# View: Image Processing Operations
#############################

class ImageProcessor:
    """
    Provides utilities for image processing tasks.
    """
    @staticmethod
    def plot_bbox(
            frame: np.ndarray,
            bboxes: List[List[int]],
            person_ids: List[str],
            face_matching_distances: List[float]
    ) -> Optional[bytes]:
        """
        Draw bounding boxes and labels on the frame and return the encoded image.

        Args:
            frame (np.ndarray): Input image.
            bboxes (List[List[int]]): Bounding boxes as [x_min, y_min, x_max, y_max].
            person_ids (List[str]): Recognized person IDs.
            face_matching_distances (List[float]): Matching distances.

        Returns:
            Optional[np.ndarray]: Encoded JPEG image bytes if successful, otherwise None.
        """
        try:
            for i, bbox in enumerate(bboxes):
                x_min, y_min, x_max, y_max = bbox
                person_id = person_ids[i]
                distance = face_matching_distances[i]
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"{person_id} ({round(distance, 2)})",
                    (x_min, max(y_min - 10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 0),
                    2,
                )
            success, encoded_frame = cv2.imencode('.jpg', frame)
            if not success:
                raise ValueError("Failed to encode frame")
            return encoded_frame.tobytes()
        except Exception as e:
            database_server_logger.error(f"Exception while plotting bounding boxes: {e}")
            return None

    @staticmethod
    def base64_to_image(base64_frame: str) -> Optional[np.ndarray]:
        """
        Convert a base64 encoded string to an image.

        Args:
            base64_frame (str): Base64 encoded image.

        Returns:
            Optional[np.ndarray]: Decoded image array if successful, otherwise None.
        """
        try:
            frame_bytes = base64.b64decode(base64_frame)
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            image = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            database_server_logger.error(f"Error decoding base64 frame: {e}")
            return None


#############################
# Controller: Recognition Processing
#############################

class RecognitionController:
    """
    Handles recognition data processing and orchestrates operations between
    the model and view.
    """
    def __init__(self, db_model: DatabaseModel) -> None:
        """
        Initialize the RecognitionController with a DatabaseModel instance.

        Args:
            db_model (DatabaseModel): Instance of DatabaseModel.
        """
        self.db_model = db_model

    @staticmethod
    def get_current_lecture(recognition_time_str: str) -> Optional[int]:
        """
        Determine the current lecture based on the recognition time.

        Args:
            recognition_time_str (str): Time in "HH:MM:SS" format.

        Returns:
            Optional[int]: Lecture ID if found, else None.
        """
        try:
            recognition_time = datetime.strptime(recognition_time_str, "%H:%M:%S").time()
        except ValueError as ve:
            database_server_logger.error(
                f"Invalid time format for recognition_time: {recognition_time_str}. Expected HH:MM:SS. {ve}"
            )
            return None

        for lecture_id, (start_str, end_str) in LECTURE_TIMES.items():
            lecture_start = datetime.strptime(start_str, "%H:%M:%S").time()
            lecture_end = datetime.strptime(end_str, "%H:%M:%S").time()
            if lecture_start <= recognition_time <= lecture_end:
                return lecture_id
        return None

    def process_recognition_data(self, current_date: str, current_time: str, results: Dict[str, List[Tuple[str, float]]]) -> None:
        """
        Process and insert recognition data.

        Args:
            current_date (str): Date in 'YYYY-MM-DD' format.
            current_time (str): Time in 'HH:MM:SS' format.
            results (Dict[str, List[Tuple[str, float]]]): Recognition results.
        """
        self.db_model.insert_recognition_data(current_date, current_time, results)

    def process_detection_count(self, current_date: str, current_time: str, student_count_result: Dict[str, int]) -> None:
        """
        Process and insert student detection counts.

        Args:
            current_date (str): Date in 'YYYY-MM-DD' format.
            current_time (str): Time in 'HH:MM:SS' format.
            student_count_result (Dict[str, int]): Mapping of classroom names to student counts.
        """
        self.db_model.insert_student_detection_count(current_date, current_time, student_count_result)
