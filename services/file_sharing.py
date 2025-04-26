"""
File Sharing Service Module

This module provides a pluggable interface for file sharing services.
It allows for easy switching between different providers (like Gofile, etc.)
and isolates the application from API changes in those services.
"""

import os
import logging
import importlib
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class FileSharingService(ABC):
    """Abstract base class for file sharing services."""
    
    @abstractmethod
    def upload_file(self, file_path: str, filename: Optional[str] = None) -> Dict[str, str]:
        """
        Upload a file to the sharing service.
        
        Args:
            file_path: Path to the file to upload
            filename: Optional override for the filename
            
        Returns:
            Dict with file info (fileId, fileName, downloadPage)
        """
        pass
    
    @abstractmethod
    def get_direct_download_url(self, file_id: str) -> str:
        """
        Get a direct download URL for a file.
        
        Args:
            file_id: ID of the file
            
        Returns:
            Direct download URL
        """
        pass


class GofileService(FileSharingService):
    """Implementation of FileSharingService for Gofile."""
    
    def __init__(self):
        """Initialize the Gofile service with API endpoints."""
        self.api_base_url = "https://api.gofile.io"
        self.server_url = None
        self.server_ttl = 300  # 5 minutes
        self.last_server_fetch = 0
        
        # Attempt different API endpoints for backward/forward compatibility
        self.server_endpoints = [
            "/servers",      # Current endpoint
            "/getServer",    # Old endpoint
        ]
        
        self.upload_endpoints = [
            "/contents/uploadfile",  # Current endpoint
            "/uploadFile",           # Old endpoint
        ]
        
        self.content_endpoints = [
            "/contents/{file_id}",   # Current endpoint
            "/getContent",           # Old endpoint
        ]
        
        # Detect working endpoints
        self._detect_working_endpoints()
    
    def _detect_working_endpoints(self):
        """Detect which API endpoints are currently working."""
        import time
        
        self.working_server_endpoint = None
        self.working_content_endpoint = None
        
        # Try each server endpoint
        for endpoint in self.server_endpoints:
            try:
                url = f"{self.api_base_url}{endpoint}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'ok':
                        self.working_server_endpoint = endpoint
                        logger.info(f"Using server endpoint: {endpoint}")
                        
                        # Get the server if response matches expected format
                        if 'data' in data:
                            if 'servers' in data['data'] and isinstance(data['data']['servers'], list):
                                self.server_url = data['data']['servers'][0]
                            elif 'server' in data['data']:
                                self.server_url = data['data']['server']
                        
                        self.last_server_fetch = time.time()
                        break
            except Exception as e:
                logger.warning(f"Failed to check server endpoint {endpoint}: {str(e)}")
        
        # If we couldn't detect working endpoints, use the first ones as default
        if not self.working_server_endpoint:
            self.working_server_endpoint = self.server_endpoints[0]
            logger.warning(f"No working server endpoint detected, defaulting to {self.working_server_endpoint}")
    
    def _get_server(self) -> str:
        """
        Get the best Gofile server for uploads.
        Caches the result to avoid frequent API calls.
        
        Returns:
            Server name
        """
        import time
        
        current_time = time.time()
        
        # Check if we need to refresh the server
        if not self.server_url or (current_time - self.last_server_fetch) > self.server_ttl:
            try:
                url = f"{self.api_base_url}{self.working_server_endpoint}"
                response = requests.get(url)
                response.raise_for_status()
                
                data = response.json()
                
                if data['status'] != 'ok':
                    logger.error(f"Gofile API returned error: {data}")
                    raise Exception(f"Gofile API error: {data.get('message', 'Unknown error')}")
                
                # Parse the server from the response based on format
                if 'data' in data:
                    if 'servers' in data['data'] and isinstance(data['data']['servers'], list):
                        self.server_url = data['data']['servers'][0]
                    elif 'server' in data['data']:
                        self.server_url = data['data']['server']
                
                self.last_server_fetch = current_time
                logger.info(f"Got Gofile server: {self.server_url}")
                
            except Exception as e:
                # If we can't get a server, try to redetect endpoints
                logger.error(f"Error getting Gofile server: {str(e)}")
                self._detect_working_endpoints()
                
                # If we still don't have a server, use a default one
                if not self.server_url:
                    self.server_url = "store"
                    logger.warning(f"Using default Gofile server: {self.server_url}")
        
        return self.server_url
    
    def upload_file(self, file_path: str, filename: Optional[str] = None) -> Dict[str, str]:
        """
        Upload a file to Gofile.
        
        Args:
            file_path: Path to file to upload
            filename: Optional override for filename
            
        Returns:
            Dict with file info (fileId, fileName, downloadPage)
        """
        # Get server for upload
        server = self._get_server()
        
        # If no filename provided, use the original filename
        if not filename:
            filename = os.path.basename(file_path)
        
        # Try each upload endpoint with the server
        for endpoint in self.upload_endpoints:
            try:
                # Prepare the file for upload
                with open(file_path, 'rb') as f:
                    files = {'file': (filename, f)}
                    
                    # For newer API
                    data = {"token": ""}
                    
                    # Construct upload URL
                    upload_url = f"https://{server}.gofile.io{endpoint}"
                    logger.info(f"Trying to upload to {upload_url}")
                    
                    # Make the request
                    response = requests.post(upload_url, files=files, data=data, timeout=120)
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    if result['status'] != 'ok':
                        logger.error(f"Gofile upload API returned error: {result}")
                        raise Exception(f"Gofile upload error: {result.get('message', 'Unknown error')}")
                    
                    # Parse the response based on format
                    file_id = None
                    file_name = None
                    download_page = None
                    
                    if 'data' in result:
                        if 'fileId' in result['data']:
                            file_id = result['data']['fileId']
                        if 'fileName' in result['data']:
                            file_name = result['data']['fileName']
                        if 'downloadPage' in result['data']:
                            download_page = result['data']['downloadPage']
                    
                    # If we didn't get a download page but have a file ID, construct it
                    if file_id and not download_page:
                        download_page = f"https://gofile.io/d/{file_id}"
                    
                    # Return file info
                    file_info = {
                        'fileId': file_id,
                        'fileName': file_name or filename,
                        'downloadPage': download_page
                    }
                    
                    logger.info(f"File uploaded successfully: {file_info['fileId']}")
                    return file_info
                    
            except Exception as e:
                logger.error(f"Error with upload endpoint {endpoint}: {str(e)}")
                continue  # Try the next endpoint
        
        # If we get here, all endpoints failed
        raise Exception("All Gofile upload endpoints failed")
    
    def get_direct_download_url(self, file_id: str) -> str:
        """
        Get direct download URL for a Gofile file ID.
        
        Args:
            file_id: The Gofile file ID
            
        Returns:
            Direct download URL
        """
        # Try each content endpoint
        for base_endpoint in self.content_endpoints:
            try:
                # Format the endpoint with the file ID if needed
                if '{file_id}' in base_endpoint:
                    endpoint = base_endpoint.format(file_id=file_id)
                    url = f"{self.api_base_url}{endpoint}"
                    params = {}
                else:
                    url = f"{self.api_base_url}{base_endpoint}"
                    params = {'contentId': file_id}
                
                logger.info(f"Trying to get file content from {url}")
                response = requests.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if data['status'] != 'ok':
                    logger.warning(f"Gofile content API returned error: {data}")
                    continue  # Try the next endpoint
                
                # Parse the response based on format
                if 'data' in data:
                    content_data = data['data']
                    
                    # Look for contents field
                    if 'contents' in content_data and content_data['contents']:
                        contents = content_data['contents']
                        
                        # Get the first file
                        file_key = next(iter(contents))
                        file_info = contents[file_key]
                        
                        if 'link' in file_info:
                            return file_info['link']
                    
                    # Look for direct link field
                    if 'directLink' in content_data:
                        return content_data['directLink']
                
                # If we couldn't find a direct link, return a fallback
                return f"https://gofile.io/d/{file_id}"
                
            except Exception as e:
                logger.error(f"Error with content endpoint {base_endpoint}: {str(e)}")
                continue  # Try the next endpoint
        
        # If we get here, all endpoints failed - return a fallback URL
        logger.warning(f"All content endpoints failed for file {file_id}, using fallback URL")
        return f"https://gofile.io/d/{file_id}"


# Factory function to get the appropriate file sharing service
def get_file_sharing_service(provider: str = 'gofile') -> FileSharingService:
    """
    Factory function to create a file sharing service instance.
    
    Args:
        provider: The service provider to use ('gofile', etc.)
        
    Returns:
        FileSharingService instance
    """
    if provider.lower() == 'gofile':
        return GofileService()
    else:
        raise ValueError(f"Unsupported file sharing provider: {provider}")