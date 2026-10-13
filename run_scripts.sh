#!/bin/bash

# Define the date (current date)
DATE=$(date +"%d-%B-%Y")
YEAR=$(date +"%Y")
MONTH=$(date +"%B")

# Check if today is Saturday (6) or Sunday (7)
DAY_OF_WEEK=$(date +%u)
if [ "$DAY_OF_WEEK" -eq 6 ] || [ "$DAY_OF_WEEK" -eq 7 ]; then
    echo "Today is Saturday or Sunday. Exiting."
    exit 0
fi

# Define the base directory
BASE_DIR="CLASSROOM-ATTENDANCE-TESTING/$DATE"

# Check if the base directory exists
if [ ! -d "$BASE_DIR" ]; then
    echo "No data available for $DATE. Exiting."
    exit 0
fi

# Define log file
LOG_FILE="logs/Attendance-Report/${YEAR}/${MONTH}/${DATE}.log"

# Create log directory if it does not exist
mkdir -p logs/Attendance-Report/"${YEAR}"/"${MONTH}"

# Start logging
{
    echo "Script execution started: $(date)"
    echo
    echo

    # Loop through each lecture directory
    for LECTURE_DIR in "$BASE_DIR"/Lecture_*; do
        # Extract the lecture number
        LECTURE=$(basename "$LECTURE_DIR" | cut -d'_' -f2)

        echo "###########################################################################################################################################"
        echo "PROCESSING LECTURE: $LECTURE"
        echo "###########################################################################################################################################"
        echo

        # Loop through each classroom directory within the lecture directory
        for CLASSROOM_DIR in "$LECTURE_DIR"/*/; do
            # Extract the classroom name (string after _)
            CLASSROOM=$(basename "$CLASSROOM_DIR" | cut -d'_' -f2-)

            echo "-------------------------------------------------------------------------------------------------------------------------------------------"
            echo "PROCESSING CLASSROOM: $CLASSROOM"
            echo "-------------------------------------------------------------------------------------------------------------------------------------------"

            echo

            # Run the Python scripts
            python3 src/util/plot_bbox_face_recognition.py --date "$DATE" --lecture "$LECTURE" --classroom "$CLASSROOM"

            echo

            python3 src/util/plot_bbox_student_count.py --date "$DATE" --lecture "$LECTURE" --classroom "$CLASSROOM"
            echo "-------------------------------------------------------------------------------------------------------------------------------------------"
            echo
        done
        echo "###########################################################################################################################################"
        echo
        echo
    done

    echo "Script execution finished: $(date)"
} >> "$LOG_FILE" 2>&1
