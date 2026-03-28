import React, { useState, useRef } from 'react';
import { FiMic, FiSquare } from 'react-icons/fi';

function VoiceRecorder({ onTranscription }) {
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState('');
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const [isRecording, setIsRecording] = useState(false);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  const startRecording = async () => {
    setTranscript('');
    setError('');
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      setError('Microphone recording is not supported in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);

      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('audio', blob, 'voice.webm');

        try {
          const response = await fetch(`${API_URL}/api/speech-to-text/`, {
            method: 'POST',
            body: formData,
          });

          const data = await response.json();

          if (data.text) {
            setTranscript(data.text);
            if (onTranscription) {
              onTranscription(data.text);
            }
          } else if (data.error) {
            setError(data.error);
          }
        } catch (err) {
          setError('Failed to transcribe audio. Please try again.');
        } finally {
          stream.getTracks().forEach((t) => t.stop());
          setIsRecording(false);
          chunksRef.current = [];
        }
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
    } catch (e) {
      setError('Unable to access microphone. Check permissions and try again.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  };

  return (
    <div className="voice-recorder">
      <button
        className={`mic-button ${isRecording ? 'recording' : ''}`}
        onClick={isRecording ? stopRecording : startRecording}
        title={isRecording ? 'Stop recording' : 'Start recording'}
      >
        {isRecording ? <FiSquare size={24} /> : <FiMic size={28} />}
      </button>

      <p className={`voice-status ${isRecording ? 'recording' : ''}`}>
        {isRecording ? '🔴 Recording... Click to stop' : 'Click the mic to start speaking'}
      </p>

      {error && (
        <p style={{ color: 'var(--danger)', fontSize: '0.8125rem', marginTop: '8px' }}>
          {error}
        </p>
      )}

      {transcript && (
        <div className="transcription-preview">
          <strong style={{ color: 'var(--text-primary)', fontStyle: 'normal' }}>
            Transcription:
          </strong><br />
          {transcript}
        </div>
      )}

      {transcript && !isRecording && (
        <button
          className="btn btn-primary btn-sm"
          onClick={() => onTranscription && onTranscription(transcript)}
        >
          Use this transcription
        </button>
      )}
    </div>
  );
}

export default VoiceRecorder;
