# syntax=docker/dockerfile:1

# Step 1 - Select base docker image
FROM python:3.8-slim-buster

# CAM_* credentials, camera IPs and ERP endpoints are injected at runtime from secrets.env (docker-compose env_file)

# Step 2 - Upgrade pip
RUN python3 -m pip install --upgrade pip

# Step 3 - Set timezone, for updating system in subsequent steps
# https://grigorkh.medium.com/fix-tzdata-hangs-docker-image-build-cdb52cc3360d
ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Step 4 - Upgrade and install additional libraries to work on videos
RUN apt update -y && apt install -y ffmpeg libsm6 libxext6

# Step 5 - Create a user hamza
RUN useradd -ms /bin/bash hamza

# Step 6 - Set up project directory
WORKDIR /Classroom-Attendance-System

# Step 7 - Copy the project contents - src/ folder to docker image
COPY ./requirements.txt ./requirements.txt

# Step 8 - Change ownership of the working directory
RUN chown -R hamza:hamza /Classroom-Attendance-System

# Step 9 - Make the directory accessible by everyone
RUN chmod 755 /Classroom-Attendance-System

# Step 10 - Install project requirements
RUN python3 -m pip install -r requirements.txt

# Step 11 - Give starting point of project
CMD ["python3", "src/main.py"]
