"""
This module contains the default parameters used by the app
"""
from dotenv import load_dotenv
import os

########################################################################################################################
# Project Configuration for each INSTITUTE
########################################################################################################################
load_dotenv("master.env")
# Credentials, camera IPs and ERP endpoints live in the untracked secrets.env (see secrets.env.example).
# Docker Compose injects it via env_file; load it here too for scripts run on the host.
load_dotenv("secrets.env")
INSTITUTE = os.getenv("INSTITUTE")
IP_ADDRESS = os.getenv("IP_ADDRESS")

# PTZ Camera Details
CAM_PORT = os.environ.get("CAM_PORT")
CAM_USERNAME = os.environ.get("CAM_USERNAME")
CAM_PASSWORD = os.environ.get("CAM_PASSWORD")
CONFIGURATION_FOLDER = f"src/camera_configuration_files/{INSTITUTE}"

# Configuration for each INSTITUTE
DATA_CONFIGURATION = {
    "ABESIT": {
        "PTZ_CAMS": {
            "supernova": {
                "cam-ip": os.getenv("CAM_IP_SUPERNOVA"),
                "cam-port": CAM_PORT,  # CAM_PORT
                "cam-username": CAM_USERNAME,  # CAM_USERNAME
                "cam-password": CAM_PASSWORD,  # CAM_PASSWORD
                "configuration-file": os.path.join(CONFIGURATION_FOLDER, "supernova.json"),
                "sim_attendance_api_endpoint": os.getenv("ERP_ENDPOINT_SUPERNOVA")
            },
            "2F-32": {
                "cam-ip": os.getenv("CAM_IP_2F_32"),
                "cam-port": CAM_PORT,
                "cam-username": CAM_USERNAME,
                "cam-password": CAM_PASSWORD,
                "configuration-file": os.path.join(CONFIGURATION_FOLDER, "2F-32.json"),
                "sim_attendance_api_endpoint": os.getenv("ERP_ENDPOINT_2F_32")
            }
        },
        "LECTURE_TIMES": {
            1: ("09:00:00", "09:49:59"),
            2: ("09:50:00", "10:39:59"),
            3: ("10:40:00", "11:29:59"),
            4: ("11:30:00", "12:19:59"),
            5: ("13:20:00", "14:09:59"),
            6: ("14:10:00", "14:59:59"),
            7: ("15:00:00", "15:49:59"),
            8: ("15:50:00", "16:39:59")
        }
    },
    "GLBITM": {
        "PTZ_CAMS": {
            "AB-1_319": {
                "cam-ip": os.getenv("CAM_IP_AB_1_319"),
                "cam-port": CAM_PORT,
                "cam-username": CAM_USERNAME,
                "cam-password": CAM_PASSWORD,
                "configuration-file": os.path.join(CONFIGURATION_FOLDER, "AB-1_319.json"),
                "sim_attendance_api_endpoint": os.getenv("ERP_ENDPOINT_AB_1_319")
            },
        },
        "LECTURE_TIMES": {
            1: ("09:10:00", "10:00:00"),
            2: ("10:01:00", "10:50:00"),
            3: ("10:51:00", "11:40:00"),
            4: ("11:41:00", "12:30:00"),
            5: ("13:11:00", "14:00:00"),
            6: ("14:01:00", "14:50:00"),
            7: ("14:51:00", "15:40:00"),
            8: ("15:41:00", "16:30:00")
        }
    }
}

PTZ_CAMS = DATA_CONFIGURATION[INSTITUTE]["PTZ_CAMS"]
# Lecture times
LECTURE_TIMES = DATA_CONFIGURATION[INSTITUTE]["LECTURE_TIMES"]
########################################################################################################################

########################################################################################################################
# Parameters specific to Project Paths
########################################################################################################################
# Mapping of Admission Numbers to University Roll Number
MAPPING_FILE = f"FACIAL_RECOGNITION_DATASET/{INSTITUTE}/mapping.csv"

# The path where logs will be stored
LOGS_FOLDER = "logs"
MULTICAM_SERVER_LOGGER = "multicam_server"
DATABASE_SERVER_LOGGER = "database_server"
API_LOGGER = "api"
FEEDBACK_LOGGER = "feedback_server"
########################################################################################################################


########################################################################################################################
# Parameters specific to Cameras, Livestreams and Buffers
########################################################################################################################
# set BATCH_SIZE for face detection
BATCH_SIZE = 1  # for DGX 64, 8 for CPU

# buffer size for video streaming to minimize inconsistent network conditions
LIVE_STREAM_BUFFER_SIZE = 4096  # single camera

# buffer size for frames on which face recognition will be performed
LIVE_STREAM_BUFFER_PURGE_SIZE = 256  # 256 for DGX

# Speed of the camera
MOVEMENT_SPEED = 1

# Set wait duration for PTZ camera re-initialization if we are not able to initialize the cam
PTZ_CAM_REINIT_WAIT_DURATION = 30  # seconds

