import re
import json
import os
import subprocess
import tempfile
from pathlib import Path

from google import genai
from google.genai import types
from django.conf import settings


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def extract_video_id(url: str) -> str | None:
    """Validiert und extrahiert die YouTube-Video-ID."""
    match = re.search(r'(?:v=|/v/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})', url)
    return match.group(1) if match else None


def get_transcript(url: str) -> str:
    """
    Lädt Audio mit yt-dlp herunter (ffmpeg konvertiert zu mp3)
    und transkribiert es über Gemini Whisper.
    """
    client = _get_client()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, 'audio.%(ext)s')

        result = subprocess.run(
            [
                'yt-dlp',
                '--no-playlist',
                '-x',
                '--audio-format', 'mp3',
                '--audio-quality', '5',
                '-o', output_template,
                url,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            raise ValueError(f'yt-dlp error: {result.stderr.strip()}')

        audio_file = Path(tmpdir) / 'audio.mp3'
        if not audio_file.exists():
            files = list(Path(tmpdir).iterdir())
            if not files:
                raise ValueError('Audio download failed — no output file found.')
            audio_file = files[0]

        # Audio über Gemini File API hochladen
        uploaded = client.files.upload(
            file=audio_file,
            config=types.UploadFileConfig(mime_type='audio/mpeg'),
        )

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[
                'Transcribe this audio verbatim. Return only the transcript text, nothing else.',
                uploaded,
            ],
        )

        # Hochgeladene Datei wieder löschen
        client.files.delete(name=uploaded.name)

        return response.text.strip()


def generate_quiz_from_transcript(transcript: str, video_url: str) -> dict:
    """Schickt das Transkript an Gemini und bekommt ein strukturiertes Quiz zurück."""
    client = _get_client()

    prompt = f"""Based on the following transcript, generate a quiz in valid JSON format.

The quiz must follow this exact structure:

{{
  "title": "Create a concise quiz title based on the topic of the transcript.",
  "description": "Summarize the transcript in no more than 150 characters. Do not include any quiz questions or answers.",
  "questions": [
    {{
      "question_title": "The question goes here.",
      "question_options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "The correct answer from the above options"
    }},
    ...
    (exactly 10 questions)
  ]
}}

Requirements:
- Each question must have exactly 4 distinct answer options.
- Only one correct answer is allowed per question, and it must be present in 'question_options'.
- The output must be valid JSON and parsable as-is (e.g., using Python's json.loads).
- Do not include explanations, comments, or any text outside the JSON.

Transcript:
{transcript[:6000]}"""

    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            temperature=0.7,
        ),
    )
    raw = response.text.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError('Gemini returned invalid JSON.')

    data['video_url'] = video_url
    return data