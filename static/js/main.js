/**
 * Main JavaScript functions for Whisper Subtitler
 */

// Format seconds to HH:MM:SS,mmm format for SRT or HH:MM:SS.mmm for VTT
function formatTimestamp(seconds, format = 'srt') {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    const separator = format === 'vtt' ? '.' : ',';
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${secs.toFixed(3).padStart(6, '0')}`.replace('.', separator);
}

// Parse timestamp string like "00:01:23,456" or "00:01:23.456" to seconds
function parseTimestamp(timestamp, format = 'srt') {
    // Remove any non-numeric characters except for : and . or ,
    const separator = format === 'vtt' ? '\\.' : ',';
    const regex = new RegExp(`^(\\d+):(\\d+):(\\d+)${separator}(\\d+)$`);
    const matches = timestamp.match(regex);
    
    if (matches) {
        const hours = parseInt(matches[1], 10);
        const minutes = parseInt(matches[2], 10);
        const seconds = parseInt(matches[3], 10);
        const milliseconds = parseInt(matches[4], 10) / 1000;
        
        return hours * 3600 + minutes * 60 + seconds + milliseconds;
    }
    
    return 0;
}

// Show an alert message
function showAlert(message, type = 'success', container = document.body) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Append to container or at the top of the page
    if (container === document.body) {
        const mainContainer = document.querySelector('.container');
        if (mainContainer) {
            mainContainer.prepend(alertDiv);
        } else {
            document.body.prepend(alertDiv);
        }
    } else {
        container.prepend(alertDiv);
    }
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, 5000);
}

// Truncate text with ellipsis
function truncateText(text, maxLength = 30) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}

// Fetch and download a file from a URL
async function fetchAndDownloadFile(url, filename) {
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch file');
        
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Clean up
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
        
        return true;
    } catch (error) {
        console.error('Error downloading file:', error);
        showAlert(`Error downloading file: ${error.message}`, 'danger');
        return false;
    }
}

// Download text content as a file
function downloadTextAsFile(text, filename) {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}