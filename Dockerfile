# syntax=docker/dockerfile:experimental  
  
# Use Ubuntu 20.04 as the base image for amd64  
FROM --platform=linux/amd64 ubuntu:20.04  
  
# Set noninteractive frontend to suppress prompts  
ENV DEBIAN_FRONTEND=noninteractive  
ENV TZ=Etc/UTC  
ENV LD_LIBRARY_PATH=/usr/local/lib  
  
# Set the timezone and suppress tzdata prompts  
RUN ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \  
    echo $TZ > /etc/timezone  
  
# Install required packages and dependencies  
RUN apt-get update && \  
    apt-get install -y --no-install-recommends \  
        build-essential \  
        cmake \  
        git \  
        gcc \  
        python3 \  
        python3-dev \  
        python3-pip \  
        libssl-dev \  
        libffi-dev \  
        gnupg \  
        wget \  
        curl \  
        ca-certificates \  
        tzdata \  
        lsb-release && \  
    apt-get clean && \  
    rm -rf /var/lib/apt/lists/*  
  
# Add MongoDB Enterprise's official GPG key and repository for Ubuntu 20.04 (focal)  
RUN wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add - && \  
    echo "deb [ arch=amd64 ] https://repo.mongodb.com/apt/ubuntu focal/mongodb-enterprise/6.0 multiverse" | \  
    tee /etc/apt/sources.list.d/mongodb-enterprise.list  
  
# Install MongoDB Enterprise  
RUN apt-get update && \  
    apt-get install -y --no-install-recommends mongodb-enterprise && \  
    apt-get clean && \  
    rm -rf /var/lib/apt/lists/*  
  
# Create MongoDB data directories and set permissions  
RUN mkdir -p /data/db /data/configdb && \  
    chown -R mongodb:mongodb /data/db /data/configdb && \  
    chmod -R 0755 /data/db /data/configdb  
  
# Build libmongocrypt from source  
RUN git clone --branch 1.8.0 https://github.com/mongodb/libmongocrypt /tmp/libmongocrypt && \  
    mkdir -p /tmp/libmongocrypt/cmake-build && \  
    cd /tmp/libmongocrypt/cmake-build && \  
    cmake -DCMAKE_BUILD_TYPE=Release .. && \  
    cmake --build . --target install && \  
    rm -rf /tmp/libmongocrypt  
  
# Install Python dependencies, including PyMongo with CSFLE support  
RUN pip3 install --no-cache-dir --upgrade pip && \  
    pip3 install --no-cache-dir pymongo[encryption]==4.5.0 cryptography  
  
# Copy the Python script into the container  
COPY csfle_demo.py /csfle_demo.py  
  
# Expose MongoDB's default port  
EXPOSE 27017  
  
# Start MongoDB, mongocryptd, and run the Python script  
CMD ["bash", "-c", "mongod --bind_ip_all --logpath /var/log/mongod.log --logappend --fork && mongocryptd --logpath /var/log/mongocryptd.log --logappend --fork && python3 /csfle_demo.py && tail -f /dev/null"]  
