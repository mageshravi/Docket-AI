#!/bin/bash

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

execute_command "git checkout master && git pull" "Failed to pull latest changes."
execute_command "bun run build:css" "Failed to build CSS"
execute_command "bun run build:js" "Failed to build JS"
execute_command "echo \"Tag: $(git describe --tags). Rollout date: $(date +'%Y_%m_%d')\" > version_info.txt" "Failed to create version_info file."
execute_command "tar -czf master.tar.gz core django_42_base static templates manage.py pip-requirements version_info.txt" "Failed to create deployment archive."
execute_command "scp master.tar.gz root@remote:/path/to/releases" "Failed to copy deployment archive to remote server."

echo "Cleaning up..."

rm master.tar.gz version_info.txt

echo "${GREEN}Deployment archive copied to remote successfully.${RESET}"
