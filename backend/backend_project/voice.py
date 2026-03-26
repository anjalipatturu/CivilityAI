"""
Voice and audio processing for Civility.ai
- Voice Upload: convert audio files to text using speech recognition
- Audio analysis support
"""

import os
import tempfile
import speech_recognition as sr
from pydub import AudioSegment


def convert_audio_to_text(audio_file_path):
    """
    Convert an audio file to text using Google's Speech Recognition.
    Supports: wav, mp3, ogg, flac, m4a, webm
    """
    recognizer = sr.Recognizer()
    temp_wav = None

    try:
        file_ext = os.path.splitext(audio_file_path)[1].lower()

        # Convert non-wav formats to wav
        if file_ext != '.wav':
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_wav_path = temp_wav.name
            temp_wav.close()

            try:
                audio = AudioSegment.from_file(audio_file_path)
                audio.export(temp_wav_path, format='wav')
                wav_path = temp_wav_path
            except Exception as e:
                return {
                    'success': False,
                    'text': '',
                    'error': f'Failed to convert audio format: {str(e)}',
                }
        else:
            wav_path = audio_file_path

        # Recognize speech
        with sr.AudioFile(wav_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio_data)
            return {
                'success': True,
                'text': text,
                'error': None,
            }
        except sr.UnknownValueError:
            return {
                'success': False,
                'text': '',
                'error': 'Could not understand the audio content',
            }
        except sr.RequestError as e:
            return {
                'success': False,
                'text': '',
                'error': f'Speech recognition service error: {str(e)}',
            }

    except Exception as e:
        return {
            'success': False,
            'text': '',
            'error': f'Audio processing error: {str(e)}',
        }
    finally:
        if temp_wav and os.path.exists(temp_wav.name):
            try:
                os.unlink(temp_wav.name)
            except OSError:
                pass


def save_uploaded_audio(uploaded_file):
    """Save an uploaded audio file to a temp location and return the path."""
    temp_dir = tempfile.mkdtemp(prefix='civility_audio_')
    file_path = os.path.join(temp_dir, uploaded_file.name)

    with open(file_path, 'wb+') as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)

    return file_path


def cleanup_audio_file(file_path):
    """Clean up temporary audio files."""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            parent_dir = os.path.dirname(file_path)
            if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                os.rmdir(parent_dir)
    except OSError:
        pass
