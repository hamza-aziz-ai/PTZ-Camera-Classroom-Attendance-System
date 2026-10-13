# Use the official Python image as the base image
FROM python:3.8-slim-buster

# API_KEY and POSTGRES_* are injected at runtime from secrets.env (docker-compose env_file)

# Upgrade pip
RUN python3 -m pip install --upgrade pip

ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update -y && apt install -y ffmpeg libsm6 libxext6

# Copy the project contents - src/ folder to docker image
WORKDIR /Classroom-Attendance-System
COPY src/ src/

# Install requirements
RUN python3 -m pip install -r src/api/requirements.txt

# Expose the port your FastAPI app will run on
EXPOSE 8000

# Start the FastAPI application
CMD ["python3", "src/api/app.py"]
