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
    """
    Creates and returns a configured Google Gemini API client.

    The API key is read from Django's settings (originally loaded from the
    .env file via python-dotenv).
    """
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def extract_video_id(url: str) -> str | None:
    """
    Extracts the 11-character YouTube video ID from a given URL.

    Supports the following URL formats:
      - Standard watch URLs: youtube.com/watch?v=<id>
      - Short URLs:          youtu.be/<id>
      - Embed URLs:          youtube.com/embed/<id>
      - Legacy /v/ URLs:     youtube.com/v/<id>

    Returns None if the URL does not match any recognised YouTube pattern.
    """
    match = re.search(r'(?:v=|/v/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})', url)
    return match.group(1) if match else None


def get_transcript(url: str) -> str:
    """
    Downloads the audio from a YouTube video and transcribes it using Gemini.

    Workflow:
      1. Downloads the audio track as MP3 into a temporary directory via yt-dlp.
      2. Uploads the audio file to the Gemini File API.
      3. Requests a verbatim transcription from gemini-2.5-flash-lite.
      4. Deletes the uploaded file from Gemini after transcription to avoid
         unnecessary storage usage.

    Raises ValueError if yt-dlp exits with a non-zero return code or if no
    output file is found after the download.
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

        uploaded = client.files.upload(
            file=audio_file,
            config=types.UploadFileConfig(mime_type='audio/mpeg'),
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[
                'Transcribe this audio verbatim. Return only the transcript text, nothing else.',
                uploaded,
            ],
        )
        client.files.delete(name=uploaded.name)

        return response.text.strip()


def generate_quiz_from_transcript(transcript: str, video_url: str) -> dict:
    """
    Generates a structured quiz from a video transcript using Gemini.

    Sends a prompt to gemini-2.5-flash-lite requesting exactly 10 multiple-choice
    questions with 4 distinct options each, returned as structured JSON.

    The returned dict contains:
      - title (str):       A concise quiz title derived from the transcript topic.
      - description (str): A short summary of the video (max 150 characters).
      - questions (list):  10 question objects, each with:
                             - question_title (str)
                             - question_options (list of 4 strings)
                             - answer (str, must be one of question_options)
      - video_url (str):   The original YouTube URL, appended before returning.

    Raises ValueError if Gemini returns a response that cannot be parsed as JSON.
    """
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
        model='gemini-2.5-flash-lite',
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