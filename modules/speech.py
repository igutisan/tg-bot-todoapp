"""
Handles speech-to-text functionality.
"""
import os
import speech_recognition as sr
from pydub import AudioSegment

async def transcribe_voice_message(user_id: int, voice_file) -> str | None:
    """Transcribes a voice message and returns the text."""
    file_path = f"user_{user_id}_voice.ogg"
    wav_file_path = f"user_{user_id}_voice.wav"

    try:
        await voice_file.download_to_drive(file_path)

        audio = AudioSegment.from_ogg(file_path)
        audio.export(wav_file_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file_path) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data, language="en-US")
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"Error with speech recognition service: {e}")
        return None
    except Exception as e:
        print(f"Error processing voice message: {e}")
        return None
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(wav_file_path):
            os.remove(wav_file_path)
