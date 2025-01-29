# Use Ubuntu 22.04 as the base image  
FROM ubuntu:22.04 
  
# Set environment variables to prevent Python from writing .pyc files and buffering stdout/stderr  
ENV PYTHONDONTWRITEBYTECODE=1  
ENV PYTHONUNBUFFERED=1  
ENV DEBIAN_FRONTEND=noninteractive  
  
# Install necessary system packages  
RUN apt-get update && \  
    apt-get install -y --no-install-recommends \  
        wget \  
        gnupg \  
        ca-certificates \  
        lsb-release \  
        curl \  
        unzip \  
        libgssapi-krb5-2 \  
        libssl3 \  
        software-properties-common \  
        && \  
    rm -rf /var/lib/apt/lists/*  
  
# Install Python 3.10  
RUN add-apt-repository -y ppa:deadsnakes/ppa && \  
    apt-get update && \  
    apt-get install -y python3.10 python3.10-distutils && \  
    rm -rf /var/lib/apt/lists/*  
  
# Install pip for Python 3.10  
RUN wget https://bootstrap.pypa.io/get-pip.py && \  
    python3.10 get-pip.py && \  
    rm get-pip.py  
  
# Import the MongoDB public GPG key  
RUN wget -qO - https://pgp.mongodb.com/server-8.0.asc | \  
    gpg --dearmor -o /usr/share/keyrings/mongodb-server-8.0.gpg  
  
# Create the MongoDB Enterprise source list file  
RUN echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.com/apt/ubuntu jammy/mongodb-enterprise/8.0 multiverse" | \  
    tee /etc/apt/sources.list.d/mongodb-enterprise.list  
  
# Update package database and install MongoDB Enterprise  
RUN apt-get update && \  
    apt-get install -y mongodb-enterprise && \  
    rm -rf /var/lib/apt/lists/*  
  
# Install Python dependencies  
RUN pip3.10 install --no-cache-dir "pymongo[encryption]>=4.5"  
  
# Ensure mongocryptd is in the PATH  
ENV PATH="/usr/bin:${PATH}"  
  
# Set the working directory  
WORKDIR /app  
  
# Copy the application code  
COPY . /app  
  
CMD ["python3.10", "queryable-encryption.py"]  
