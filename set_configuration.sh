#!/bin/bash

# Source the get_ip.sh script to import the IP_ADDRESS variable
source ./get_ip.sh

# Use the IP_ADDRESS variable
echo "The system's IP address is: $IP_ADDRESS"


# Load ABESIT_HOST_IP / GLBITM_HOST_IP from the untracked secrets.env
set -a
source ./secrets.env
set +a

# Conditionally set the INSTITUTE based on the host IP_ADDRESS
if [ "$IP_ADDRESS" == "$ABESIT_HOST_IP" ]; then
    export INSTITUTE="ABESIT"
elif [ "$IP_ADDRESS" == "$GLBITM_HOST_IP" ]; then
    export INSTITUTE="GLBITM"
else
    export INSTITUTE="ABESIT"
fi


# Update the master.env file (created from the template on a fresh clone)
[ -f master.env ] || cp master.env.example master.env
sed -i "/^IP_ADDRESS=/c\IP_ADDRESS=$IP_ADDRESS" master.env
sed -i "/^INSTITUTE=/c\INSTITUTE=$INSTITUTE" master.env
