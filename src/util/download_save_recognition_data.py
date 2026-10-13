import json
import os
import argparse
import redis
import sys
from datetime import datetime

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from parameters import REDIS_HOST, REDIS_PORT, FILE_PATHS, LECTURE_TIMES, SAVE_FRAMES_DIRECTORY

REDIS_CLIENT = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

def filter_data_by_time_range(data, start_time, end_time) -> dict:
    filtered_student_count = [
        entry for entry in data["student_count"]
        if start_time <= datetime.strptime(entry["time"], "%H:%M:%S").time() <= end_time
    ]
    filtered_recognition = [
        entry for entry in data["recognition"]
        if start_time <= datetime.strptime(entry["time"], "%H:%M:%S").time() <= end_time
    ]
    
    return {
        "student_count": filtered_student_count,
        "recognition": filtered_recognition
    }


def download_and_save_data(date: str):
    try:
        formatted_date = datetime.strptime(date, "%d-%B-%Y").strftime("%d_%m_%Y")
        data = REDIS_CLIENT.json().get(f"{formatted_date}", f"$")[0]
        
        # Download recognition data lecture wise
        for lecture_number, (start_time_str, end_time_str) in LECTURE_TIMES.items():
            try:
                start_time = datetime.strptime(start_time_str, "%H:%M").time()
                end_time = datetime.strptime(end_time_str, "%H:%M").time()
                
                filtered_data = filter_data_by_time_range(data, start_time, end_time)
                
                file_path = f"/workspace/{FILE_PATHS[lecture_number - 1].format(date=date)}"
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w') as f:
                    json.dump(filtered_data, f, indent=4)
                
                print(f"Data for Lecture {lecture_number} saved successfully. You can find the data at '{file_path}'")
            except Exception as error:
                print(f"Error in saving data for Lecture {lecture_number} due to error: {error}")
        
        # Download data for whole day
        file_path = f"/workspace/{SAVE_FRAMES_DIRECTORY}/{date}/attendance.json"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

        print(f"Whole day data saved successfully. You can find the data at '{file_path}'")
    except Exception as error:
        print(f"Error in saving data due to error: {error}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Lecture Attendance")
    parser.add_argument("--date", type=str, help="Date of the lecture")
    args = parser.parse_args()
    
    download_and_save_data(args.date)
