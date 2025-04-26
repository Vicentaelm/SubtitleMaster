import logging
import requests
import os
import time
from config import Config

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Cache for server information to reduce API calls
server_cache = {
    'server': None,
    'timestamp': 0,
    'ttl': 300  # Cache TTL in seconds (5 minutes)
}

def get_gofile_server():
    """
    Get the best Gofile server for uploads.
    Caches the result to avoid frequent API calls.
    """
    # Check if we have a cached server that's still valid
    current_time = time.time()
    if (server_cache['server'] and 
        current_time - server_cache['timestamp'] < server_cache['ttl']):
        logger.debug(f"Using cached Gofile server: {server_cache['server']}")
        return server_cache['server']
    
    try:
        # Make the API request to get the best server
        response = requests.get(f"{Config.GOFILE_API_URL}/getServer")
        response.raise_for_status()
        
        data = response.json()
        
        if data['status'] != 'ok':
            logger.error(f"Gofile API returned error: {data}")
            raise Exception(f"Gofile API error: {data.get('message', 'Unknown error')}")
        
        # Cache the server information
        server_cache['server'] = data['data']['server']
        server_cache['timestamp'] = current_time
        
        logger.info(f"Got Gofile server: {server_cache['server']}")
        return server_cache['server']
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Gofile API: {str(e)}")
        raise Exception(f"Gofile server request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unknown error getting Gofile server: {str(e)}")
        raise Exception(f"Failed to get Gofile server: {str(e)}")

def upload_to_gofile(file_path, filename=None):
    """
    Upload a file to Gofile and return the download link
    
    Args:
        file_path (str): Path to file to upload
        filename (str, optional): Override filename
        
    Returns:
        dict: Contains fileId and downloadPage
    """
    try:
        # Get the best server for upload
        server = get_gofile_server()
        logger.info(f"Uploading to Gofile server: {server}")
        
        # If no filename provided, use the original filename
        if not filename:
            filename = os.path.basename(file_path)
        
        # Prepare the file for upload
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f)}
            
            # Make the upload request
            logger.info(f"Uploading file {filename} to Gofile")
            upload_url = f"https://{server}.gofile.io/uploadFile"
            response = requests.post(upload_url, files=files)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] != 'ok':
                logger.error(f"Gofile upload API returned error: {data}")
                raise Exception(f"Gofile upload error: {data.get('message', 'Unknown error')}")
            
            # Return file info
            file_info = {
                'fileId': data['data']['fileId'],
                'fileName': data['data']['fileName'],
                'downloadPage': data['data']['downloadPage']
            }
            
            logger.info(f"File uploaded successfully: {file_info['fileId']}")
            return file_info
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Gofile API during upload: {str(e)}")
        raise Exception(f"Gofile upload request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unknown error during Gofile upload: {str(e)}")
        raise Exception(f"Failed to upload to Gofile: {str(e)}")

def get_gofile_content(file_id):
    """
    Get content information for a Gofile file
    
    Args:
        file_id (str): The Gofile file ID
        
    Returns:
        dict: File content information
    """
    try:
        # Make the API request to get content info
        content_url = f"{Config.GOFILE_API_URL}/getContent"
        response = requests.get(content_url, params={'contentId': file_id})
        response.raise_for_status()
        
        data = response.json()
        
        if data['status'] != 'ok':
            logger.error(f"Gofile content API returned error: {data}")
            raise Exception(f"Gofile content error: {data.get('message', 'Unknown error')}")
        
        return data['data']
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Gofile API for content: {str(e)}")
        raise Exception(f"Gofile content request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unknown error getting Gofile content: {str(e)}")
        raise Exception(f"Failed to get Gofile content: {str(e)}")

def get_direct_download_url(file_id):
    """
    Get direct download URL for a Gofile file ID
    
    Args:
        file_id (str): The Gofile file ID
        
    Returns:
        str: Direct download URL
    """
    try:
        # Get content info
        content_info = get_gofile_content(file_id)
        
        # Extract file information
        contents = content_info.get('contents', {})
        
        if not contents:
            raise Exception(f"No content found for file ID: {file_id}")
        
        # Get the first file in the contents (assuming single file upload)
        file_key = next(iter(contents))
        file_info = contents[file_key]
        
        # Return the direct link
        return file_info.get('link')
        
    except Exception as e:
        logger.error(f"Error getting direct download URL: {str(e)}")
        raise Exception(f"Failed to get direct download URL: {str(e)}")
