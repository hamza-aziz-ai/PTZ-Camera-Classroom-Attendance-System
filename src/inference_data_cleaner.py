"""
This module is created to clean and format the inference data of insightface_face_recognition
"""

from parameters import FACE_MATCHING_TOLERANCE, METRIC_TYPE


def collect_cropped_face_data(inference_result, face_array_list: list) -> dict:
    """
    This function formats the raw inference data of a single batch and cleans it for further use.

    Arguments:
        face_array_list: A List of cropped faces who were detected in a single batch
        inference_result: Raw inference result of single batch

    Returns:
        single_batch_result: A list of cropped faces corresponding to the person recognized in a single batch in dictionary format
    """

    single_batch_result = {}

    for i, hit in enumerate(inference_result):
        name_of_person = hit[0].id
        cropped_face = face_array_list[i]

        # If using L2 (Euclidean Distance) for face recognition
        if METRIC_TYPE == "L2":
            face_distance = hit[0].distance
            if face_distance <= FACE_MATCHING_TOLERANCE:
                if name_of_person not in single_batch_result.keys():
                    single_batch_result[name_of_person] = [cropped_face]
                else:
                    single_batch_result[name_of_person].append(cropped_face)

        # If using COSINE metric type for face recognition
        elif METRIC_TYPE == "COSINE":
            cosine_similarity = hit[0].distance
            if cosine_similarity >= FACE_MATCHING_TOLERANCE:
                if name_of_person not in single_batch_result.keys():
                    single_batch_result[name_of_person] = [cropped_face]
                else:
                    single_batch_result[name_of_person].append(cropped_face)

    # print(single_batch_result)
    return single_batch_result


def data_formatter(inference_result, camera_list: list) -> dict:
    """
    This function formats the raw inference data of a single batch and cleans it for further use.

    Arguments:
        inference_result: Raw inference result of single batch
        camera_list: List of cameras corresponding to the inference results

    Returns:
        single_batch_result: Processed inference result of single batch in a dictionary format
    """

    single_batch_result = {}
    for i, hit in enumerate(inference_result):
        name_of_person = hit[0].id
        cam_name = camera_list[i]

        if METRIC_TYPE == "L2":
            euclidean_distance = hit[0].distance
            if euclidean_distance <= FACE_MATCHING_TOLERANCE:
                if cam_name not in single_batch_result.keys():
                    single_batch_result[cam_name] = [(name_of_person, euclidean_distance)]
                else:
                    single_batch_result[cam_name].append((name_of_person, euclidean_distance))

        elif METRIC_TYPE == "COSINE":
            cosine_similarity = hit[0].distance
            if cosine_similarity >= FACE_MATCHING_TOLERANCE:
                if cam_name not in single_batch_result.keys():
                    single_batch_result[cam_name] = [(name_of_person, cosine_similarity)]
                else:
                    single_batch_result[cam_name].append((name_of_person, cosine_similarity))

    return single_batch_result


def feedback_data_formatter(inference_result, camera_list: list, ip_list: list, frame_list: list, bbox_list: list) -> dict:
    """
    This function formats the raw inference data of a single batch and cleans it for further use.

    Arguments:
        inference_result: Raw inference result of single batch
        camera_list: List of cameras corresponding to the inference results
        ip_list: List of ip addresses corresponding to the inference results
        frame_list: List of frames corresponding to the inference results
        bbox_list: List of bounding boxes' coordinates corresponding to the inference results

    Returns:
        single_batch_result: Processed inference result of single batch in a dictionary format
    """

    single_batch_result = dict()

    for i, hit in enumerate(inference_result):
        name_of_person = hit[0].id
        cam_name = camera_list[i]
        cam_ip = ip_list[i]
        frame = frame_list[i]
        bbox = bbox_list[i]

        # If using L2 (Euclidean Distance) for face recognition
        if METRIC_TYPE == "L2":
            euclidean_distance = hit[0].distance
            percentage_similarity = round((1 - (euclidean_distance / 2)) * 100, 2)
            if euclidean_distance <= FACE_MATCHING_TOLERANCE:
                if cam_name not in single_batch_result.keys():
                    single_batch_result[cam_name] = [(name_of_person, cam_ip, percentage_similarity, frame, bbox)]
                else:
                    single_batch_result[cam_name].append((name_of_person, cam_ip, percentage_similarity, frame, bbox))
        # If using COSINE metric type for face recognition
        elif METRIC_TYPE == "COSINE":
            cosine_similarity = hit[0].distance
            percentage_similarity = round(((cosine_similarity + 1) / 2) * 100, 2)
            if cosine_similarity >= FACE_MATCHING_TOLERANCE:
                if cam_name not in single_batch_result.keys():
                    single_batch_result[cam_name] = [(name_of_person, cam_ip, percentage_similarity, frame, bbox)]
                else:
                    single_batch_result[cam_name].append((name_of_person, cam_ip, percentage_similarity, frame, bbox))

    # print(single_batch_result.keys())
    return single_batch_result
