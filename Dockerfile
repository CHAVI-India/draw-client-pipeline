# Stage 1: Base build stage
FROM python:3.13-slim-bookworm AS builder
 
# Create the app directory
RUN mkdir /app
 
# Set the working directory
WORKDIR /app
 
# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 
 
# Install dependencies first for caching benefit
RUN pip install --upgrade pip 
COPY requirements.txt /app/ 
RUN pip install --no-cache-dir -r requirements.txt
 
# Stage 2: Production stage
FROM python:3
 
# Create user and required directories
RUN groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser appuser && \
    mkdir /app && \
    mkdir -p /app/static && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app
 
# Copy the Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
 
# Set the working directory
WORKDIR /app
 
# Copy static files first
COPY --chown=appuser:appuser static/ /app/static/

# Copy remaining application code
COPY --chown=appuser:appuser . .

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

# Switch to non-root user
USER appuser

# We do that in the entrypoint script after setting up symlinks

# Expose the application port
EXPOSE 8000 

# Make entry file executable
RUN chmod +x /app/entrypoint.docker.sh
 
# Start the application using the entrypoint script
CMD ["/app/entrypoint.docker.sh"]