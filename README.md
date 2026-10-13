# Facial-Recognition-Classroom-Attendance-System

This project is an extended version of the [Multi-Person-Face-Recognition](https://github.com/anubhavpatrick/Multi-Person-Face-Recognition) project. The project is a classroom attendance system that uses facial recognition to mark the attendance of students in a classroom.

## How to Start the Project?

This project is still under development and is partially dependent on the [Multi-Person-Face-Recognition](https://github.com/anubhavpatrick/Multi-Person-Face-Recognition) project. The following steps will help you to start the project:

Clone the [Multi-Person-Face-Recognition](https://github.com/anubhavpatrick/Multi-Person-Face-Recognition) project.

```bash
# Clone repository from GitHub
git clone git@github.com:anubhavpatrick/Multi-Person-Face-Recognition.git CCTV-Face-Recognition-Attendance-System

# Make every bash script inside the repository executable
find CCTV-Face-Recognition-Attendance-System -type f -name "*.sh" -exec chmod +x {} \;

# Change directory to the project
cd CCTV-Face-Recognition-Attendance-System
```

Update the master configuration for the project using the following command

```bash
# Update Institute Name and IP Address
nano master.env
```

Update INSTITUTE and IP_ADDRESS

```dotenv
INSTITUTE=ABESIT
IP_ADDRESS=<host IP address>
```

Now save the file by pressing `Ctrl+X` &rarr; `Y` &rarr; `Enter`


Start the container using the following command

```bash
# Execute the script
. start_standalone_services.sh
```

Clone this project

```bash
git clone git@github.com:anubhavpatrick/PTZ-Face-Recognition.git PTZ-Face-Recognition-Classroom-Attendance-System

# Make every bash script inside the repository executable
find PTZ-Face-Recognition-Classroom-Attendance-System -type f -name "*.sh" -exec chmod +x {} \;

# Change directory to the project
cd PTZ-Face-Recognition-Classroom-Attendance-System
```

Update the master configuration for the project using the following command

```bash
# Update Institute Name and IP Address
nano master.env
```

Update INSTITUTE and IP_ADDRESS

```dotenv
INSTITUTE=ABESIT
IP_ADDRESS=<host IP address>
```

Now save the file by pressing `Ctrl+X` &rarr; `Y` &rarr; `Enter`

Create the secrets file from the template and fill in the real values (database and camera credentials, API key, camera IPs, institute ERP endpoints, host IPs). `secrets.env` is gitignored and must never be committed.

```bash
cp secrets.env.example secrets.env
nano secrets.env
```

Start the project in the containerized form using the following command

```bash
# Start new containers for the updated redis-database, database-controller, student-counting and api for this project
./start_project.sh
```

## Ports and GPU information for the project containers

| Container Name                                      | Image Name                                                  | Port  | GPU        |
|-----------------------------------------------------|-------------------------------------------------------------|-------|------------|
| ptz-classroom-face-recognition-database-controller  | ptz-classroom-face-recognition-database-controller:v-beta   | 20002 | N/A        |
| ptz-classroom-face-recognition-api                  | ptz-classroom-face-recognition-api:v-beta                   | 9093  | N/A        |
| ptz-classroom-face-recognition-student-count        | ptz-classroom-face-recognition-student-count:v-beta_yolov9  | 5011  | 7:2 (5 GB) |

## Changing Parameters and Camera Configurations

- If you want change the parameters for the project, you can do this by editing the file under the location [`src/parameters.py`](src/parameters.py)
- If you want to change the configurations for the camera, you can do this by editing the JSON file named by the *classroom name* under the location [`src/camera_configuration_files`](src/camera_configuration_files)
- If you want to change the ports exposed to the docker containers, you can do this by editing the `ports` defined in [`docker-compose.yml`](docker-compose.yml)

## Camera Information

Camera IPs and credentials are kept in `secrets.env`. Each classroom has a preset configuration file:

| Classroom Name | Institute Profile | Configuration File                                      |
|----------------|-------------------|---------------------------------------------------------|
| supernova      | ABESIT            | `src/camera_configuration_files/ABESIT/supernova.json`  |
| 2F-32          | ABESIT            | `src/camera_configuration_files/ABESIT/2F-32.json`      |
| AB-1_319       | GLBITM            | `src/camera_configuration_files/GLBITM/AB-1_319.json`   |
