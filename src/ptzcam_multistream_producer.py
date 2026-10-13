"""
This module was created to control the camera.

Author: [Redacted]
Date: 5 January 2024
"""

import json
import threading
import time
from datetime import datetime, time as dt_time, timedelta
from typing import Optional

import cv2
import numpy as np
from onvif import ONVIFCamera

from custom_logging import multicam_server_logger, feedback_server_logger
from parameters import PTZ_CAMS, \
    PTZ_CAM_REINIT_WAIT_DURATION, \
    SAVE_FRAMES, \
    RECOGNITION_PATH, \
    SAVE_FRAMES_DIRECTORY, \
    RETRY_COUNT, \
    COUNTING_PATH, \
    LECTURE_TIMES
from util.generic_utilities import check_for_directory


class PTZCamera:
    """
    This class is used to control the camera.
    """

    def __init__(self, cam_name, cam_ip, cam_port, cam_username, cam_password, shared_buffer, count_buffer, configuration_file):
        """
        Initializes the camera.

        Parameters:
            cam_name: Name of the camera
            cam_ip: IP address of the camera
            cam_port: Port of the camera
            cam_username: Username of the camera
            cam_password: Password of the camera
            shared_buffer: Shared buffer to store the frames
            configuration_file: Configuration file path

        Returns:
            None
        """
        self.initialized = False
        try:
            # Set the shared buffer
            self.shared_buffer = shared_buffer
            # Set the count buffer
            self.count_buffer = count_buffer
            # Initialize the camera
            self.cam_name = cam_name
            self.cam_ip = cam_ip
            self.cam_port = cam_port
            self.cam_username = cam_username
            self.cam_password = cam_password
            self.camera = ONVIFCamera(self.cam_ip, self.cam_port, self.cam_username, self.cam_password)

            # Create media service object
            self.media = self.camera.create_media_service()
            # Get target profile
            self.media_profile = self.media.GetProfiles()[0]
            # Create PTZ service object
            self.ptz = self.camera.create_ptz_service()
            # Configuration File for the Camera in JSON format
            self.configuration_file = configuration_file
            # Read configuration file as dictionary
            with open(self.configuration_file, "r") as json_file:
                self.data = json.load(json_file)

            self.initialized = True
            multicam_server_logger.info(f"Camera {self.cam_name} initialized")
            # print(f"Camera {self.cam_name} initialized")
        except Exception as e:
            multicam_server_logger.error(f"Camera {self.cam_name} failed to initialize due to {e}")

    def frame_capture_retry_mechanism(self, capture_object: cv2.VideoCapture, return_value: bool = False):
        """
        Retry mechanism to capture frames from a camera if failed to do so.

        Parameters:
            capture_object: The VideoCapture object for the camera
            return_value: Indicator whether the frame has been captured or not

        Returns:
            return_value, frame_data
        """
        retry_count = 0

        while not return_value and retry_count < RETRY_COUNT:
            time.sleep(0.1)
            return_value, frame = capture_object.read()

            if return_value is True:
                return return_value, frame

            retry_count += 1

        multicam_server_logger.error(
            f"Unable to capture frames from the camera {self.cam_name} (URL: {self.cam_ip})"
        )
        return False, None

    def save_frames(self, frame_to_be_saved: np.ndarray, position_of_frame: int, save_counting_frames: bool = False):
        """
        Saves the frames captured from the camera for debugging.

        Parameters:
            frame_to_be_saved: The frame to be saved
            position_of_frame: The position (camera preset) of the frame
            save_counting_frames: Boolean flag to indicate whether to save frames captured for counting. If false, then save frames captured for recognition

        Returns:
            None
        """
        def get_current_lecture() -> Optional[str]:
            """
            Determines the current lecture based on the time.

            Returns:
                str: The lecture identifier, e.g., 'Lecture_1', or None if no lecture is ongoing.
        """
            current_time = datetime.now().time()
            for lecture_number, (start_time_str, end_time_str) in LECTURE_TIMES.items():
                start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
                end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
                if start_time <= current_time <= end_time:
                    return f"Lecture_{lecture_number}"
            return None

        def construct_directory_path(lecture: str) -> str:
            """
            Constructs the directory path based on the parameters.

            Returns:
                str: The full directory path for saving the frame.
            """
            date_str = datetime.now().strftime("%d-%B-%Y")
            base_path = f"{SAVE_FRAMES_DIRECTORY}/{date_str}/{lecture}/Classroom_{self.cam_name}"
            return f"{base_path}/{COUNTING_PATH}/Raw_Frames" if save_counting_frames else f"{base_path}/{RECOGNITION_PATH}/Raw_Frames/PRESET_{position_of_frame}"

        lecture = get_current_lecture()
        if lecture is None:
            feedback_server_logger.warning("No ongoing lecture found for the current time.")
            return

        directory_path = construct_directory_path(lecture)
        check_for_directory(directory_path)
        file_name = f"Frame_{datetime.now().strftime('%H-%M-%S')}.jpg"

        try:
            cv2.imwrite(f"{directory_path}/{file_name}", frame_to_be_saved)
        except Exception as error:
            feedback_server_logger.error(f"Error in saving {directory_path}/{file_name} due to error: {error}")

    def publish_for_duration(self, preset_token: int, minutes: int):
        """
        Move to the given preset, wait for focus, then continuously
        call publish_frames until the duration elapses.
        """
        # 1) Goto the faculty preset
        self.set_camera_position(preset_token)
        time.sleep(2 * self.data["delay-for-zoom-and-focus"])
        # 2) Calculate end time
        end_time = datetime.now() + timedelta(minutes=minutes)
        # 3) Loop until window closes
        while datetime.now() < end_time:
            self.publish_frames(camera_preset=preset_token)

    def publish_frames(self, camera_preset):
        """
        Publishes the frames to the shared buffer.

        Returns:
            None
        """
        capture = cv2.VideoCapture(
            f"rtsp://{self.cam_username}:{self.cam_password}@{self.cam_ip}:554/live/0/MAIN"
        )

        # Read initial frames to stabilize
        for i in range(2):
            _, _ = capture.read()

        for frame_idx in range(self.data["number-of-frames"]):
            ret, frame = capture.read()

            # Retry mechanism
            if not ret:
                ret, frame = self.frame_capture_retry_mechanism(capture, ret)

            if ret:
                self.shared_buffer.put((frame, self.cam_name, self.cam_ip))

                # Saving frames for debugging frames
                if SAVE_FRAMES:
                    self.save_frames(frame_to_be_saved=frame, position_of_frame=camera_preset)
            else:
                multicam_server_logger.error(
                    f"Unable to publish frame from camera {self.cam_name} (url: {self.cam_ip})"
                )

            time.sleep(self.data["delay-between-frames"])

        capture.release()

    def mask_frames(self, position):
        """
        This function publishes the masked frames to the shared buffer.

        Returns:
            None
        """
        capture = cv2.VideoCapture(f"rtsp://{self.cam_username}:{self.cam_password}@{self.cam_ip}:554/live/0/MAIN")
        for i in range(2):
            _, _ = capture.read()

        ret, frame = capture.read()

        # Retry mechanism
        if not ret:
            ret, frame = self.frame_capture_retry_mechanism(capture, ret)

        if ret:
            # Fill the polygon with white color (255) in the mask
            if self.data["positions_to_count_students"][position]["masking-polygon-vertices"]:
                # Create a mask with the same dimensions as the frame
                mask = np.zeros_like(frame[:, :, 0])
                polygon_vertices = np.array(
                    self.data["positions_to_count_students"][position]["masking-polygon-vertices"], dtype=np.int32
                )

                cv2.fillPoly(mask, [polygon_vertices], (255, 255, 255))

                # Apply the mask to the frame
                masked_frame = cv2.bitwise_and(frame, frame, mask=mask)
            else:
                masked_frame = frame

            # Saving frames for debugging purpose
            if SAVE_FRAMES:
                self.save_frames(save_counting_frames=True, frame_to_be_saved=masked_frame, position_of_frame=0)

            # Push this frame for recognition as well
            self.shared_buffer.put((frame, self.cam_name, self.cam_ip))

            reshaped_frame = cv2.resize(masked_frame, (2304, 1312))
            return reshaped_frame
        else:
            multicam_server_logger.error(
                f"Unable to mask frame from camera {self.cam_name} (url: {self.cam_ip})"
            )

        capture.release()

    def reset_camera_position(self):
        """
        Resets the camera position.

        Returns:
            None
        """
        # Reset
        reset_token = self.data["reset-preset"]
        self.ptz.GotoPreset({"ProfileToken": self.media_profile.token, "PresetToken": reset_token})
        time.sleep(self.data["delay-for-zoom-and-focus"])
        self.publish_frames(camera_preset=reset_token)

    def set_camera_position(self, idx: int):
        """
        Sets the camera position corresponding to the index.

        Parameters:
            idx: Index of the camera position

        Returns:
            None
        """
        # Set the camera position
        self.ptz.GotoPreset({"ProfileToken": self.media_profile.token, "PresetToken": idx})

    def set_camera_position_for_student_count(self):
        """
        This method moves the camera to the bottom right corner of the classroom.

        Returns:
            None
        """
        try:
            masked_frames_list = []
            for position in self.data["positions_to_count_students"]:
                # Move camera to the preset position
                preset = self.data["positions_to_count_students"][position]["preset"]
                # print(f"Camera {self.cam_name} (url: {self.cam_ip}) is moving to position {preset}")
                self.set_camera_position(preset)
                # Wait for the camera to move to the focus token
                time.sleep(4 * self.data["delay-for-zoom-and-focus"])
                # Publish frames to the shared buffer
                masked_frame = self.mask_frames(position)
                masked_frames_list.append(masked_frame)

            # Publish the group of frames along with cam_name and cam_ip
            self.count_buffer.put((masked_frames_list, self.cam_name, self.cam_ip))

            # Reset the camera position
            self.reset_camera_position()
        except Exception as e:
            raise e

    def run_camera_cycle(self):
        """
        Runs the camera movement cycle as per the configuration.
        """
        try:
            # Move to faculty position
            faculty_preset = self.data["faculty-attendance"]
            # multicam_server_logger.info(f"Camera moving to faculty position {faculty_preset}")
            self.set_camera_position(faculty_preset)
            time.sleep(self.data["delay-for-zoom-and-focus"])

            # Capture frames at faculty position
            self.publish_frames(camera_preset=faculty_preset)
            self.publish_frames(camera_preset=faculty_preset)

            # Reset camera position
            # multicam_server_logger.info(f"Camera position resetting")
            self.reset_camera_position()

            # Traverse through class presets
            for student_preset in self.data["class-trace-presets"]:
                # if student_preset == 1:
                #     multicam_server_logger.info(f"Camera position resetting")
                # else:
                #     multicam_server_logger.info(f"Camera moving to position {student_preset}")
                self.set_camera_position(student_preset)
                time.sleep(self.data["delay-for-zoom-and-focus"])
                self.publish_frames(camera_preset=student_preset)

            # Reset camera position
            # multicam_server_logger.info(f"Camera position resetting")
            self.reset_camera_position()
        except Exception as e:
            raise e


