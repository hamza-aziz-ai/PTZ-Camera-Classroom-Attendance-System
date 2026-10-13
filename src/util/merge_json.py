import json
import argparse


def merge_json_files(input_files, output_file):
    """
    Merges data from multiple JSON files into a single file.

    Args:
        input_files (list): List of paths to the JSON files to be merged.
        output_file (str): Path to the output file where merged data will be saved.
    """
    merged_data = {"student_count": [], "recognition": []}

    for file in input_files:
        with open(file, "r") as f:
            data = json.load(f)
            merged_data["student_count"].extend(data["student_count"])
            merged_data["recognition"].extend(data["recognition"])

    with open(output_file, "w") as f:
        json.dump(merged_data, f, indent=4)  # Add indent for readability (optional)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Student Count")
    parser.add_argument("--date", type=str, help="Date of the lecture")
    args = parser.parse_args()

    file_paths = [
        f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/Lecture_1/attendance.json",
        f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/Lecture_2/attendance.json",
        f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/Lecture_3/attendance.json",
        f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/Lecture_4/attendance.json",
        f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/Lecture_5/attendance.json",
        f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/Lecture_6/attendance.json",
        f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/Lecture_7/attendance.json",
        f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/Lecture_8/attendance.json"
    ]

    output_file_path = f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/attendance.json"
    merge_json_files(file_paths, output_file_path)

    print(f"Merged data written to: {output_file_path}")
