#!/bin/bash

# usage: rollout_release.sh <tar_file>

RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
CYAN=$(tput setaf 6)
RESET=$(tput sgr0)

# Function to execute command and handle errors
execute_command() {
    local cmd="$1"
    local error_message="${2:-Command failed: $cmd}"

    printf "${CYAN}Executing: ${YELLOW}$cmd${RESET}\n"
    eval "$cmd"

    if [ $? -ne 0 ]; then
        printf "${RED}ERROR: $error_message${RESET}\n" >&2
        exit 1
    fi
}

SITE_NAME="mysite.com"
RELEASES_DIR=/opt/$SITE_NAME/data/releases
TAR_FILENAME=$1
VENV_BIN=/opt/$SITE_NAME/venv/bin

# Extract TAR file
execute_command "tar -xzf $RELEASES_DIR/$TAR_FILENAME -C /opt/$SITE_NAME/" "Failed to extract deployment archive."

cd /opt/$SITE_NAME

source $VENV_BIN/activate

# Deployment commands
execute_command "$VENV_BIN/pip3 install -r pip-requirements" "Failed to install dependencies."
execute_command "$VENV_BIN/python3 manage.py check --deploy" "Deployment checks failed."
execute_command "$VENV_BIN/python3 manage.py migrate" "Database migration failed."
execute_command "$VENV_BIN/python3 manage.py collectstatic --noinput" "Static files collection failed."

# Restart services
execute_command "sudo systemctl restart $SITE_NAME.service" "Failed to restart systemd service."

printf "${GREEN}Rollout completed successfully.${RESET}\n"
