import os
import sys
from yolov9.detect_custom import person_detection

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
from custom_logging import multicam_server_logger

def student_counting(batch_of_frames: list, batch_of_cameras):
    student_count_dictionary = dict()
    for i, masked_frames in enumerate(batch_of_frames):
        cam_name = batch_of_cameras[i]
        try:
            student_count = person_detection(weights="yolov9-e-converted.pt", frames=masked_frames)
    
            student_count_dictionary[cam_name] = student_count
        except Exception as e:
            multicam_server_logger.error(f"Error in counting students for Classroom {cam_name} due to error: {e}")
    
    # print(student_count_dictionary)
    return student_count_dictionary
