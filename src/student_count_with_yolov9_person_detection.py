# -*- coding: utf-8 -*-
"""
@Author: Anubhav Patrick, Hamza Aziz
"""

# importing the required libraries
import json
import time
import requests
from yolov9_person_detection import person_detection
from custom_logging import multicam_server_logger
from parameters import ENABLE_DATABASE_SERVER, \
    DATABASE_HOST, \
    DATABASE_PORT


def student_count_with_yolov9_person_detection(
        batch_of_masked_frames: list,
        batch_of_cam_names: list,
):
    """
    This function is to be used for GPU based face recognition.
    It performs face detection on a batch of frames at a time.

    Arguments:
        batch_of_masked_frames: List of frames
        batch_of_cam_names: List of camera names
    """

    # USE EXCEPTION HANDLING TO HANDLE ERRORS THAT MAY OCCUR DURING BATCH PROCESSING
    try:
        ################################################################################################################
        # PERFORM FACE RECOGNITION ON THE BATCH OF FRAMES
        ################################################################################################################
        # Get the face encodings, bounding boxes' coordinates, corresponding frames and cameras with their ip addresses
        student_count = person_detection(batch_of_masked_frames, batch_of_cam_names)
        # print(f"Student Count is {student_count}")

        data_to_send = {
            "current_date": time.strftime("%Y-%m-%d"),
            "current_time": time.strftime("%H:%M:%S"),
            "results": student_count
        }

        # Check if the database server is enabled
        if ENABLE_DATABASE_SERVER and student_count:
            # Build the URL for the FastAPI ingestion endpoint.
            url = f"http://{DATABASE_HOST}:{DATABASE_PORT}/count_entry"
            try:
                # Use the "json" parameter to let requests handle encoding and proper content-type.
                response = requests.post(url, json=data_to_send, timeout=5)

                if response.status_code == 200:
                    multicam_server_logger.info("Data sent successfully:", response.json())
                else:
                    multicam_server_logger.error(f"Failed to send data. Status code: {response.status_code}. Response: {response.text}")
            except Exception as e:
                multicam_server_logger.debug("Exception sending data to database server:", e)

    except Exception as e:
        multicam_server_logger.error(
            f'Error in batched_face_locations: {e}'
        )
