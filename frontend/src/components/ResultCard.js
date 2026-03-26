import React from 'react';
import {
  FiCheckCircle, FiAlertTriangle, FiFileText, FiImage,
  FiVideo, FiMic, FiMessageCircle
} from 'react-icons/fi';

function ResultCard({ result, index }) {
  const getTypeIcon = (type) => {
    switch (type) {
      case 'text': return <FiFileText />;
      case 'image': return <FiImage />;
      case 'video': return <FiVideo />;
      case 'audio': return <FiMic />;
      case 'voice-to-text': return <FiMessageCircle />;
      default: return <FiFileText />;
    }
  };

  const getScoreColor = (score) => {
    if (score < 30) return 'safe';
    if (score < 60) return 'warning';
    return 'danger';
  };

  return (
    <div
      className="result-card"
      style={{ animationDelay: `${index * 0.15}s` }}
    >
      <div className="result-header">
        <div className="result-type">
          <div className="result-type-icon">
            {getTypeIcon(result.content_type)}
          </div>
          <span className="result-type-label">
            {result.content_type?.charAt(0).toUpperCase() + result.content_type?.slice(1)} Content
          </span>
        </div>
        <span className={`badge ${result.status === 'Approved' ? 'badge-approved' : 'badge-flagged'}`}>
          {result.status === 'Approved' ? <FiCheckCircle size={12} /> : <FiAlertTriangle size={12} />}
          {result.status}
        </span>
      </div>

      <div className="result-body">
        <div className="result-metric">
          <div className="result-metric-label">Confidence Score</div>
          <div className="result-metric-value" style={{ color: 'var(--primary)' }}>
            {result.confidence_score}%
          </div>
          <div className="score-bar" style={{ marginTop: '8px' }}>
            <div
              className={`score-bar-fill safe`}
              style={{ width: `${result.confidence_score}%` }}
            ></div>
          </div>
        </div>

        <div className="result-metric">
          <div className="result-metric-label">Abusive Score</div>
          <div className="result-metric-value" style={{
            color: result.abusive_score < 30 ? 'var(--success)' :
                   result.abusive_score < 60 ? 'var(--warning)' : 'var(--danger)'
          }}>
            {result.abusive_score}%
          </div>
          <div className="score-bar" style={{ marginTop: '8px' }}>
            <div
              className={`score-bar-fill ${getScoreColor(result.abusive_score)}`}
              style={{ width: `${result.abusive_score}%` }}
            ></div>
          </div>
        </div>

        <div className="result-reason">
          <div className="result-metric-label">Reason</div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {result.reason}
          </p>
        </div>

        {result.categories_detected && result.categories_detected.length > 0 && (
          <div className="result-reason">
            <div className="result-metric-label">Categories Detected</div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '8px' }}>
              {result.categories_detected.map((cat, i) => (
                <span key={i} className="badge badge-flagged" style={{ fontSize: '0.6875rem' }}>
                  {cat}
                </span>
              ))}
            </div>
          </div>
        )}

        {result.corrected_text && (
          <div className="result-corrected">
            <div className="result-metric-label" style={{ color: 'var(--success)' }}>
              ✨ Suggested Correction
            </div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {result.corrected_text}
            </p>
          </div>
        )}

        {result.transcribed_text && (
          <div className="result-transcription">
            <div className="result-metric-label" style={{ color: 'var(--info)' }}>
              🎤 Transcription
            </div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {result.transcribed_text}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ResultCard;
