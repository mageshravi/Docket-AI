FROM python:3.12-slim-bookworm
ENV PYTHONBUFFERED 1

ARG USERNAME=webinative
# replace with your actual UID and GID if not the default 1000
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

# create user
RUN groupadd --gid $USER_GID ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    # create a folder for vscode editor stuff
    && mkdir -p /home/${USERNAME}/.vscode-server \
    && chown ${USER_UID}:${USER_GID} /home/${USERNAME}/.vscode-server \
    # create a folder for project code
    && mkdir -p /home/${USERNAME}/code \
    && chown ${USER_UID}:${USER_GID} /home/${USERNAME}/code

# add sudo support
RUN apt-get update && apt-get install -y sudo \
    && echo ${USERNAME} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

# install GIT
RUN apt install -y git

USER ${USERNAME}
WORKDIR /home/${USERNAME}/code
ADD requirements.in /home/${USERNAME}/code/
ADD requirements.txt /home/${USERNAME}/code/

# install python packages locally for user "webinative"
RUN pip install --user pip-tools \
    && export PATH="${PATH}:/home/${USERNAME}/.local/bin" \
    && python -m pip install --user -r requirements.txt

# not switching back to "root" user
