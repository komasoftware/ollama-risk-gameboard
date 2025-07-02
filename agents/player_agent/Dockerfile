FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including gcloud CLI
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Google Cloud CLI
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update \
    && apt-get install -y google-cloud-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY . .

# Expose port 8080 (Cloud Run standard)
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV HOST=0.0.0.0

# Run the agent
CMD ["python", "agent_player.py"] 