/**
 * Subtitle Editor Component
 * Handles loading, parsing, editing and saving subtitle files
 */

// Global variables to store subtitle data
let subtitles = [];
let currentFormat = 'srt';
let currentFilename = 'subtitles.srt';
let subtitleContainer;

// Initialize the subtitle editor with a subtitle URL
function initSubtitleEditor(subtitleUrl, format = 'srt', filename = 'subtitles.srt') {
    currentFormat = format;
    currentFilename = filename;
    subtitleContainer = document.getElementById('subtitle-editor-container');
    
    if (!subtitleUrl || !subtitleContainer) {
        showAlert('Unable to initialize subtitle editor', 'danger');
        return;
    }
    
    // Fetch and parse subtitles
    fetchSubtitles(subtitleUrl).then(content => {
        if (content) {
            subtitles = parseSubtitles(content, format);
            renderSubtitles();
        } else {
            subtitleContainer.innerHTML = `
                <div class="alert alert-danger">
                    <h5>Error Loading Subtitles</h5>
                    <p>Unable to load subtitles from ${subtitleUrl}</p>
                </div>
            `;
        }
    }).catch(error => {
        console.error('Error loading subtitles:', error);
        subtitleContainer.innerHTML = `
            <div class="alert alert-danger">
                <h5>Error Loading Subtitles</h5>
                <p>${error.message}</p>
            </div>
        `;
    });
    
    // Add event listener for adding new subtitles
    document.getElementById('add-subtitle').addEventListener('click', () => {
        // Create a new subtitle at the end with default values
        const lastSubtitle = subtitles.length > 0 ? subtitles[subtitles.length - 1] : null;
        const startTime = lastSubtitle ? lastSubtitle.endTime + 1 : 0;
        const endTime = startTime + 3;
        
        subtitles.push({
            index: subtitles.length + 1,
            startTime,
            endTime,
            text: 'New subtitle'
        });
        
        renderSubtitles();
        
        // Scroll to the newly added subtitle
        const newSubtitleElement = document.getElementById(`subtitle-${subtitles.length - 1}`);
        if (newSubtitleElement) {
            newSubtitleElement.scrollIntoView({ behavior: 'smooth' });
            const textArea = newSubtitleElement.querySelector('textarea');
            if (textArea) {
                textArea.focus();
                textArea.select();
            }
        }
    });
}

