"""
This module is created to fetch frames from a shared buffer and collect them in batches for face recognition.

Author: Hamza Aziz
"""

from custom_logging import multicam_server_logger
from student_count_with_yolov9_person_detection import student_count_with_yolov9_person_detection
from locks import lock
from parameters import BATCH_SIZE, \
    LIVE_STREAM_BUFFER_SIZE, \
    LIVE_STREAM_BUFFER_PURGE_SIZE


def person_detection(count_buffer):
    while True:

        with lock:
            if count_buffer.qsize() < BATCH_SIZE:
                continue

            count_frame_batch = []
            while len(count_frame_batch) != BATCH_SIZE:
                buffer_elements = count_buffer.get()
                count_frame_batch.append(buffer_elements)

            batch_of_masked_frames = []
            batch_of_cam_names = []
            batch_of_cam_ips = []

        for masked_frames, camera_name, camera_ip in count_frame_batch:
            batch_of_masked_frames.append(masked_frames)
            batch_of_cam_names.append(camera_name)
            batch_of_cam_ips.append(camera_ip)

        student_count_with_yolov9_person_detection(
            batch_of_masked_frames=batch_of_masked_frames,
            batch_of_cam_names=batch_of_cam_names,
        )

        # Delete batch_of_frames
        del batch_of_masked_frames

        frames_buffer_size = count_buffer.qsize()
        # print(f"THREAD: {thread_id} CURRENT BUFFER SIZE: {frames_buffer_size}")
        if frames_buffer_size > LIVE_STREAM_BUFFER_SIZE:
            multicam_server_logger.warning(f"Frames buffer size {frames_buffer_size}. Purging frames_buffer...")
            for _ in range(LIVE_STREAM_BUFFER_PURGE_SIZE):
                count_buffer.get()


def consumer_main(count_buffer):
    """
    This function starts the face recognition process.

    Parameters:
        count_buffer
    """
    try:
        person_detection(count_buffer)

    except KeyboardInterrupt:
        multicam_server_logger.warning("EXITING THE PROGRAM...")
