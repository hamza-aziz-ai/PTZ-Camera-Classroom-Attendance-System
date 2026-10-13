#!/bin/bash

# Description: This script is used to deploy the project
# Author: Anubhav Patrick
# Modification: Hamza Aziz
# Created: Thur September 14 2023
# Modified: Tuesday, 4 June 2024

# make healthcheck scripts executable
# shellcheck disable=SC2046
chmod 777 $(pwd)/src/database_server/healthcheck_db_controller.sh
# shellcheck disable=SC2046
chmod 777 $(pwd)/src/api/healthcheck_api.sh
# shellcheck disable=SC2046
chmod 777 $(pwd)/src/StudentCount/healthcheck_student_count.sh

# Load the INSTITUTE and IP_ADDRESS variable from master.env
. set_configuration.sh

# start main program, redis, database and feedback controller, api service and face liveness detection
echo "start main program, redis, database and feedback controller, api service and face liveness detection"
docker-compose up -d
