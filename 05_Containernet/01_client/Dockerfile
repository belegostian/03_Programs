# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.10-slim

# Set default shell to /bin/bash
SHELL [ "/bin/bash", "-c" ]

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install the required packages for Containernet
RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    curl \
    bash \
    iproute2 \
    iputils-ping

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Set the working directory
WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# The CMD field will be ignored by Containernet, but keep for other purposes
CMD ["python", "ctest1.py"]
