import React, { useState, useRef } from 'react';
import { FiMic, FiSquare, FiTrash2 } from 'react-icons/fi';

function VoiceUpload({ files, setFiles }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [error, setError] = useState('');
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    setError('');

    if (!navigator.mediaDevices || !window.MediaRecorder) {
      setIsSupported(false);
      setError('Microphone recording is not supported in this browser. Please use a modern browser like Chrome or Edge.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Pick a supported MIME type for best compatibility
      let options = {};
      try {
        const MR = window.MediaRecorder;
        if (MR && typeof MR.isTypeSupported === 'function') {
          if (MR.isTypeSupported('audio/webm')) {
            options.mimeType = 'audio/webm';
          } else if (MR.isTypeSupported('audio/ogg')) {
            options.mimeType = 'audio/ogg';
          }
        }
      } catch (_) {
        // Ignore MIME detection issues, will fall back below
      }

      let mediaRecorder;
      try {
        mediaRecorder = new MediaRecorder(stream, options);
      } catch (err) {
        // Fallback: try without options if MIME type not accepted
        mediaRecorder = new MediaRecorder(stream);
      }

      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        const extension = mimeType.includes('ogg') ? 'ogg' : 'webm';
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const file = new File([blob], `recording-${Date.now()}.${extension}`, { type: mimeType });
        setFiles([file]);
        stream.getTracks().forEach(t => t.stop());
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
    } catch (e) {
      console.error('Error starting microphone recording:', e);
      setError('Unable to access microphone. Please check browser permissions and try again.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const clearRecording = () => {
    setFiles([]);
    setError('');
  };

  if (!isSupported) {
    return (
      <div className="voice-recorder">
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Microphone recording is not supported or not permitted in this browser.
        </p>
      </div>
    );
  }

  const hasRecording = files && files.length > 0;
  const currentFile = hasRecording ? files[0] : null;

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
        {isRecording ? '🔴 Recording... Click to stop' : 'Click the mic to record your voice'}
      </p>

      {error && (
        <p style={{ color: 'var(--danger)', fontSize: '0.8125rem', marginTop: '8px' }}>
          {error}
        </p>
      )}

      {hasRecording && (
        <div style={{ marginTop: '12px' }}>
          <div
            className="file-tag"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
          >
            <span style={{ fontSize: '0.875rem' }}>{currentFile.name}</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
              ({(currentFile.size / 1024).toFixed(1)} KB)
            </span>
            <button
              className="file-tag-remove"
              onClick={clearRecording}
              title="Remove recording"
            >
              <FiTrash2 size={10} />
            </button>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Recording will be uploaded for transcription & moderation when you click
            <strong> Analyze Content</strong>.
          </p>
        </div>
      )}
    </div>
  );
}

export default VoiceUpload;