// Fetch subtitle content from URL
async function fetchSubtitles(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to fetch subtitles: ${response.status} ${response.statusText}`);
        }
        return await response.text();
    } catch (error) {
        console.error('Error fetching subtitles:', error);
        throw error;
    }
}

// Parse subtitle content based on format
function parseSubtitles(content, format) {
    const parsedSubtitles = [];
    
    if (format === 'srt') {
        // Parse SRT format
        const blocks = content.trim().split(/\n\s*\n/);
        
        blocks.forEach(block => {
            const lines = block.trim().split('\n');
            if (lines.length < 3) return; // Invalid block
            
            const index = parseInt(lines[0], 10);
            const timeMatch = lines[1].match(/(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})/);
            
            if (!timeMatch) return; // Invalid time format
            
            const startTime = parseTimestamp(timeMatch[1], 'srt');
            const endTime = parseTimestamp(timeMatch[2], 'srt');
            const text = lines.slice(2).join('\n');
            
            parsedSubtitles.push({ index, startTime, endTime, text });
        });
    } else if (format === 'vtt') {
        // Parse VTT format
        const lines = content.trim().split('\n');
        let index = 0;
        let currentSubtitle = null;
        let textLines = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            if (line === 'WEBVTT') continue;
            if (line === '' && currentSubtitle) {
                // End of a subtitle block
                currentSubtitle.text = textLines.join('\n');
                parsedSubtitles.push(currentSubtitle);
                currentSubtitle = null;
                textLines = [];
                continue;
            }
            
            const timeMatch = line.match(/(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})/);
            if (timeMatch) {
                // Start of a new subtitle block
                index++;
                currentSubtitle = {
                    index,
                    startTime: parseTimestamp(timeMatch[1], 'vtt'),
                    endTime: parseTimestamp(timeMatch[2], 'vtt'),
                    text: ''
                };
                textLines = [];
            } else if (currentSubtitle && line !== '') {
                // Text content
                textLines.push(line);
            }
        }
        
        // Add the last subtitle block if it exists
        if (currentSubtitle) {
            currentSubtitle.text = textLines.join('\n');
            parsedSubtitles.push(currentSubtitle);
        }
    } else if (format === 'txt') {
        // Parse simple text (no timing info)
        const lines = content.trim().split('\n');
        let index = 0;
        let startTime = 0;
        
        lines.forEach(line => {
            if (line.trim() === '') return;
            
            index++;
            const endTime = startTime + 3; // Assume 3 seconds per line
            
            parsedSubtitles.push({
                index,
                startTime,
                endTime,
                text: line.trim()
            });
            
            startTime = endTime + 0.1; // Small gap between subtitles
        });
    }
    
    return parsedSubtitles;
}

// Render subtitles in the editor
function renderSubtitles() {
    if (!subtitleContainer) return;
    
    // Create HTML for all subtitles
    const html = subtitles.map((subtitle, idx) => {
        return `
            <div class="subtitle-item p-3" id="subtitle-${idx}">
                <div class="d-flex justify-content-between mb-2">
                    <span class="badge bg-secondary">#${subtitle.index}</span>
                    <button type="button" class="btn btn-sm btn-outline-danger delete-subtitle" data-index="${idx}">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
                <div class="row mb-2">
                    <div class="col-md-6 mb-2 mb-md-0">
                        <div class="input-group">
                            <span class="input-group-text">Start</span>
                            <input type="text" class="form-control time-input subtitle-start" data-index="${idx}"
                                value="${formatTimestamp(subtitle.startTime, currentFormat)}" 
                                placeholder="00:00:00,000">
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="input-group">
                            <span class="input-group-text">End</span>
                            <input type="text" class="form-control time-input subtitle-end" data-index="${idx}"
                                value="${formatTimestamp(subtitle.endTime, currentFormat)}" 
                                placeholder="00:00:03,000">
                        </div>
                    </div>
                </div>
                <div class="form-group">
                    <textarea class="form-control subtitle-text" data-index="${idx}" rows="2">${subtitle.text}</textarea>
                </div>
            </div>
        `;
    }).join('');
    
    // Update the container
    subtitleContainer.innerHTML = html || `
        <div class="alert alert-warning">
            <p>No subtitles found. Click "Add" to create your first subtitle.</p>
        </div>
    `;
    
    // Add event listeners for delete buttons
    const deleteButtons = document.querySelectorAll('.delete-subtitle');
    deleteButtons.forEach(button => {
        button.addEventListener('click', () => {
            const index = parseInt(button.getAttribute('data-index'), 10);
            deleteSubtitle(index);
        });
    });
    
    // Add event listeners for time inputs
    const timeInputs = document.querySelectorAll('.time-input');
    timeInputs.forEach(input => {
        input.addEventListener('change', () => {
            const index = parseInt(input.getAttribute('data-index'), 10);
            const field = input.classList.contains('subtitle-start') ? 'startTime' : 'endTime';
            const value = parseTimestamp(input.value, currentFormat);
            updateSubtitleTime(index, field, value);
        });
    });
    
    // Add event listeners for text areas
    const textAreas = document.querySelectorAll('.subtitle-text');
    textAreas.forEach(textarea => {
        textarea.addEventListener('change', () => {
            const index = parseInt(textarea.getAttribute('data-index'), 10);
            updateSubtitleText(index, textarea.value);
        });
    });
}

// Delete a subtitle
function deleteSubtitle(index) {
    if (index < 0 || index >= subtitles.length) return;
    
    // Ask for confirmation
    if (confirm('Are you sure you want to delete this subtitle?')) {
        subtitles.splice(index, 1);
        
        // Update indices
        subtitles.forEach((sub, idx) => {
            sub.index = idx + 1;
        });
        
        renderSubtitles();
        showAlert('Subtitle deleted', 'info');
    }
}

// Update subtitle time
function updateSubtitleTime(index, field, value) {
    if (index < 0 || index >= subtitles.length) return;
    
    const subtitle = subtitles[index];
    
    // Validate value
    if (isNaN(value) || value < 0) {
        showAlert('Invalid time format. Please use HH:MM:SS,mmm format.', 'warning');
        renderSubtitles(); // Reset to previous value
        return;
    }
    
    // Update the time field
    subtitle[field] = value;
    
    // Ensure startTime is before endTime
    if (subtitle.startTime >= subtitle.endTime) {
        if (field === 'startTime') {
            subtitle.endTime = subtitle.startTime + 0.5;
        } else {
            subtitle.startTime = subtitle.endTime - 0.5;
        }
        renderSubtitles(); // Update both fields
    }
}

// Update subtitle text
function updateSubtitleText(index, text) {
    if (index < 0 || index >= subtitles.length) return;
    subtitles[index].text = text;
}

// Save subtitle changes
function saveSubtitleChanges() {
    // Generate subtitle content
    const content = generateSubtitleContent();
    
    // Download as file
    downloadTextAsFile(content, currentFilename);
    showAlert('Subtitles saved successfully', 'success');
}

// Generate subtitle content based on format
function generateSubtitleContent() {
    let content = '';
    
    if (currentFormat === 'srt') {
        // Generate SRT format
        content = subtitles.map(sub => {
            return `${sub.index}\n${formatTimestamp(sub.startTime, 'srt')} --> ${formatTimestamp(sub.endTime, 'srt')}\n${sub.text}\n`;
        }).join('\n');
    } else if (currentFormat === 'vtt') {
        // Generate VTT format
        content = 'WEBVTT\n\n';
        content += subtitles.map(sub => {
            return `${sub.index}\n${formatTimestamp(sub.startTime, 'vtt')} --> ${formatTimestamp(sub.endTime, 'vtt')}\n${sub.text}\n`;
        }).join('\n');
    } else if (currentFormat === 'txt') {
        // Generate plain text format
        content = subtitles.map(sub => sub.text).join('\n\n');
    }
    
    return content;
}

// Update video subtitles in video preview
function updateVideoSubtitles() {
    // Generate VTT content for video preview
    const vttContent = 'WEBVTT\n\n' + subtitles.map(sub => {
        return `${formatTimestamp(sub.startTime, 'vtt')} --> ${formatTimestamp(sub.endTime, 'vtt')}\n${sub.text}\n`;
    }).join('\n');
    
    // Create a blob URL for the VTT content
    const blob = new Blob([vttContent], { type: 'text/vtt' });
    const url = URL.createObjectURL(blob);
    
    // Update the track element
    const track = document.getElementById('subtitle-track');
    if (track) {
        const oldUrl = track.src;
        track.src = url;
        
        // Cleanup old blob URL
        if (oldUrl && oldUrl.startsWith('blob:')) {
            URL.revokeObjectURL(oldUrl);
        }
        
        // Ensure subtitles are displayed
        track.mode = 'showing';
        
        // Switch to video preview tab
        document.getElementById('video-tab').click();
        
        showAlert('Subtitles updated in video preview', 'success');
    } else {
        showAlert('Video preview not available', 'warning');
    }
}