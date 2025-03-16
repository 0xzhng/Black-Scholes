#!/usr/bin/env python3
"""
Main entry point for the Implied Volatility Surface Tracker application.
This script can start both the data collection server and the Streamlit UI.
"""

import os
import sys
import argparse
import subprocess
import time
import signal
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('iv_surface')

# Load environment variables
load_dotenv()

def start_server():
    """Start the data collection server"""
    from utils.server import start_server
    logger.info("Starting data collection server...")
    return start_server()

def start_streamlit():
    """Start the Streamlit UI"""
    logger.info("Starting Streamlit UI...")
    streamlit_process = subprocess.Popen(
        ["streamlit", "run", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return streamlit_process

def handle_exit(signum, frame):
    """Handle exit signals gracefully"""
    logger.info("Received exit signal. Shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Implied Volatility Surface Tracker")
    parser.add_argument(
        "--server-only", 
        action="store_true", 
        help="Start only the data collection server without the UI"
    )
    parser.add_argument(
        "--ui-only", 
        action="store_true", 
        help="Start only the Streamlit UI without the server"
    )
    
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    server_components = None
    streamlit_process = None
    
    try:
        # Start components based on arguments
        if args.server_only:
            server_components = start_server()
        elif args.ui_only:
            streamlit_process = start_streamlit()
        else:
            # Start both by default
            server_components = start_server()
            time.sleep(2)  # Give the server a moment to start
            streamlit_process = start_streamlit()
        
        # Keep the main process running
        while True:
            time.sleep(1)
            
            # Check if streamlit process is still running
            if streamlit_process and streamlit_process.poll() is not None:
                logger.error("Streamlit process exited unexpectedly")
                break
                
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    except Exception as e:
        logger.error(f"Error in main process: {e}")
    finally:
        # Clean up
        if streamlit_process:
            logger.info("Stopping Streamlit UI...")
            streamlit_process.terminate()
            streamlit_process.wait(timeout=5)
        
        if server_components:
            logger.info("Stopping data collection server...")
            scheduler, stop_event, _ = server_components
            from utils.server import stop_server
            stop_server(scheduler, stop_event)
        
        logger.info("Application shutdown complete")

if __name__ == "__main__":
    main() 