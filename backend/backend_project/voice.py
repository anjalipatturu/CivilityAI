"""Voice and audio processing for Civility.ai.

This module supports:
- Voice Upload: convert audio files to text using speech recognition
- Audio analysis support

Note: The "speech_recognition" package currently depends on the
deprecated stdlib module "aifc", which was removed in Python 3.13.
To avoid import errors preventing Django from starting, we lazily
import speech_recognition inside the conversion function instead of
at module import time. If the environment does not provide
"speech_recognition" (or its dependencies), audio transcription
will gracefully fail while the rest of the API continues to work.
"""

import os
import tempfile


def convert_audio_to_text(audio_file_path):
    """
    Convert an audio file to text using Google's Speech Recognition.
    Supports: wav, mp3, ogg, flac, m4a, webm
    """
    # Work around removal of standard library modules in Python 3.13+
    # that older versions of SpeechRecognition import unconditionally.
    # We provide lightweight stubs so the library can be imported and
    # used for non-AIFF formats.
    try:  # pragma: no cover - environment-specific
        import aifc  # type: ignore  # noqa: F401
    except ModuleNotFoundError:  # pragma: no cover - environment-specific
        import sys
        import types

        aifc_stub = types.ModuleType("aifc")

        class AIFCError(Exception):
            pass

        def _aifc_not_supported(*_args, **_kwargs):  # pragma: no cover
            raise AIFCError("AIFF format not supported in this environment")

        aifc_stub.Error = AIFCError
        aifc_stub.open = _aifc_not_supported
        sys.modules["aifc"] = aifc_stub

    # audioop was also removed in Python 3.13; create a minimal stub
    # implementing rms() for 16-bit PCM so SpeechRecognition can
    # compute energy levels. Other functions can be added as needed.
    try:  # pragma: no cover - environment-specific
        import audioop  # type: ignore  # noqa: F401
    except ModuleNotFoundError:  # pragma: no cover - environment-specific
        import sys
        import types
        import math
        import struct

        audioop_stub = types.ModuleType("audioop")

        class AudioOpError(Exception):
            pass

        def rms(fragment, width):  # pragma: no cover - simple approximation
            """Compute RMS for 16-bit mono PCM audio.

            This covers the common case used by SpeechRecognition for
            energy detection. For unsupported widths, returns 0.
            """
            if not fragment:
                return 0
            if width != 2:
                return 0

            try:
                count = len(fragment) // width
                if count <= 0:
                    return 0
                samples = struct.unpack('<%dh' % count, fragment)
                sum_squares = sum(s * s for s in samples)
                return int(math.sqrt(sum_squares / count))
            except Exception:
                return 0

        def max_(fragment, width):  # pragma: no cover - simple approximation
            if not fragment or width != 2:
                return 0
            try:
                count = len(fragment) // width
                if count <= 0:
                    return 0
                samples = struct.unpack('<%dh' % count, fragment)
                return max(abs(s) for s in samples)
            except Exception:
                return 0

        def lin2lin(fragment, width, newwidth):  # pragma: no cover - simple approximation
            """Best-effort linear sample width conversion.

            SpeechRecognition typically uses 2-byte widths; for that
            common case we simply return the original fragment.
            """
            if width == newwidth:
                return fragment
            # Unsupported conversions: return original data so that
            # downstream code can still attempt to operate.
            return fragment

        audioop_stub.rms = rms
        audioop_stub.max = max_
        audioop_stub.lin2lin = lin2lin
        audioop_stub.error = AudioOpError
        sys.modules["audioop"] = audioop_stub

    try:
        import speech_recognition as sr
    except Exception as e:  # pragma: no cover - environment-specific
        return {
            'success': False,
            'text': '',
            'error': f'Speech recognition not available: {str(e)}',
        }

    try:
        from pydub import AudioSegment
    except Exception as e:  # pragma: no cover - environment-specific
        return {
            'success': False,
            'text': '',
            'error': f'Audio processing not available: {str(e)}',
        }

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
