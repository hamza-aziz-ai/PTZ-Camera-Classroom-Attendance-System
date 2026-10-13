"""
This module is created to make an API for the Student Detection Model.

Date: 12 December 2023
Author: Hamza Aziz
"""
from typing import List

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from yolov9_person_detection import student_counting
import numpy as np
import base64
import cv2

app = FastAPI()


class PayLoad(BaseModel):
    batch_frames: List[List[str]]
    camera_names: List[str]


@app.post("/student_count/")
async def person_detection(payload: PayLoad):
    try:
        batch_of_frames = []
        for masked_frames in payload.batch_frames:
            batch = []
            for masked_frame in masked_frames:
                frame_data = base64.b64decode(masked_frame)
                np_array = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
                batch.append(frame)
            batch_of_frames.append(batch)
        # print(batch_of_frames)
        batch_of_cams = payload.camera_names

        batch_result = student_counting(batch_of_frames, batch_of_cams)
        
        if batch_result is None:
            batch_result = {}
        
        # print()
        # print(f"BATCH RESULT: {batch_result}")
        # print()

        return JSONResponse(content=batch_result, status_code=200)

    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return JSONResponse(content={"error": error_message}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5011)
