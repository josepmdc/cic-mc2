FROM python:3.11

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app/

# Expose port 5000 for the Flask app
EXPOSE 5001

# Start the Flask app
CMD ["gunicorn", "-b", "0.0.0.0:5001", "app:app"]
