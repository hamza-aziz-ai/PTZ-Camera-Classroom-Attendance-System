import argparse
import os
import sys
import re
import cv2
import numpy
from generic_utilities import check_for_directory

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from insightface_face_detection import IFRClient
from milvus_server import create_connection, create_collection, search_embedding
from parameters import MILVUS_HOST, \
    MILVUS_PORT, \
    MILVUS_COLLECTION_NAME, \
    FACE_MATCHING_TOLERANCE, \
    INSTITUTE, \
    METRIC_TYPE


def draw_rectangle_and_label(frame, x_min, y_min, x_max, y_max, name, similarity, is_match):
    color = (0, 255, 0) if is_match else (0, 0, 255)
    cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 3)
    cv2.putText(
        frame,
        f"{name} ({round(similarity, 3)})",
        (x_min, y_min - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        color,
        2,
    )
    return frame


def main(date: str, lecture: int, classroom_name: str):
    ifr_client = IFRClient()  # Initialize IFRClient

    faculty_pattern, student_pattern = None, None
    if INSTITUTE == "GLBITM":
        # Define the pattern for faculty employee ID
        faculty_pattern = re.compile(r'^GLBITM\d{4}$')
    elif INSTITUTE == "ABESIT":
        # Define the pattern for student admission numbers
        student_pattern = re.compile(r'^\d{4}[A-Za-z]+?\d{3}$')

    # input_folder = f"/home/hamza/CLASSROOM-TESTING/{date}/GRIL Training/Snapshots/StudentFrames/TOTAL-FRAMES/Inferred_Frames"
    input_folder = f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{date}/Lecture_{lecture}/Classroom_{classroom_name}/RecognitionFrames/Raw_Frames"

    # output_folder = f"/home/hamza/CLASSROOM-TESTING/{date}/GRIL Training/Snapshots/StudentFrames/TOTAL-FRAMES/Inferred_Frames"
    output_folder = f"/workspace/CLASSROOM-ATTENDANCE-TESTING/{date}/Lecture_{lecture}/Classroom_{classroom_name}/RecognitionFrames/Inferred_Frames"
    check_for_directory(output_folder)

    # Process files in the folder_path
    frames = []
    filenames = []
    for subdirectory in os.listdir(input_folder):
        # print(subdirectory)
        for root, _, files in os.walk(os.path.join(input_folder, subdirectory)):
            # print(root, _, files)
            for file in files:
                # Read each file and add to frames
                frame = cv2.imread(os.path.join(root, file))
                # print(frame)
                # frame = cv2.resize(frame, (1920, 1080))
                frames.append(frame)
                filenames.append((subdirectory, file))

    # print(len(filenames))
    # print(filenames)
    # print(len(frames))

    # Connect to Milvus
    create_connection(MILVUS_HOST, MILVUS_PORT)

    # Assuming you already have a Milvus collection
    embeddings_collection = create_collection(MILVUS_COLLECTION_NAME)

    # Track recognized names and count them
    recognized_names = []

    # Define batch size for inference
    batch_size = 16

    for i in range(0, len(frames), batch_size):
        batch_frames = frames[i : (i + batch_size)]
        batch_filenames = filenames[i : (i + batch_size)]

        # Perform face detection on the batch of frames
        faces_data = ifr_client.plot_bbox(batch_frames)

        batch_embedding = []
        batch_bbox = []
        batch_filename = []
        batch_frame = []

        # Search embeddings and put names and bounding boxes on frames
        for faces, filename in zip(faces_data["data"], batch_filenames):
            frame = cv2.imread(os.path.join(input_folder, filename[0], filename[1]))

            for face_data in faces["faces"]:
                embedding = numpy.array(face_data["vec"])
                bbox = face_data["bbox"]

                batch_embedding.append(embedding)
                batch_bbox.append(bbox)
                batch_filename.append(filename)
                batch_frame.append(frame)

        # TODO: Uncomment to Debug
        # print(f"Length of embeddings batch: {len(batch_embedding)}")
        # print(f"Length of bounding box batch: {len(batch_bbox)}")
        # print(f"Length of filenames batch: {len(batch_filename)}")
        # print(f"Length of frames batch: {len(batch_frame)}")

        inference_result = search_embedding(embeddings_collection, batch_embedding)
        for j, hit in enumerate(inference_result):
            name_of_person = hit[0].id

            frame = batch_frame[j]
            filename = batch_filename[j]

            bbox = batch_bbox[j]
            x_min, y_min, x_max, y_max = bbox

            is_match, face_matching_score = None, None

            if METRIC_TYPE == "COSINE":
                face_matching_score = hit[0].distance
                is_match = (face_matching_score >= FACE_MATCHING_TOLERANCE)

            elif METRIC_TYPE == "L2":
                face_matching_score = hit[0].distance
                is_match = (face_matching_score <= FACE_MATCHING_TOLERANCE)

            if is_match:
                recognized_names.append(name_of_person)

            frame = draw_rectangle_and_label(
                frame,
                x_min,
                y_min,
                x_max,
                y_max,
                name_of_person,
                face_matching_score,
                is_match,
            )

            check_for_directory(os.path.join(output_folder, filename[0]))
            cv2.imwrite(os.path.join(output_folder, filename[0], filename[1]), frame)

    # Get list of recognized names and count of recognitions
    unique_names = sorted(list(set(recognized_names)))

    # Initialize lists for students and faculty
    students_list = []
    faculty_list = []

    # Filter the students and faculty
    for name in unique_names:
        if INSTITUTE == "ABESIT":
            if student_pattern.match(name):
                students_list.append(name)
            else:
                faculty_list.append(name)
        elif INSTITUTE == "GLBITM":
            if faculty_pattern.match(name):
                faculty_list.append(name)
            else:
                students_list.append(name)

    total_students_recognition = len(students_list)
    total_faculty_recognition = len(faculty_list)

    print()
    print("List of recognized faculties:\n", faculty_list)
    print()
    print("List of recognized students:\n", students_list)
    print()
    print("Total count of faculty recognitions : ", total_faculty_recognition)
    print("Total count of student recognitions : ", total_students_recognition)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Face Detection")
    parser.add_argument("--date", type=str, help="Date of the lecture")
    parser.add_argument("--lecture", type=int, help="Lecture number")
    parser.add_argument("--classroom", type=str, default="AB-1_319" if INSTITUTE == "GLBITM" else "2F-32", help="Name of the classroom")
    args = parser.parse_args()

    main(args.date, args.lecture, args.classroom)
