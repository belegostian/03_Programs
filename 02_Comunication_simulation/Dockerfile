# This is sample for wrapped-script containers
FROM python:3.10-slim

# Install any needed packages specified in requirements.txt
RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    curl

# Use a virtual environment to avoid running pip as root
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy the current directory contents into the container at /app
COPY . /app

# Set the working directory to /app
WORKDIR /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