# Set maximum retries limit if we are unable to capture the frame
RETRY_COUNT = 5
########################################################################################################################

########################################################################################################################
# Parameters specific to YOLOv9 Person Detection for Counting Students in Classroom
YOLOv9_PERSON_DETECTION_HOST = f"http://{IP_ADDRESS}"
YOLOv9_PERSON_DETECTION_PORT = "5011"

STUDENT_COUNT_THRESHOLD = 3
########################################################################################################################


########################################################################################################################
# Parameters specific to InsightFace-REST face detection
########################################################################################################################
# InsightFace-REST host
INSIGHTFACE_HOST = f"http://{IP_ADDRESS}"

# InsightFace-REST port
INSIGHTFACE_PORT = "6385"  # 6385 for DGX, 18081 for the local system
# INSIGHTFACE_PORT_2 = "6385"

# Threaded GPU Flag
THREAD_FLAG = True
# Multi-Process GPU Flag
MULTIPROCESSING_FLAG = False

# Number of threads to be used for face recognition
NUMBER_OF_THREADS = 4

# Number of processes to be used for face recognition
NUMBER_OF_PROCESSES = 2

# Boolean flag to indicate whether to save the landmarks of the images while creating embeddings
SAVE_LANDMARKS = False
########################################################################################################################

########################################################################################################################
# Parameters specific to Face-Liveness-Detection
########################################################################################################################
# Face-Liveness-Detection host
FACE_LIVENESS_DETECTION_HOST = f"http://{IP_ADDRESS}"

# Face-Liveness-Detection port
FACE_LIVENESS_DETECTION_PORT = 6386

# Boolean flag to indicate whether to enable face liveness detection
ENABLE_FACE_LIVENESS_DETECTION = False
########################################################################################################################


########################################################################################################################
# Parameters specific to Milvus Vector Database
########################################################################################################################
# Milvus host
MILVUS_HOST = IP_ADDRESS

# Milvus port
MILVUS_PORT = "19530"

# Vector metric type and index type
METRIC_TYPE = "L2"    # L2, COSINE
INDEX_TYPE = "GPU_IVF_FLAT"

# Threshold
FACE_MATCHING_TOLERANCE = 0.5 if METRIC_TYPE == "COSINE" else 0.95    # For L2 Metric Type

# Milvus collection name
MILVUS_COLLECTION_NAME = f"{INSTITUTE}_FACE_DATA_COLLECTION_FOR_{METRIC_TYPE}"
########################################################################################################################


########################################################################################################################
# Parameters specific to Database Server Which Connects to Database (REDIS)
########################################################################################################################
# DATABASE Host
DATABASE_HOST = IP_ADDRESS  # IP of the machine where the database is running

# DATABASE port
DATABASE_PORT = 20002

# Boolean flag to indicate whether to enable the database server
ENABLE_DATABASE_SERVER = True
########################################################################################################################


########################################################################################################################
# Parameters specific to PostgreSQL Database
########################################################################################################################
# PostgreSQL Host
POSTGRESQL_HOST = IP_ADDRESS

# PostgreSQL port
POSTGRESQL_PORT = 5432

# PostgreSQL Database Name
POSTGRESQL_DATABASE = f"{INSTITUTE}_PTZ_Classroom_Attendance"

# If the person is recognized by the same camera within this time threshold, the entry will not be added to the database
SAME_CAM_TIME_ENTRY_THRESHOLD = 5    # minutes
########################################################################################################################


########################################################################################################################
# Parameters specific to Feedback given to the user
########################################################################################################################
# Wait time for API response in seconds
API_RESPONSE_TIMEOUT = 1 * 60

# Boolean Flag to indicate whether to save frames
SAVE_FRAMES = True

# Path to save the frames
SAVE_FRAMES_DIRECTORY = "CLASSROOM-ATTENDANCE-TESTING"
RECOGNITION_PATH = "RecognitionFrames"
COUNTING_PATH = "CountingFrames"

# Attendance JSON File Paths
FILE_PATHS = [
    f"{SAVE_FRAMES_DIRECTORY}/{{date}}/Lecture_1/attendance.json",
    f"{SAVE_FRAMES_DIRECTORY}/{{date}}/Lecture_2/attendance.json",
    f"{SAVE_FRAMES_DIRECTORY}/{{date}}/Lecture_3/attendance.json",
    f"{SAVE_FRAMES_DIRECTORY}/{{date}}/Lecture_4/attendance.json",
    f"{SAVE_FRAMES_DIRECTORY}/{{date}}/Lecture_5/attendance.json",
    f"{SAVE_FRAMES_DIRECTORY}/{{date}}/Lecture_6/attendance.json",
    f"{SAVE_FRAMES_DIRECTORY}/{{date}}/Lecture_7/attendance.json",
    f"{SAVE_FRAMES_DIRECTORY}/{{date}}/Lecture_8/attendance.json"
]
########################################################################################################################
