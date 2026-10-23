# -*- coding: utf-8 -*-
"""
@Author: Hamza Aziz
"""

# importing the required libraries
import json
import time
import requests

from custom_logging import multicam_server_logger
from face_liveness_detection import face_liveness_detection
from inference_data_cleaner import data_formatter, collect_cropped_face_data
from milvus_server import search_embedding
from parameters import ENABLE_DATABASE_SERVER, \
    DATABASE_HOST, \
    DATABASE_PORT, \
    ENABLE_FACE_LIVENESS_DETECTION


def batched_frame_face_recognition(
        ifr_client,
        thread_name: str,
        batch_of_frames: list,
        batch_of_cam_names: list,
        batch_of_cam_ips: list,
        embeddings_collection
):
    """
    This function is to be used for GPU based face recognition.
    It performs face detection on a batch of frames at a time.

    Arguments:
        ifr_client: InsightFace-REST database_client to establish connection
        thread_name: Thread name of the current thread in process
        batch_of_frames: List of frames
        batch_of_cam_names: List of camera names
        batch_of_cam_ips: List of camera ip addresses
        embeddings_collection: A collection of embeddings of known faces
    """

    # USE EXCEPTION HANDLING TO HANDLE ERRORS THAT MAY OCCUR DURING BATCH PROCESSING
    try:
        # start_time = time.time()
        ################################################################################################################
        # PERFORM FACE RECOGNITION ON THE BATCH OF FRAMES
        ################################################################################################################
        # Get the face encodings, bounding boxes' coordinates, corresponding frames and cameras with their ip addresses
        # current_face_encoding_start_time = time.time()
        batch_information = ifr_client.batch_face_locations(
            batch_of_frames, batch_of_cam_names, batch_of_cam_ips
        )

        face_encodings_list, bounding_boxes_list, frames_list, cameras_list, ip_addresses_list, face_array_list = (None, None, None, None, None, None)
        # Perform face liveness detection on the batch of frames before the recognition
        if ENABLE_FACE_LIVENESS_DETECTION is True:
            face_encodings_list, bounding_boxes_list, frames_list, cameras_list, ip_addresses_list, face_array_list = batch_information
        else:
            face_encodings_list, bounding_boxes_list, frames_list, cameras_list, ip_addresses_list = batch_information

        # current_face_encoding_end_time = time.time()
        # time_taken_to_get_current_face_encoding = current_face_encoding_end_time - current_face_encoding_start_time
        # multicam_server_logger.info(
        #     f"Time taken to get current real face encoding is {time_taken_to_get_current_face_encoding:>20.9f} seconds"
        # )

        # Perform face recognition on the batch of frames by searching the embeddings in Milvus server
        # similarity_search_start_time = time.time()
        result = search_embedding(embeddings_collection, face_encodings_list)
        # similarity_search_end_time = time.time()
        # similarity_search_time = similarity_search_end_time - similarity_search_start_time
        # multicam_server_logger.info(
        #     f"Time taken for similarity search is {similarity_search_time:>20.9f} seconds"
        # )
        ################################################################################################################

        ################################################################################################################
        # AFTER PERFORMING FACE RECOGNITION ON THE BATCH OF FRAMES, SEND THE RESULTS TO THE
        # DATABASE SERVER (REDIS) FOR STORING THE RECOGNITION RESULTS IN THE DATABASE, AND
        # FEEDBACK SERVER (KAFKA) FOR SENDING THE RECOGNITION RESULTS TO THE FEEDBACK SERVER TO BE DISPLAYED TO THE USER
        # Also, save the recognition frames if SAVE_RECOGNITION_FRAMES is True
        ################################################################################################################
        # Format the result of pymilvus search
        # format_result_start_time = time.time()
        formatted_result = data_formatter(result, cameras_list)
        # print(f"Formatted Result: {formatted_result}")
        # print(formatted_result)
        # format_result_end_time = time.time()
        # format_result_total_time = format_result_end_time - format_result_start_time
        # multicam_server_logger.info(
        #     f"Time taken to format the raw inference results is {format_result_total_time:>20.9f} seconds"
        # )

        if ENABLE_FACE_LIVENESS_DETECTION:

            cropped_faces_data = collect_cropped_face_data(result, face_array_list)

            for person_id, cropped_faces_list in cropped_faces_data.items():
                # print(face_liveness_detection(person_id, cropped_faces_list), f"List Size: {len(cropped_faces_list)}")
                # face_liveness_start_time = time.time()
                person_face_liveness = face_liveness_detection(person_id, cropped_faces_list)
                # face_liveness_end_time = time.time()
                # face_liveness_total_time = face_liveness_end_time - face_liveness_start_time
                # multicam_server_logger.info(
                #     f"Time taken to perform face liveness detection via API on the batch of faces of size {len(cropped_faces_list)} is {round((face_liveness_total_time * 1000), 2)} milliseconds"
                # )
                # print(f"\n{person_face_liveness}, List Size: {len(cropped_faces_list)}\n")
                if "error" in person_face_liveness:
                    multicam_server_logger.error(
                        f"Error while detecting face liveness for {person_id}: {person_face_liveness['error']}"
                    )
                else:
                    liveness_counter = person_face_liveness[person_id]
                    real_count = liveness_counter.get("Real Face", 0)
                    fake_count = liveness_counter.get("Spoof Face", 0)
                    # print(real_count < fake_count)
                    if real_count < fake_count:
                        formatted_result.pop(person_id)
                        # corresponding_value = formatted_result.pop(person_id)
                        # database_server_logger.warn(f"Person {person_id} with details {corresponding_value} is a spoofing attempt.")

        # Get the current date and time; at which, the person id recognized
        # current time in HH:MM:SS format
        current_time = time.strftime("%H:%M:%S")
        # current date in DD_MM_YYYY format
        current_date = time.strftime("%Y-%m-%d")

        # data_encoding_start_time = time.time()
        # Create a dictionary of the data to be sent to the database server and feedback server
        data_to_send = {
            'current_date': current_date,
            'current_time': current_time,
            'results': formatted_result
        }
        # print()
        # print(data_to_send['results'])
        # print()

        # Encode the data to be sent
        data_to_send_encoded = json.dumps(data_to_send).encode('utf-8')

        # Check if the database server is enabled
        if ENABLE_DATABASE_SERVER and formatted_result:
            # Build the URL for the FastAPI ingestion endpoint.
            url = f"http://{DATABASE_HOST}:{DATABASE_PORT}/recognition_entry"
            try:
                # Use the "json" parameter to let requests handle encoding and proper content-type.
                response = requests.post(url, json=data_to_send, timeout=5)

                if response.status_code == 200:
                    pass
                    # multicam_server_logger.info("Data sent successfully:", response.json())
                else:
                    multicam_server_logger.error(f"Failed to send data. Status code: {response.status_code}. Response: {response.text}")
            except Exception as e:
                multicam_server_logger.debug("Exception sending data to database server:", e)
        ################################################################################################################

        # end_time = time.time()
        # time_taken = end_time - start_time
        # # print(f"Time taken to perform face recognition on the batch of frames is {time_taken:>20.9f} seconds")
        # multicam_server_logger.info(
        #     f"Time taken to perform face recognition on the batch of frames is {time_taken:>20.9f} seconds"
        # )

    except Exception as e:
        multicam_server_logger.error(
            f'Thread: {thread_name} - Error in batched_face_locations: {e}'
        )
