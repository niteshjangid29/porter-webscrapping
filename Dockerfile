# Debian-based Python image (multi-arch)
FROM python:3.10-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

# Install Chromium, ChromeDriver, and any needed libs
RUN apt-get update && apt-get install -y \ 
    chromium chromium-driver \ 
    libgl1-mesa-glx \ 
    libglib2.0-0 libnss3 libx11-6 libxcb1 libxcomposite1 libxcursor1 libxdamage1 \ 
    libxext6 libxfixes3 libxi6 libxtst6 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY ./requirements.txt ./requirements.txt

# python dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# We expect the user to volume-mount the file into place and buffering can be a 
# problem, so use unbuffered mode for reading the input.csv
ENV PYTHONUNBUFFERED=1

# NOTE: depends on a /tmp/input.csv existing
# ENV CHROMEDRIVER_PATH=$CHROMEDRIVER_DIR
# CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
CMD ["fastapi", "run", "main.py"]