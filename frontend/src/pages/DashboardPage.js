import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import axios from 'axios';
import {
  FiFileText, FiMic,
  FiMessageCircle, FiSend, FiUploadCloud
} from 'react-icons/fi';

import FileUploader from '../components/FileUploader';
import VoiceRecorder from '../components/VoiceRecorder';
import VoiceUpload from '../components/VoiceUpload';
import LoadingSpinner from '../components/LoadingSpinner';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function DashboardPage({ user, token }) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('text');
  const [textContent, setTextContent] = useState('');
  const [files, setFiles] = useState([]);
  const [voiceFiles, setVoiceFiles] = useState([]);
  const [transcription, setTranscription] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const tabs = [
    { id: 'text', label: 'Text', icon: <FiFileText size={16} /> },
    { id: 'files', label: 'Files', icon: <FiUploadCloud size={16} /> },
    { id: 'voice-upload', label: 'Voice Upload', icon: <FiMic size={16} /> },
    { id: 'voice-to-text', label: 'Voice-to-Text', icon: <FiMessageCircle size={16} /> },
  ];

  const handleSubmit = async () => {
    // Validate input
    if (!textContent && files.length === 0 && voiceFiles.length === 0 && !transcription) {
      toast.error('Please provide some content to analyze');
      return;
    }

    setIsLoading(true);

    try {
      const formData = new FormData();

      if (textContent) {
        formData.append('text', textContent);
      }

      if (transcription) {
        formData.append('transcription', transcription);
      }

      files.forEach((file) => {
        formData.append('files', file);
      });

      voiceFiles.forEach((file) => {
        formData.append('files', file);
      });

      const response = await axios.post(`${API_URL}/analyze-content`, formData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.success) {
        const results = response.data.results || [];

        // Notify explicitly when voice-to-text was used
        if (results.some(r => r && r.transcribed_text)) {
          toast.info('Voice transcription processed successfully. Showing moderation on the transcribed text.');
        }

        toast.success(`${response.data.count} item(s) analyzed successfully!`);

        // Navigate to results with data
        navigate('/results', { state: { results } });
      }
    } catch (error) {
      console.error('Analysis error:', error);

      const status = error.response?.status;

      if (status === 401) {
        toast.error('Session expired. Please login again.');
      } else if (status === 403) {
        // Backend explicitly blocked the request (e.g. suspended account).
        const message = error.response?.data?.error || 'Access denied for this analysis request.';
        toast.error(message);
      } else {
        // Demo mode – simulate results only for network/unknown errors
        const demoResults = [];

        if (textContent) {
          demoResults.push(simulateAnalysis(textContent, 'text'));
        }

        if (transcription) {
          const result = simulateAnalysis(transcription, 'voice-to-text');
          result.transcribed_text = transcription;
          demoResults.push(result);
        }

        files.forEach((file) => {
          const ext = file.name.split('.').pop().toLowerCase();
          let type = 'unknown';
          if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) type = 'image';
          else if (['mp4', 'avi', 'mov', 'mkv', 'webm'].includes(ext)) type = 'video';
          else if (['mp3', 'wav', 'ogg', 'flac', 'm4a'].includes(ext)) type = 'audio';
          demoResults.push(simulateAnalysis(file.name, type));
        });

        voiceFiles.forEach((file) => {
          demoResults.push(simulateAnalysis(file.name, 'audio'));
        });

        if (demoResults.length > 0) {
          toast.success(`${demoResults.length} item(s) analyzed (Demo mode)`);
          navigate('/results', { state: { results: demoResults } });
        } else {
          toast.error('Analysis failed. Please try again.');
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  const simulateAnalysis = (content, type) => {
    const flaggedWords = ['kill', 'hate', 'die', 'stupid', 'idiot', 'damn', 'violence', 'attack'];
    const contentLower = content.toLowerCase();
    const found = flaggedWords.filter(w => contentLower.includes(w));
    const isFlagged = found.length > 0;

    return {
      content_type: type,
      status: isFlagged ? 'Flagged' : 'Approved',
      reason: isFlagged
        ? `Contains potentially harmful language: ${found.join(', ')}`
        : 'Content appears safe and appropriate (Demo mode)',
      confidence_score: isFlagged ? 78 : 92,
      abusive_score: isFlagged ? Math.min(85, 25 + found.length * 20) : 5,
      categories_detected: isFlagged ? ['Profanity', 'Potential harassment'] : [],
      corrected_text: isFlagged ? 'Please rephrase in a more respectful manner.' : null,
      transcribed_text: type === 'audio' || type === 'voice-to-text' ? content : null,
    };
  };

  const handleVoiceTranscription = (text) => {
    setTranscription(text);
    setActiveTab('voice-to-text');
    toast.info('Transcription captured!');
  };

  const clearAll = () => {
    setTextContent('');
    setFiles([]);
    setVoiceFiles([]);
    setTranscription('');
  };

  const hasContent = textContent || files.length > 0 || voiceFiles.length > 0 || transcription;

  return (
    <div className="page-container">
      {isLoading && <LoadingSpinner text="🔍 Analyzing your content with AI..." />}

      <div className="page-header">
        <h1 className="page-title">Content Moderation</h1>
        <p className="page-description">
          Upload or enter content for AI-powered moderation analysis. Supports text, images, videos, and voice input.
        </p>
      </div>

      {/* Upload Tabs */}
      <div className="upload-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`upload-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="upload-tab-icon">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="card animate-fade-in" style={{ marginBottom: '24px' }}>
        {activeTab === 'text' && (
          <div>
            <label className="form-label">Enter text content to analyze</label>
            <textarea
              className="form-textarea"
              placeholder="Type or paste content here for moderation analysis..."
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              rows={6}
            />
          </div>
        )}

        {activeTab === 'files' && (
          <div>
            <label className="form-label">Upload images, videos, or audio files</label>
            <FileUploader files={files} setFiles={setFiles} />
          </div>
        )}

        {activeTab === 'voice-upload' && (
          <div>
            <label className="form-label">Upload an audio file for transcription & analysis</label>
            <VoiceUpload
              files={voiceFiles}
              setFiles={setVoiceFiles}
            />
          </div>
        )}

        {activeTab === 'voice-to-text' && (
          <div>
            <label className="form-label">Use your microphone for live speech-to-text</label>
            <VoiceRecorder onTranscription={handleVoiceTranscription} />

            {transcription && (
              <div style={{ marginTop: '16px' }}>
                <label className="form-label">Captured Transcription</label>
                <textarea
                  className="form-textarea"
                  value={transcription}
                  onChange={(e) => setTranscription(e.target.value)}
                  rows={3}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Summary & Submit */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          {textContent && (
            <span className="badge badge-approved" style={{ textTransform: 'none' }}>
              <FiFileText size={12} /> Text ready
            </span>
          )}
          {files.length > 0 && (
            <span className="badge badge-approved" style={{ textTransform: 'none' }}>
              <FiUploadCloud size={12} /> {files.length} file(s) ready
            </span>
          )}
          {voiceFiles.length > 0 && (
            <span className="badge badge-approved" style={{ textTransform: 'none' }}>
              <FiMic size={12} /> {voiceFiles.length} voice file(s) ready
            </span>
          )}
          {transcription && (
            <span className="badge badge-approved" style={{ textTransform: 'none' }}>
              <FiMic size={12} /> Transcription ready
            </span>
          )}
          {!hasContent && (
            <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              No content added yet
            </span>
          )}
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          {hasContent && (
            <button className="btn btn-secondary btn-sm" onClick={clearAll}>
              Clear All
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={!hasContent || isLoading}
          >
            <FiSend size={16} />
            Analyze Content
          </button>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
