## Backend Setup

### 1. Install Python dependencies

From the `backend/` directory:

```bash
pip install -r requirements.txt
```

`requirements.txt` already includes `SpeechRecognition` and `pydub` so they will be installed automatically.

On Linux you also need `ffmpeg` for audio processing (used by `pydub` and speech features):

```bash
sudo apt install ffmpeg
```

### 2. Apply migrations

Still in the `backend/` directory, run:

```bash
python manage.py migrate
```

### 3. Run the development server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/`.
