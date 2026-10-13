FROM python:3.8-slim-buster

# POSTGRES_* are injected at runtime from secrets.env (docker-compose env_file)

# Step 2 - Upgrade pip
RUN python3 -m pip install --upgrade pip --no-cache-dir

ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update -y && apt install -y ffmpeg libsm6 libxext6

# Step 2 - Copy the project contents - src/ folder to docker image
WORKDIR /Classroom-Attendance-System
COPY src/database_server/requirements.txt src/database_server/requirements.txt

# Step 3 - Install project requirements
RUN python3 -m pip install -r src/database_server/requirements.txt

# Step 4 - Remove requirements.txt
RUN rm -rf src/

EXPOSE 20002

# Step 5 - Give starting point of project
CMD ["python3", "src/database_server/database_server_controller.py"]

