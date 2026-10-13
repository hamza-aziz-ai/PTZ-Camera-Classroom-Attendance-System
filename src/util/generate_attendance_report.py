import argparse
import csv
import json
import re
import os
import sys
from generic_utilities import check_for_directory

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from parameters import MAPPING_FILE, SAVE_FRAMES_DIRECTORY, INSTITUTE

# # Read data from CSV File
# admission_to_roll_mapping = {}
# with open(MAPPING_FILE, 'r') as csv_file:
#     csv_reader = csv.DictReader(csv_file)
#     for row in csv_reader:
#         admission_to_roll_mapping[row["Admission No"]] = row["University Roll No"]


# Function to process the JSON data
def process_data(json_data):
    classroom_information = {}

    faculty_pattern, student_pattern = None, None
    if INSTITUTE == "GLBITM":
        # Define the pattern for faculty employee ID
        faculty_pattern = re.compile(r'^GLBITM\d{4}$')
    elif INSTITUTE == "ABESIT":
        # Define the pattern for student admission numbers
        student_pattern = re.compile(r'^\d{4}[A-Za-z]+?\d{3}$')

    for entry in json_data["recognition"]:
        classroom_name = entry["classroom_name"]
        entity = entry["entity"]

        if classroom_name not in classroom_information:
            classroom_information[classroom_name] = {"students": set(), "faculty": set()}

        if INSTITUTE == "GLBITM":
            if faculty_pattern.match(entity):  # Check if the entity matches the faculty pattern
                classroom_information[classroom_name]["faculty"].add(entity)
            else:
                classroom_information[classroom_name]["students"].add(entity)
        elif INSTITUTE == "ABESIT":
            if student_pattern.match(entity):  # Check if the entity matches the student pattern
                # university_roll = admission_to_roll_mapping.get(entity, "Unknown")
                # classroom_information[classroom_name]["students"].add(university_roll)
                classroom_information[classroom_name]["students"].add(entity)
            else:
                classroom_information[classroom_name]["faculty"].add(entity)

    return classroom_information


# Function to write data to text files
def write_to_files(classroom_information, date, lecture):
    for classroom_name, entities in classroom_information.items():
        directory_path = f"/workspace/{SAVE_FRAMES_DIRECTORY}/{date}/Lecture_{lecture}/Classroom_{classroom_name}"
        check_for_directory(directory_path)
        filename = f"{directory_path}/attendance.txt"
        # print(filename)
        with open(filename, "w") as file:
            file.write("FACULTY\n")
            file.write("-------------------------------\n")
            for faculty in sorted(entities["faculty"]):
                file.write(faculty + "\n")
            file.write("\n\nSTUDENTS\n")
            file.write("-------------------------------\n")
            for student in sorted(entities["students"]):
                file.write(student + "\n")
            file.write(f"\nTotal number of students recognized: {len(entities['students'])}")
            # file.write(f"\nTotal number of students present: {student_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Student Count")
    parser.add_argument("--date", type=str, help="Date of the lecture")
    parser.add_argument("--lecture", type=int, help="Lecture number")
    args = parser.parse_args()

    try:
        # Read data from JSON File
        with open(f"/workspace/{SAVE_FRAMES_DIRECTORY}/{args.date}/Lecture_{args.lecture}/attendance.json", 'r') as json_file:
            data = json.load(json_file)
    except FileNotFoundError:
        # lecture = f"LECTURE {args.lecture}"
        print(f"No attendance data available for Lecture {args.lecture} on date {args.date}")
        exit(0)

    # Process and write data
    classroom_data = process_data(data)
    # total_students_present = get_most_frequent_count(f"{SAVE_FRAMES_DIRECTORY}/{args.date}/Lecture_{args.lecture}/attendance.json")
    write_to_files(classroom_data, args.date, args.lecture)
