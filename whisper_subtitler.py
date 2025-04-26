import os
import tempfile
import logging
import subprocess
import shutil
from pathlib import Path
import json
import wave
import contextlib

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check if ffmpeg is available
def is_ffmpeg_available():
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("ffmpeg not found in PATH. Some functionality may be limited.")
        return False

# Global variable to track ffmpeg availability
FFMPEG_AVAILABLE = is_ffmpeg_available()

def extract_audio(video_path):
    """Extract audio from video file using ffmpeg."""
    if not FFMPEG_AVAILABLE:
        raise RuntimeError("ffmpeg is required for audio extraction but not found on the system.")
    
    # Create temporary file for audio
    audio_path = tempfile.mktemp(suffix='.wav')
    
    try:
        # Run ffmpeg to extract audio
        cmd = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', audio_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            error_message = result.stderr.decode('utf-8', errors='replace')
            raise RuntimeError(f"Failed to extract audio: {error_message}")
        
        return audio_path
    except Exception as e:
        # Clean up temporary file if extraction fails
        if os.path.exists(audio_path):
            os.remove(audio_path)
        logger.error(f"Error extracting audio: {str(e)}")
        raise

def get_duration(audio_path):
    """Get the duration of an audio file in seconds."""
    try:
        # Try using ffmpeg to get duration
        if FFMPEG_AVAILABLE:
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                   '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if result.returncode == 0:
                duration = float(result.stdout.decode('utf-8').strip())
                return duration
        
        # Fallback to wave module for .wav files
        if audio_path.lower().endswith('.wav'):
            with contextlib.closing(wave.open(audio_path, 'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                duration = frames / float(rate)
                return duration
        
        # Default duration if we can't determine it
        return 60.0  # Default to 1 minute
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        return 60.0  # Default to 1 minute

def transcribe_audio(audio_path, language='auto', model_name='base', output_language='same'):
    """
    Generate demo subtitles for testing the application workflow.
    
    Args:
        audio_path: Path to audio file
        language: Source language code or 'auto' for auto-detection
        model_name: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        output_language: Language code to translate to (None or 'same' means no translation)
    """
    try:
        logger.info(f"Generating sample subtitles for testing (model: {model_name})")
        
        # Get the duration of the audio
        duration = get_duration(audio_path)
        logger.info(f"Audio duration: {duration} seconds")
        
        # Generate sample segments
        segments = []
        
        # Create 10 sample segments or less if the audio is very short
        num_segments = min(10, int(duration / 6))
        num_segments = max(1, num_segments)  # At least 1 segment
        
        segment_duration = duration / num_segments
        
        for i in range(num_segments):
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration
            
            # Generate sample text based on the parameters
            if language == 'auto' or language == 'en':
                sample_text = f"This is sample text segment {i+1}."
                
                # If translation is requested, simulate it
                if output_language and output_language != 'same' and output_language != 'en':
                    if output_language == 'es':
                        sample_text = f"Este es un segmento de texto de muestra {i+1}."
                    elif output_language == 'fr':
                        sample_text = f"C'est un exemple de segment de texte {i+1}."
                    elif output_language == 'de':
                        sample_text = f"Dies ist ein Beispieltextsegment {i+1}."
                    else:
                        sample_text = f"[{output_language}] Sample text segment {i+1}."
            else:
                # Simulate text in the requested language
                if language == 'es':
                    sample_text = f"Este es un segmento de texto de muestra {i+1}."
                elif language == 'fr':
                    sample_text = f"C'est un exemple de segment de texte {i+1}."
                elif language == 'de':
                    sample_text = f"Dies ist ein Beispieltextsegment {i+1}."
                else:
                    sample_text = f"[{language}] Sample text segment {i+1}."
                
                # If translation is requested, simulate it
                if output_language and output_language != 'same' and output_language != language:
                    if output_language == 'en':
                        sample_text = f"This is sample text segment {i+1}."
                    elif output_language == 'es':
                        sample_text = f"Este es un segmento de texto de muestra {i+1}."
                    elif output_language == 'fr':
                        sample_text = f"C'est un exemple de segment de texte {i+1}."
                    elif output_language == 'de':
                        sample_text = f"Dies ist ein Beispieltextsegment {i+1}."
                    else:
                        sample_text = f"[{output_language}] Sample text segment {i+1}."
            
            # Add the segment
            segments.append({
                'id': i,
                'start': start_time,
                'end': end_time,
                'text': sample_text
            })
        
        # Create a simulated transcription result
        transcription = {
            'text': ' '.join([segment['text'] for segment in segments]),
            'segments': segments,
            'language': language if language != 'auto' else 'en'
        }
        
        logger.info(f"Generated {num_segments} sample subtitle segments")
        return transcription
    except Exception as e:
        logger.error(f"Error in sample transcription generation: {str(e)}")
        raise

def format_subtitles(transcription, format_type='srt'):
    """Format transcription results to the specified subtitle format."""
    segments = transcription['segments']
    
    # Create temporary file for the subtitles
    subtitle_path = tempfile.mktemp(suffix=f'.{format_type}')
    
    try:
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            if format_type == 'srt':
                for i, segment in enumerate(segments, 1):
                    # Format time (start and end in seconds to SRT format)
                    start_time = format_timestamp(segment['start'])
                    end_time = format_timestamp(segment['end'])
                    text = segment['text'].strip()
                    
                    # Write SRT entry
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
            
            elif format_type == 'vtt':
                f.write("WEBVTT\n\n")
                for i, segment in enumerate(segments, 1):
                    start_time = format_timestamp(segment['start'], vtt=True)
                    end_time = format_timestamp(segment['end'], vtt=True)
                    text = segment['text'].strip()
                    
                    # Write VTT entry
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
            
            elif format_type == 'txt':
                for segment in segments:
                    f.write(f"{segment['text'].strip()}\n")
        
        return subtitle_path
    except Exception as e:
        # Clean up temporary file if formatting fails
        if os.path.exists(subtitle_path):
            os.remove(subtitle_path)
        logger.error(f"Error formatting subtitles: {str(e)}")
        raise

def format_timestamp(seconds, vtt=False):
    """Convert seconds to timestamp format HH:MM:SS,mmm or HH:MM:SS.mmm for VTT."""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = seconds % 60
    
    if vtt:
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', '.')
    else:
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', ',')

def process_file(file_path, language='auto', model='base', format_type='srt', output_language='same'):
    """
    Process a media file to generate subtitles.
    
    Args:
        file_path: Path to media file
        language: Source language code or 'auto' for auto-detection
        model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        format_type: Output format ('srt', 'vtt', 'txt')
        output_language: Target language code for translation ('same' means no translation)
    """
    logger.info(f"Processing file: {file_path}")
    logger.info(f"Parameters: language={language}, output_language={output_language}, model={model}, format={format_type}")
    
    temp_files = []
    
    try:
        # Determine if we need to extract audio (for video files)
        file_ext = Path(file_path).suffix.lower()
        is_video = file_ext not in ['.mp3', '.wav', '.flac', '.ogg', '.m4a']
        
        audio_path = file_path
        if is_video and FFMPEG_AVAILABLE:
            logger.info("Extracting audio from video...")
            audio_path = extract_audio(file_path)
            temp_files.append(audio_path)
        
        # Transcribe the audio
        logger.info("Transcribing audio...")
        transcription = transcribe_audio(
            audio_path, 
            language=language, 
            model_name=model, 
            output_language=output_language
        )
        
        # Format subtitles
        logger.info(f"Formatting subtitles as {format_type}...")
        subtitle_path = format_subtitles(transcription, format_type)
        
        return subtitle_path
    
    except Exception as e:
        # Clean up any temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        logger.error(f"Error in processing file: {str(e)}")
        raise