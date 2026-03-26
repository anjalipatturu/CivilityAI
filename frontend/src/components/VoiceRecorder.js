import React, { useState, useRef, useEffect } from 'react';
import { FiMic, FiMicOff, FiSquare } from 'react-icons/fi';

function VoiceRecorder({ onTranscription }) {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(true);
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript + ' ';
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      const fullText = (finalTranscript + interimTranscript).trim();
      setTranscript(fullText);
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      if (event.error !== 'no-speech') {
        setIsRecording(false);
      }
    };

    recognition.onend = () => {
      if (isRecording) {
        try {
          recognition.start();
        } catch (e) {
          setIsRecording(false);
        }
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // ignore
        }
      }
    };
  }, [isRecording]);

  const startRecording = () => {
    setTranscript('');
    setIsRecording(true);
    try {
      recognitionRef.current?.start();
    } catch (e) {
      console.error('Failed to start recording:', e);
    }
  };

  const stopRecording = () => {
    setIsRecording(false);
    try {
      recognitionRef.current?.stop();
    } catch (e) {
      // ignore
    }
    if (transcript && onTranscription) {
      onTranscription(transcript);
    }
  };

  if (!isSupported) {
    return (
      <div className="voice-recorder">
        <div style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
          <FiMicOff size={32} style={{ marginBottom: '12px', opacity: 0.4 }} />
          <p>Speech recognition is not supported in this browser.</p>
          <p style={{ fontSize: '0.8125rem', marginTop: '8px' }}>
            Please use Chrome or Edge for voice-to-text features.
          </p>
        </div>
      </div>
    );
  }

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
