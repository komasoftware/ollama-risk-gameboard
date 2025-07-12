FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
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
CMD ["python", "workflow_agent.py"] 