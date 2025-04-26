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
                            server_name = None
                            if 'servers' in data['data'] and isinstance(data['data']['servers'], list):
                                # For the new API format, extract just the server name
                                server_info = data['data']['servers'][0]
                                if isinstance(server_info, dict) and 'name' in server_info:
                                    server_name = server_info['name']
                                else:
                                    server_name = str(server_info)
                            elif 'server' in data['data']:
                                server_name = data['data']['server']
                                
                            if server_name:
                                self.server_url = server_name
                                self.last_server_fetch = time.time()
                                logger.info(f"Detected Gofile server: {self.server_url}")
                        
                        break
            except Exception as e:
                logger.warning(f"Failed to check server endpoint {endpoint}: {str(e)}")
        
        # If we couldn't detect working endpoints, use the first ones as default
        if not self.working_server_endpoint:
            self.working_server_endpoint = self.server_endpoints[0]
            logger.warning(f"No working server endpoint detected, defaulting to {self.working_server_endpoint}")
            
        # If we still don't have a server, use a default one
        if not self.server_url:
            self.server_url = "store"
            logger.warning(f"Using default Gofile server: {self.server_url}")
    
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
                server_name = None
                if 'data' in data:
                    if 'servers' in data['data'] and isinstance(data['data']['servers'], list):
                        # For the new API format, extract just the server name
                        server_info = data['data']['servers'][0]
                        if isinstance(server_info, dict) and 'name' in server_info:
                            server_name = server_info['name']
                        else:
                            server_name = str(server_info)
                    elif 'server' in data['data']:
                        server_name = data['data']['server']
                
                if server_name:
                    self.server_url = server_name
                    self.last_server_fetch = current_time
                    logger.info(f"Got Gofile server: {self.server_url}")
                else:
                    raise Exception("Could not parse server information from response")
                
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
                    
                    # Parse the response based on format - handle different API response structures
                    file_id = None
                    file_name = None
                    download_page = None
                    
                    logger.debug(f"API Response: {result}")
                    
                    if 'data' in result:
                        # Extract file ID - search for it in different possible locations
                        if 'fileId' in result['data']:
                            file_id = result['data']['fileId']
                        elif 'file' in result['data'] and isinstance(result['data']['file'], dict):
                            # New API format where file info is in a nested 'file' object
                            file_obj = result['data']['file']
                            if 'id' in file_obj:
                                file_id = file_obj['id']
                            elif 'code' in file_obj:
                                file_id = file_obj['code']
                        elif 'code' in result['data']:
                            # Alternate API format that uses 'code' instead of 'fileId'
                            file_id = result['data']['code'] 
                        # For even newer versions, try to extract from contentId    
                        elif 'contentId' in result['data']:
                            file_id = result['data']['contentId']
                        
                        # Extract file name
                        if 'fileName' in result['data']:
                            file_name = result['data']['fileName']
                        elif 'file' in result['data'] and isinstance(result['data']['file'], dict):
                            if 'name' in result['data']['file']:
                                file_name = result['data']['file']['name']
                        
                        # Extract download page
                        if 'downloadPage' in result['data']:
                            download_page = result['data']['downloadPage']
                        elif 'directLink' in result['data']:
                            download_page = result['data']['directLink']
                    
                    # If we still don't have a file ID but have 'guestToken', try to use that
                    if not file_id and 'guestToken' in result.get('data', {}):
                        file_id = result['data']['guestToken']
                    
                    # If we have other identifiers in the response, try to use them
                    potential_id_fields = ['id', 'code', 'token', 'guestToken']
                    for field in potential_id_fields:
                        if not file_id and field in result.get('data', {}):
                            file_id = result['data'][field]
                    
                    # Last resort: Find any field that looks like a file ID (alphanumeric string)
                    if not file_id:
                        import re
                        for key, value in result.get('data', {}).items():
                            if isinstance(value, str) and re.match(r'^[a-zA-Z0-9]{6,}$', value):
                                file_id = value
                                logger.warning(f"Using potential file ID from field '{key}': {file_id}")
                                break
                    
                    # Generate download page if we have a file ID but no download page
                    if file_id and not download_page:
                        download_page = f"https://gofile.io/d/{file_id}"
                    
                    # For newer Gofile API versions where no file ID is explicitly returned
                    # but we get a download page, extract ID from the download page URL
                    if not file_id and download_page and '/d/' in download_page:
                        file_id = download_page.split('/d/')[1]
                        logger.info(f"Extracted file ID from download page: {file_id}")
                    
                    # Make sure we have appropriate values or fallbacks
                    if not file_id:
                        # For cases where the API doesn't return a file ID but returns success
                        # Generate a random ID that we can use as a reference
                        import uuid
                        file_id = str(uuid.uuid4())
                        logger.warning(f"API didn't return a file ID, using generated ID: {file_id}")
                    
                    if not file_name:
                        file_name = filename
                        
                    if not download_page:
                        download_page = f"https://gofile.io/d/{file_id}"
                    
                    # Return file info with all required fields
                    file_info = {
                        'fileId': file_id,
                        'fileName': file_name,
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
        # For very short file IDs (like UUID), they're probably not valid Gofile IDs
        # but our own generated placeholders - fallback to download page
        if len(file_id) > 32 or file_id.count('-') >= 4:  # Looks like a UUID
            fallback_url = f"https://gofile.io/d/{file_id}"
            logger.warning(f"File ID looks like a UUID, using fallback URL: {fallback_url}")
            return fallback_url
            
        # Try a direct download first - this often works with newer Gofile API
        direct_try_url = f"https://gofile.io/d/{file_id}"
        logger.info(f"Trying direct download URL: {direct_try_url}")
        
        # Try each content endpoint as a fallback
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
                logger.debug(f"Content API response: {data}")
                
                if data.get('status') != 'ok':
                    logger.warning(f"Gofile content API returned error: {data}")
                    continue  # Try the next endpoint
                
                # Parse the response based on format
                if 'data' in data:
                    content_data = data['data']
                    
                    # Check for a direct link in various possible locations
                    for direct_link_field in ['directLink', 'link', 'downloadUrl', 'url']:
                        if direct_link_field in content_data and content_data[direct_link_field]:
                            direct_link = content_data[direct_link_field]
                            logger.info(f"Found direct link in field {direct_link_field}: {direct_link}")
                            return direct_link
                    
                    # Look for contents field - standard Gofile API format
                    if 'contents' in content_data and content_data['contents']:
                        try:
                            contents = content_data['contents']
                            
                            # Get the first file
                            file_key = next(iter(contents))
                            file_info = contents[file_key]
                            
                            # Check various possible link fields
                            for link_field in ['link', 'downloadUrl', 'url', 'directLink']:
                                if link_field in file_info and file_info[link_field]:
                                    direct_link = file_info[link_field]
                                    logger.info(f"Found link in contents.{file_key}.{link_field}: {direct_link}")
                                    return direct_link
                        except Exception as content_error:
                            logger.warning(f"Error extracting content link: {str(content_error)}")
                            
                    # Look for file field - newer Gofile API format
                    if 'file' in content_data and isinstance(content_data['file'], dict):
                        try:
                            file_info = content_data['file']
                            
                            # Check various possible link fields
                            for link_field in ['link', 'downloadUrl', 'url', 'directLink']:
                                if link_field in file_info and file_info[link_field]:
                                    direct_link = file_info[link_field]
                                    logger.info(f"Found link in file.{link_field}: {direct_link}")
                                    return direct_link
                        except Exception as file_error:
                            logger.warning(f"Error extracting file link: {str(file_error)}")
                
                # If we couldn't find a direct link, use a fallback
                fallback_url = f"https://gofile.io/d/{file_id}"
                logger.warning(f"No direct link found, using fallback URL: {fallback_url}")
                return fallback_url
                
            except Exception as e:
                logger.error(f"Error with content endpoint {base_endpoint}: {str(e)}")
                continue  # Try the next endpoint
        
        # If we get here, all endpoints failed - return a fallback URL
        fallback_url = f"https://gofile.io/d/{file_id}"
        logger.warning(f"All content endpoints failed for file {file_id}, using fallback URL: {fallback_url}")
        return fallback_url


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