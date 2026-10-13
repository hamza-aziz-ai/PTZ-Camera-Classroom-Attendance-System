FROM nvcr.io/nvidia/pytorch:22.11-py3

# Update pip
RUN python3 -m pip install --upgrade pip

# Set timezone, for updating system in subsequent steps
#https://grigorkh.medium.com/fix-tzdata-hangs-docker-image-build-cdb52cc3360d
ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Change work directory in docker image
WORKDIR /Classroom-Attendance-System

# Install cron
RUN apt-get update && apt-get install -y cron ffmpeg libsm6 libxext6

# Add the script to the container
ADD run_scripts.sh /Classroom-Attendance-System/run_scripts.sh

COPY ./src/StudentCount/yolov9/requirements.txt ./src/StudentCount/yolov9/requirements.txt
COPY ./requirements.txt ./requirements.txt

# Install requirements
RUN python3 -m pip install -r requirements.txt
RUN python3 -m pip install -r src/StudentCount/yolov9/requirements.txt
RUN python3 -m pip install "opencv-python<4.8"

# Give execution rights to the script
RUN chmod +x /Classroom-Attendance-System/run_scripts.sh

# Add the cron job
RUN echo "0 17 * * 1-5 /Classroom-Attendance-System/run_scripts.sh" > /etc/cron.d/classroom-attendance-cron

# Give execution rights on the cron job file
RUN chmod 0644 /etc/cron.d/classroom-attendance-cron

# Apply cron job
RUN crontab /etc/cron.d/classroom-attendance-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Run the command on container startup
CMD cron && tail -f /var/log/cron.log

