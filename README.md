# 🛡️ Civility.ai — AI-Powered Content Moderation System

<p align="center">
  <strong>An intelligent content moderation platform that analyzes text, images, videos, and voice content in real-time using AI.</strong>
</p>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup Guide](#setup-guide)
- [OAuth Setup](#oauth-setup)
- [API Documentation](#api-documentation)
- [Features](#features)

---

## 🎯 Overview

Civility.ai is a full-stack content moderation system that automatically reviews user-generated content before publication. It uses Google's Gemini AI to detect harmful, abusive, or inappropriate content across multiple media types.

### Key Capabilities
- **Text Moderation** — Detect hate speech, harassment, profanity
- **Image Analysis** — Identify violence, nudity, hate symbols
- **Video Screening** — Screen for harmful visual content
- **Voice Processing** — Speech-to-text transcription + content analysis
- **Behavior Tracking** — Monitor user abuse patterns over time
- **Admin Alerts** — Automatic notifications for repeated violations

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────┐
│   React.js      │────▶│   Django REST API     │────▶│   MongoDB    │
│   Frontend      │◀────│   Backend             │◀────│   Database   │
│                 │     │                        │     └──────────────┘
│  • Google OAuth │     │  • Auth (OAuth + JWT)  │
│  • Upload UI    │     │  • Gemini AI Analysis  │     ┌──────────────┐
│  • Voice Record │     │  • Voice Processing    │────▶│  Gemini API  │
│  • Charts       │     │  • Behavior Tracking   │◀────│  (Google AI) │
│  • Results      │     │  • Admin Alerts        │     └──────────────┘
└─────────────────┘     └──────────────────────┘
```

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React.js, React Router, Chart.js, React Toastify |
| Backend | Django, Django REST Framework |
| Database | MongoDB (via PyMongo) |
| AI | Google Gemini 1.5 Flash |
| Auth | Google OAuth 2.0 + JWT |
| Voice | Web Speech API (frontend), SpeechRecognition + pydub (backend) |

---

## 📁 Project Structure

```
project-root/
│
├── frontend/                    # React.js Frontend
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── components/
│       │   ├── Navbar.js        # Navigation bar
│       │   ├── FileUploader.js  # Drag & drop file upload
│       │   ├── VoiceRecorder.js # Speech-to-text recorder
│       │   ├── ResultCard.js    # Moderation result display
│       │   └── LoadingSpinner.js
│       ├── pages/
│       │   ├── LoginPage.js     # Google OAuth login
│       │   ├── HomePage.js      # Landing page
│       │   ├── DashboardPage.js # Upload & moderation
│       │   ├── ResultsPage.js   # Analysis results
│       │   └── BehaviorPage.js  # User behavior dashboard
│       ├── App.js               # Routes & auth state
│       ├── index.js             # Entry point
│       └── styles.css           # Global styles
│
├── backend/                     # Django Backend
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   └── backend_project/
│       ├── __init__.py
│       ├── settings.py          # Django + MongoDB config
│       ├── urls.py              # API routes
│       ├── views.py             # API endpoints
│       ├── models.py            # MongoDB document schemas
│       ├── mongo.py             # MongoDB connection & CRUD
│       ├── gemini.py            # Gemini AI integration
│       ├── behavior.py          # User behavior tracking
│       ├── voice.py             # Audio-to-text processing
│       ├── auth.py              # OAuth + JWT authentication
│       └── utils.py             # Helper utilities
│
└── README.md
```

---

## 🚀 Setup Guide

### Prerequisites
- **Node.js** (v16+) and npm
- **Python** (3.9+) and pip
- **MongoDB** (running locally or Atlas URI)
- **Google Cloud Console** account (for OAuth & Gemini API)

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your keys (see OAuth Setup below)

# Run migrations (for Django internals)
python manage.py migrate

# Start the server
python manage.py runserver
```

### 2. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Configure environment
# Edit .env with your Google Client ID

# Start dev server
npm start
```

The frontend runs on `http://localhost:3000` and the backend on `http://localhost:8000`.

---

## 🔐 OAuth Setup Guide

### Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the **Google People API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Set application type to **Web application**
6. Add authorized JavaScript origins:
   - `http://localhost:3000`
7. Add authorized redirect URIs:
   - `http://localhost:3000`
8. Copy the **Client ID** and **Client Secret**

### Configure Keys


### Gemini API Setup

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create an API key
3. Add to `backend/.env`:
```env
GEMINI_API_KEY=your-gemini-api-key
```

### Demo Mode
If no API keys are configured, the system runs in **Demo Mode** with simulated responses — perfect for development and testing.

---

## 📡 API Documentation

### Base URL: `http://localhost:8000`

### Authentication
All protected endpoints require a JWT token in the `Authorization` header:
```
Authorization: Bearer <jwt_token>
```

---

### `POST /auth/google-login`
Authenticate with Google OAuth.

**Request:**
```json
{
  "token": "google-oauth-access-token"
}
```

**Response:**
```json
{
  "success": true,
  "token": "jwt-token-here",
  "user": {
    "user_id": "google-sub-id",
    "email": "user@gmail.com",
    "name": "User Name",
    "picture": "https://..."
  }
}
```

---

### `POST /analyze-content`
Submit content for AI moderation. Supports multipart form data.

**Form Fields:**
- `text` — Text content to analyze
- `transcription` — Voice-to-text transcription
- `files` — Image, video, or audio files (multiple)

**Response:**
```json
{
  "success": true,
  "count": 1,
  "results": [
    {
      "content_type": "text",
      "status": "Approved",
      "reason": "Content appears safe",
      "confidence_score": 92,
      "abusive_score": 5,
      "categories_detected": [],
      "corrected_text": null,
      "transcribed_text": null
    }
  ]
}
```

---

### `GET /user-behavior`
Get behavior metrics for the authenticated user.

**Response:**
```json
{
  "success": true,
  "behavior": {
    "user_id": "...",
    "total_uploads": 15,
    "flagged_count": 3,
    "abuse_score": 22,
    "behavior_category": "Safe",
    "approval_rate": 80.0,
    "risk_level": "low",
    "history": [...]
  }
}
```

---

### `POST /send-alert`
Trigger admin alert for the current user.

**Request:**
```json
{
  "reason": "Repeated abuse violations"
}
```

---

### `GET /moderation-history`
Get moderation history for the authenticated user.

**Query Params:** `?limit=50`

---

## ✨ Features

### Content Moderation
- ✅ Text analysis (hate speech, profanity, harassment)
- ✅ Image analysis (violence, nudity, hate symbols)
- ✅ Video screening (dangerous content)
- ✅ Audio file upload with speech-to-text
- ✅ Live voice-to-text via browser microphone

### User Experience
- ✅ Google OAuth login
- ✅ Demo mode for development
- ✅ Drag & drop file upload
- ✅ Real-time speech transcription
- ✅ Loading spinners & toast notifications
- ✅ Animated score visualizations
- ✅ Interactive charts (doughnut + bar)

### Security & Monitoring
- ✅ JWT token authentication
- ✅ Protected API routes
- ✅ User behavior tracking
- ✅ Rolling abuse score calculation
- ✅ Behavior categorization (Safe/Warning/Risky/Critical)
- ✅ Admin email alerts for repeated violations

### Design
- ✅ Purple-based dark theme (#6C63FF)
- ✅ Glassmorphism effects
- ✅ Micro-animations & transitions
- ✅ Fully responsive design
- ✅ Modern Inter font typography


