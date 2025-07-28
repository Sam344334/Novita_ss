FROM python:3.10-slim

# Set working directory
WORKDIR /code

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app.py .

# Expose port
EXPOSE 7860

# Run the app
CMD ["python", "app.py"]
