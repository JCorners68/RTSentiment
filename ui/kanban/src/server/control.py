"""
Server Control Module

This module handles starting and stopping the CLI Kanban companion server.
It provides a Python interface to control the Node.js Express server.
"""

import os
import sys
import signal
import subprocess
import time
import json
import logging
import requests
from pathlib import Path
import atexit

# Setup logging
logger = logging.getLogger(__name__)

class ServerController:
    """Controls the CLI Kanban companion server process."""
    
    def __init__(self, server_dir=None, port=None, log_file=None):
        """
        Initialize the server controller.
        
        Args:
            server_dir (str, optional): Directory containing the server code.
                Defaults to '../../server' relative to this file.
            port (int, optional): Port to run the server on. Defaults to 3000.
            log_file (str, optional): Path to the server log file.
                Defaults to '../../logs/server.log' relative to this file.
        """
        # Determine paths
        current_dir = Path(__file__).resolve().parent
        self.server_dir = Path(server_dir) if server_dir else (current_dir / '..' / '..' / 'server').resolve()
        self.log_file = Path(log_file) if log_file else (current_dir / '..' / '..' / 'logs' / 'server.log').resolve()
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Server settings
        self.port = port or 3000
        self.process = None
        self.is_running = False
        
        # Register exit handler to ensure server is stopped when Python exits
        atexit.register(self.stop)
    
    def start(self, wait_for_ready=True, timeout=10):
        """
        Start the server.
        
        Args:
            wait_for_ready (bool, optional): Whether to wait for the server to be ready.
                Defaults to True.
            timeout (int, optional): Timeout in seconds when waiting for the server.
                Defaults to 10.
                
        Returns:
            bool: True if the server was started successfully, False otherwise.
        """
        if self.is_running:
            logger.info("Server is already running")
            return True
        
        logger.info(f"Starting server from {self.server_dir}")
        
        # Check if Node.js is installed
        try:
            subprocess.run(["node", "--version"], 
                           check=True, 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("Node.js is not installed or not in PATH")
            return False
        
        # Check if server files exist
        if not (self.server_dir / "index.js").exists():
            logger.error(f"Server entry point not found at {self.server_dir / 'index.js'}")
            return False
        
        try:
            # Open log file
            log_fd = open(self.log_file, 'a')
            
            # Set environment variables
            env = os.environ.copy()
            env["KANBAN_SERVER_PORT"] = str(self.port)
            
            # Start the server process
            self.process = subprocess.Popen(
                ["node", "index.js"],
                cwd=str(self.server_dir),
                stdout=log_fd,
                stderr=log_fd,
                env=env
            )
            
            if wait_for_ready:
                # Wait for the server to be ready
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        response = requests.get(f"http://localhost:{self.port}/health")
                        if response.status_code == 200:
                            logger.info(f"Server started successfully on port {self.port}")
                            self.is_running = True
                            return True
                    except requests.RequestException:
                        time.sleep(0.5)
                
                # If we got here, the server didn't start within the timeout
                logger.error(f"Server failed to start within {timeout} seconds")
                self.stop()
                return False
            else:
                # If we don't need to wait, consider the server started
                logger.info(f"Server process started with PID {self.process.pid}")
                self.is_running = True
                return True
                
        except Exception as e:
            logger.error(f"Error starting server: {str(e)}")
            if self.process:
                self.stop()
            return False
    
    def stop(self):
        """
        Stop the server.
        
        Returns:
            bool: True if the server was stopped successfully, False otherwise.
        """
        if not self.is_running or not self.process:
            logger.info("Server is not running")
            return True
        
        logger.info("Stopping server")
        try:
            # Try to terminate gracefully first
            self.process.terminate()
            
            # Wait for it to terminate
            for _ in range(5):  # Wait up to 5 seconds
                if self.process.poll() is not None:
                    logger.info("Server stopped successfully")
                    self.is_running = False
                    self.process = None
                    return True
                time.sleep(1)
            
            # If still running, forcefully kill
            if self.process.poll() is None:
                logger.warning("Server didn't terminate gracefully, killing process")
                self.process.kill()
                self.process.wait()
            
            self.is_running = False
            self.process = None
            return True
            
        except Exception as e:
            logger.error(f"Error stopping server: {str(e)}")
            return False
    
    def restart(self, wait_for_ready=True, timeout=10):
        """
        Restart the server.
        
        Args:
            wait_for_ready (bool, optional): Whether to wait for the server to be ready.
                Defaults to True.
            timeout (int, optional): Timeout in seconds when waiting for the server.
                Defaults to 10.
                
        Returns:
            bool: True if the server was restarted successfully, False otherwise.
        """
        logger.info("Restarting server")
        if self.is_running:
            if not self.stop():
                return False
        
        return self.start(wait_for_ready, timeout)
    
    def status(self):
        """
        Check the status of the server.
        
        Returns:
            dict: A dictionary with status information.
        """
        status_info = {
            "is_running": self.is_running,
            "port": self.port,
            "pid": self.process.pid if self.process else None,
            "server_dir": str(self.server_dir),
            "log_file": str(self.log_file)
        }
        
        # Check if server is responsive
        if self.is_running:
            try:
                response = requests.get(f"http://localhost:{self.port}/health", timeout=1)
                status_info["responsive"] = response.status_code == 200
                if response.status_code == 200:
                    status_info["health"] = response.json()
            except requests.RequestException:
                status_info["responsive"] = False
        
        return status_info
    
    def send_notification(self, task_id, updates):
        """
        Send a notification to the server about task updates.
        
        This is used to notify any active CLI sessions about changes.
        
        Args:
            task_id (str): The ID of the task that was updated.
            updates (dict): The updates that were applied to the task.
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise.
        """
        if not self.is_running:
            logger.warning("Cannot send notification: server is not running")
            return False
        
        try:
            response = requests.post(
                f"http://localhost:{self.port}/api/kanban/notifications",
                json={
                    "type": "task_update",
                    "task_id": task_id,
                    "updates": updates,
                    "timestamp": time.time()
                }
            )
            
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False


# Global server controller instance
_server_controller = None

def get_server_controller():
    """
    Get the global server controller instance.
    
    Returns:
        ServerController: The global server controller instance.
    """
    global _server_controller
    if _server_controller is None:
        _server_controller = ServerController()
    return _server_controller

def start_server():
    """
    Start the server using the global controller.
    
    Returns:
        bool: True if the server was started successfully, False otherwise.
    """
    return get_server_controller().start()

def stop_server():
    """
    Stop the server using the global controller.
    
    Returns:
        bool: True if the server was stopped successfully, False otherwise.
    """
    return get_server_controller().stop()

def restart_server():
    """
    Restart the server using the global controller.
    
    Returns:
        bool: True if the server was restarted successfully, False otherwise.
    """
    return get_server_controller().restart()

def get_server_status():
    """
    Get the status of the server using the global controller.
    
    Returns:
        dict: A dictionary with status information.
    """
    return get_server_controller().status()