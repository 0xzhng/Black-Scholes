FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for Streamlit
EXPOSE 8501

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create a script to run both server and streamlit
RUN echo '#!/bin/bash\n\
python server.py & \n\
streamlit run main.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"] 
# Modified on 2024-11-28 00:00:00

# Modified on 2024-11-28 00:00:00

# Modified on 2024-11-29 00:00:00

# Modified on 2024-12-08 00:00:00

# Modified on 2024-12-13 00:00:00

# Modified on 2024-12-17 00:00:00

# Modified on 2024-12-18 00:00:00

# Modified on 2024-12-25 00:00:00

# Modified on 2025-01-04 00:00:00

# Modified on 2025-01-04 00:00:00

# Modified on 2025-02-01 00:00:00

# Modified on 2025-02-15 00:00:00

# Modified on 2025-02-20 00:00:00

# Modified on 2025-02-21 00:00:00

# Modified on 2025-02-21 00:00:00

# Modified on 2025-02-22 00:00:00

# Modified on 2025-02-23 00:00:00

# Modified on 2025-02-24 00:00:00

# Modified on 2025-02-24 00:00:00

# Modified on 2025-02-24 00:00:00