def camera_thread(cam_name, cam_specifications, shared_buffer, count_buffer):
    cam_ip, cam_port, cam_username, cam_password, configuration_file, api_endpoint = cam_specifications.values()
    camera_object = PTZCamera(
        cam_name, cam_ip, cam_port, cam_username, cam_password, shared_buffer, count_buffer, configuration_file
    )

    while True:
        current_time = datetime.now()
        current_time_only = current_time.time()
        start_time = dt_time(9, 0)
        end_time = dt_time(16, 40)

        if start_time <= current_time_only <= end_time:
            try:
                # ─── NEW WINDOW logic ─────────────────────────────────────────────
                # check each lecture’s 5-minute windows
                for lec_no, (start_str, end_str) in LECTURE_TIMES.items():
                    today = current_time.date()
                    start_dt = datetime.combine(today, datetime.strptime(start_str, "%H:%M:%S").time())
                    end_dt   = datetime.combine(today, datetime.strptime(end_str,   "%H:%M:%S").time())

                    # 5 minutes after the lecture starts
                    if start_dt <= current_time <= start_dt + timedelta(minutes=1):
                        camera_object.publish_for_duration(
                            camera_object.data["faculty-attendance"],
                            minutes=5
                        )
                        break

                    # 5 minutes before the lecture ends
                    if end_dt - timedelta(minutes=1) <= current_time <= end_dt:
                        camera_object.publish_for_duration(
                            camera_object.data["faculty-attendance"],
                            minutes=5
                        )
                        break

                camera_object.run_camera_cycle()
                camera_object.set_camera_position_for_student_count()
            except Exception as error:
                multicam_server_logger.error(
                    f"Exception raised while running camera cycle for {cam_name} due to {error}. Attempting to reconnect..."
                )
                camera_object.initialized = False
            while not camera_object.initialized:
                try:
                    camera_object = PTZCamera(
                        cam_name, cam_ip, cam_port, cam_username, cam_password, shared_buffer, count_buffer, configuration_file
                    )
                    if camera_object.initialized:
                        multicam_server_logger.info(f"Reconnection successful for {cam_name} (url: {cam_ip})")
                        break
                    else:
                        time.sleep(PTZ_CAM_REINIT_WAIT_DURATION)
                except Exception as error:
                    multicam_server_logger.error(
                        f"Failed to reconnect {cam_name} (url: {cam_ip}) due to {error}. Retrying in {PTZ_CAM_REINIT_WAIT_DURATION} seconds..."
                    )
                    time.sleep(PTZ_CAM_REINIT_WAIT_DURATION)
        else:
            # Sleep until next 9:00 AM
            current_datetime = datetime.now()
            if current_time_only >= end_time:
                # Calculate time until 9 AM next day
                next_start_datetime = (
                        current_datetime + timedelta(days=1)
                ).replace(hour=9, minute=0, second=0, microsecond=0)
            else:
                # Time is before 9:00 AM today
                next_start_datetime = current_datetime.replace(hour=9, minute=0, second=0, microsecond=0)

            sleep_seconds = (next_start_datetime - current_datetime).total_seconds()

            # Convert sleep_seconds into HH:MM:SS
            hours, remainder = divmod(sleep_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            multicam_server_logger.info(
                f"Camera {cam_name} will sleep for {int(hours)} hours, {int(minutes)} minutes and {int(seconds)} seconds until {next_start_datetime}"
            )
            time.sleep(sleep_seconds)


def producer_main(shared_buffer, count_buffer):
    threads = []
    for cam_name, cam_specifications in PTZ_CAMS.items():
        ptz_cam_thread = threading.Thread(
            target=camera_thread, args=(cam_name, cam_specifications, shared_buffer, count_buffer)
        )
        threads.append(ptz_cam_thread)
        ptz_cam_thread.start()

    for thread in threads:
        thread.join()
