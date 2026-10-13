# syntax=docker/dockerfile:1

# Step 1 - Select base docker image
# FROM python:3.8-slim-buster
FROM nvcr.io/nvidia/pytorch:22.11-py3

RUN python3 -m pip install --upgrade pip
# RUN python3 -m pip install --upgrade tensorrt
# RUN python3 -m pip install --upgrade tensorrt_lean
# RUN python3 -m pip install --upgrade tensorrt_dispatch
# RUN python3 -m pip install --upgrade onnx onnxruntime-gpu onnxsim
# RUN python3 -m pip install --upgrade nvidia-tensorrt

# Step 3 - Set timezone, for updating system in subsequent steps
#https://grigorkh.medium.com/fix-tzdata-hangs-docker-image-build-cdb52cc3360d
ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Step 4 - Change work directory in docker image
WORKDIR /Classroom-Attendance-System

# Step 5 - Upgrade and install additional libraries to work on videos
RUN apt update -y
RUN apt install ffmpeg libsm6 libxext6 -y

# Step 6 - Copy and install project requirements
COPY ./best.pt /Classroom-Attendance-System/best.pt
COPY ./yolov9-e-converted.pt /Classroom-Attendance-System/yolov9-e-converted.pt
COPY ./src/StudentCount/yolov9/requirements.txt ./src/StudentCount/yolov9/requirements.txt
COPY ./src/StudentCount/requirements.txt ./src/StudentCount/requirements.txt
RUN python3 -m pip install -r src/StudentCount/yolov9/requirements.txt
RUN python3 -m pip install -r src/StudentCount/requirements.txt
RUN python3 -m pip install "opencv-python<4.8"

# Step 7 - Uncomment following line if we want to copy project contents to docker image
#COPY . .

# Expose the port your FastAPI app will run on
EXPOSE 5011

# Step 8 - Give starting point of project
CMD ["python3", "src/StudentCount/app.py"]
# For just starting the container (i.e., we will have to manually execute the program from inside the container), uncomment next line
# CMD ["sh"]