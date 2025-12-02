#!/bin/bash

CYAN_BG=$(tput setab 6)
BOLD=$(tput bold)
RESET=$(tput sgr0)

printf "${CYAN_BG}${BOLD} Applying database migrations... ${RESET}\n"
python manage.py migrate

printf "${CYAN_BG}${BOLD} Creating superuser... ${RESET}\n"
python manage.py createsuperuser --noinput
