import os
import logging
import time
import threading
from utils.scheduler import start_scheduler, snapshot_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('volatility_server')

def start_server():
    """Start the volatility surface server in a separate thread"""
    logger.info("Starting Volatility Surface Server")
    
    # Start scheduler
    scheduler = start_scheduler()
    
    # Run initial job immediately
    snapshot_job()
    
    # Create a stop event
    stop_event = threading.Event()
    
    # Create server thread
    server_thread = threading.Thread(
        target=run_server,
        args=(scheduler, stop_event),
        daemon=True
    )
    server_thread.start()
    
    return scheduler, stop_event, server_thread

def run_server(scheduler, stop_event):
    """Run the server until the stop event is set"""
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        logger.info("Shutting down scheduler")
        scheduler.shutdown()
        logger.info("Server stopped")

def stop_server(scheduler, stop_event):
    """Stop the server gracefully"""
    logger.info("Stopping Volatility Surface Server")
    stop_event.set()
    scheduler.shutdown()
    logger.info("Server stopped")

if __name__ == "__main__":
    # This allows the module to be run directly for testing
    scheduler, stop_event, _ = start_server()
    
    try:
        # Keep the script running when executed directly
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        stop_server(scheduler, stop_event) 
# Modified on 2024-12-03 00:00:00

# Modified on 2024-12-05 00:00:00
