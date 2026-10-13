"""
This module is created to make an API call to the Student Counting module.

Date: 12 December 2023
Author: Hamza Aziz
"""

import cv2
import requests
import numpy as np
import base64
from typing import List
from parameters import YOLOv9_PERSON_DETECTION_HOST, YOLOv9_PERSON_DETECTION_PORT

# URL of the FastAPI endpoint
api_url = f"{YOLOv9_PERSON_DETECTION_HOST}:{YOLOv9_PERSON_DETECTION_PORT}/student_count/"


def person_detection(batch_of_masked_frames: List[List[np.ndarray]], batch_of_cameras: List[str]):
    try:
        # Encode NumPy array to base64 string
        batch_of_frames = []
        for masked_frames in batch_of_masked_frames:
            batch = []
            for masked_frame in masked_frames:
                # encode each frame in JPEG format
                _, buffer = cv2.imencode(".jpg", masked_frame)
                # get base64 formatted data
                data = base64.b64encode(buffer.tobytes()).decode("ascii")
                batch.append(data)
            batch_of_frames.append(batch)

        # Make a POST request to the FastAPI endpoint
        response = requests.post(
            url=api_url,
            json={
                "batch_frames": batch_of_frames,
                "camera_names": batch_of_cameras
            }
        )

        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx and 5xx)
        batch_result = response.json()

        return batch_result

    except requests.exceptions.RequestException as e:
        return {"error": f"Request error: {str(e)}"}
