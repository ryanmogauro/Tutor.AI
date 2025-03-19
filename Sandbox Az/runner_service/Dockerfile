FROM python:3.11-slim

# Install required programming language runtimes
RUN apt-get update && apt-get install -y \
    nodejs npm \
    openjdk-17-jdk \
    golang \
    && npm install -g typescript \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Setup non-root user
RUN useradd -m sandbox

# Create code execution directory with proper permissions
RUN mkdir -p /home/sandbox/code && \
    chown -R sandbox:sandbox /home/sandbox/code && \
    chmod 755 /home/sandbox/code

# Copy application files
COPY run_server.py /app/
COPY code_executor.py /app/
COPY startup.sh /app/

# Set execution permission for startup script
RUN chmod +x /app/startup.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose the port
EXPOSE 8000

# Switch to non-root user for security
USER sandbox

# Start the application
CMD ["/app/startup.sh"]