# Quizly Backend

Django REST backend for automatic quiz generation from YouTube videos using Gemini AI.

## Prerequisites

- Python 3.12+
- ffmpeg (`sudo apt install ffmpeg`)
- yt-dlp (installed via `requirements.txt`)
- A [Gemini API Key](https://aistudio.google.com/apikey)

## Installation

```bash
# Clone the repository
git clone https://github.com/fReEsPiRiT-Spiritsoft/Quizly_backend.git
cd Quizly_backend

# Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

> The `.env` file is listed in `.gitignore` and will **not** be pushed to the repository.

## Setup & Run

```bash
python manage.py migrate
python manage.py runserver 8000
```

## API Endpoints

| Method | Endpoint               | Description                           | Auth |
|--------|------------------------|---------------------------------------|------|
| POST   | `/api/register/`       | Register a new user                   | No   |
| POST   | `/api/login/`          | Login (sets auth cookies)             | No   |
| POST   | `/api/logout/`         | Logout (deletes cookies)              | Yes  |
| POST   | `/api/token/refresh/`  | Refresh access token                  | No   |
| GET    | `/api/quizzes/`        | Get all quizzes of the user           | Yes  |
| POST   | `/api/quizzes/`        | Generate quiz from YouTube URL        | Yes  |
| GET    | `/api/quizzes/{id}/`   | Get a specific quiz                   | Yes  |
| PATCH  | `/api/quizzes/{id}/`   | Partially update a quiz               | Yes  |
| DELETE | `/api/quizzes/{id}/`   | Delete a quiz                         | Yes  |