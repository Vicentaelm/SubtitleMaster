/**
 * Video Preview Component
 * Handles displaying the video with subtitles
 */

// Initialize the video preview
function initVideoPreview(videoUrl, subtitleUrl) {
    const videoContainer = document.getElementById('video-container');
    const previewVideo = document.getElementById('preview-video');
    const videoSource = document.getElementById('video-source');
    const subtitleTrack = document.getElementById('subtitle-track');
    
    if (!videoContainer || !previewVideo || !videoSource || !subtitleTrack) {
        console.error('Video preview elements not found');
        return;
    }
    
    // Show loading message
    videoContainer.insertAdjacentHTML('afterend', `
        <div id="video-loading" class="alert alert-info mt-3">
            <div class="d-flex align-items-center">
                <div class="spinner-border spinner-border-sm me-2" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div>Loading video and subtitle files... This may take a moment.</div>
            </div>
        </div>
    `);
    
    // Process the video and subtitle URLs
    Promise.all([
        extractDirectDownloadLink(videoUrl),
        extractDirectDownloadLink(subtitleUrl)
    ])
    .then(([videoDirectUrl, subtitleDirectUrl]) => {
        // Set up the video with the subtitle
        setupVideo(videoDirectUrl, subtitleDirectUrl);
    })
    .catch(error => {
        console.error('Error loading video preview:', error);
        showVideoError(`Error loading video preview: ${error.message}`);
    });
    
    // Set up the video player with sources
    function setupVideo(videoSrc, subtitleSrc) {
        if (!videoSrc || !subtitleSrc) {
            showVideoError('Could not load video or subtitle files.');
            return;
        }
        
        // Set video source
        videoSource.src = videoSrc;
        
        // Convert VTT to SRT format if needed
        fetch(subtitleSrc)
            .then(response => response.text())
            .then(content => {
                // Create a Blob URL for the subtitle track
                let trackContent = content;
                if (subtitleSrc.includes('.srt')) {
                    // Convert SRT to VTT for HTML5 video
                    trackContent = convertVttToSrt(content);
                }
                
                const trackBlob = new Blob([trackContent], { type: 'text/vtt' });
                const trackUrl = URL.createObjectURL(trackBlob);
                
                // Set subtitle track
                subtitleTrack.src = trackUrl;
                subtitleTrack.mode = 'showing';
                
                // Reload video after sources are set
                previewVideo.load();
                
                // Remove loading message
                const loadingMsg = document.getElementById('video-loading');
                if (loadingMsg) loadingMsg.remove();
            })
            .catch(error => {
                console.error('Error loading subtitles:', error);
                showVideoError(`Error loading subtitles: ${error.message}`);
            });
    }
    
    // Show error message
    function showVideoError(message) {
        const loadingMsg = document.getElementById('video-loading');
        if (loadingMsg) {
            loadingMsg.className = 'alert alert-danger mt-3';
            loadingMsg.innerHTML = `<i class="bi bi-exclamation-triangle"></i> ${message}`;
        } else {
            videoContainer.insertAdjacentHTML('afterend', `
                <div class="alert alert-danger mt-3">
                    <i class="bi bi-exclamation-triangle"></i> ${message}
                </div>
            `);
        }
    }
}

// Extract direct download link from Gofile URL
async function extractDirectDownloadLink(gofileUrl) {
    try {
        // Check if it's a Gofile URL
        if (!gofileUrl || !gofileUrl.includes('gofile.io')) {
            return gofileUrl; // Return as is if not a Gofile URL
        }
        
        // Extract the file ID from the URL
        const fileId = gofileUrl.split('/').pop();
        
        // Request the direct link through our API
        const response = await fetch(`/api/direct-link?id=${fileId}`);
        if (!response.ok) {
            throw new Error(`Failed to get direct link: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        if (data.status !== 'success' || !data.url) {
            throw new Error(data.message || 'Could not retrieve direct download link.');
        }
        
        return data.url;
    } catch (error) {
        console.error('Error getting direct download link:', error);
        return gofileUrl; // Fall back to original URL on error
    }
}

// Convert VTT format to SRT format
function convertVttToSrt(vttContent) {
    // If it already looks like a VTT file, return it as is
    if (vttContent.trim().startsWith('WEBVTT')) {
        return vttContent;
    }
    
    // Convert SRT to VTT
    let vtt = 'WEBVTT\n\n';
    
    // Split content into subtitle blocks
    const blocks = vttContent.split(/\n\s*\n/);
    
    blocks.forEach(block => {
        const lines = block.trim().split('\n');
        if (lines.length < 3) return; // Skip invalid blocks
        
        // Replace comma with dot in timestamps for VTT format
        const timelineMatch = lines[1].match(/(\d{2}:\d{2}:\d{2}),(\d{3}) --> (\d{2}:\d{2}:\d{2}),(\d{3})/);
        if (!timelineMatch) return; // Skip invalid timestamps
        
        const timeline = lines[1].replace(/,/g, '.');
        const text = lines.slice(2).join('\n');
        
        // Add block to VTT content
        vtt += `${lines[0]}\n${timeline}\n${text}\n\n`;
    });
    
    return vtt;
}

// Upload edited subtitles to Gofile
async function uploadSubtitlesToGofile(content, filename, format = 'srt') {
    try {
        // Create a blob from the content
        const blob = new Blob([content], { type: 'text/plain' });
        
        // Create a FormData object
        const formData = new FormData();
        formData.append('file', blob, filename);
        
        // Get the best Gofile server
        const serverResponse = await fetch('/api/server');
        const serverData = await serverResponse.json();
        
        if (serverData.status !== 'success' || !serverData.server) {
            throw new Error('Could not get Gofile server');
        }
        
        // Upload to Gofile
        const uploadUrl = `https://${serverData.server}.gofile.io/uploadFile`;
        const uploadResponse = await fetch(uploadUrl, {
            method: 'POST',
            body: formData
        });
        
        const uploadData = await uploadResponse.json();
        
        if (uploadData.status !== 'ok' || !uploadData.data) {
            throw new Error('Upload failed');
        }
        
        return {
            fileId: uploadData.data.fileId,
            fileName: uploadData.data.fileName,
            downloadPage: uploadData.data.downloadPage
        };
    } catch (error) {
        console.error('Error uploading to Gofile:', error);
        throw error;
    }
}