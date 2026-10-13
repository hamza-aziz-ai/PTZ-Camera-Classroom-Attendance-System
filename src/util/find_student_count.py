import argparse
import json
from collections import Counter


def get_most_frequent_count(json_file_path):
    # Read the JSON data from the file
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        lecture_number = json_file_path.split('/')[-2].split('_')[-1]
        print(f"No attendance data available for LECTURE {lecture_number}.")
        return

    # Group counts by classroom name
    classroom_counts = {}
    for entry in data['student_count']:
        classroom = entry['classroom_name']
        count = entry['count']
        if classroom not in classroom_counts:
            classroom_counts[classroom] = []
        classroom_counts[classroom].append(count)

    # Find the most frequent count for each classroom
    for classroom, counts in classroom_counts.items():
        count_freq = Counter(counts)
        max_freq = max(count_freq.values())
        most_frequent_counts = [
            count for count, freq in count_freq.items() if freq == max_freq
        ]
        print(f"The most frequent count for classroom {classroom} is: {max(most_frequent_counts)}")
        return max(most_frequent_counts)



# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Student Count")
    parser.add_argument("--date", type=str, help="Date of the lecture")
    parser.add_argument("--lecture", type=int, help="Lecture number")
    args = parser.parse_args()

    # Replace with the path to your JSON file
    json_file = f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{args.date}/Lecture_{args.lecture}/attendance.json"
    get_most_frequent_count(json_file)
