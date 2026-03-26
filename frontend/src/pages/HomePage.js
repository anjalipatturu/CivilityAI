import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FiShield, FiFileText, FiImage, FiVideo,
  FiMic, FiBarChart2, FiAlertTriangle, FiArrowRight
} from 'react-icons/fi';

function HomePage({ user }) {
  const navigate = useNavigate();

  const features = [
    {
      icon: <FiFileText size={24} />,
      name: 'Text Moderation',
      desc: 'Analyze text content for hate speech, harassment, profanity, and inappropriate language using advanced AI.',
    },
    {
      icon: <FiImage size={24} />,
      name: 'Image Analysis',
      desc: 'Detect violence, nudity, hate symbols, and other inappropriate visual content in uploaded images.',
    },
    {
      icon: <FiVideo size={24} />,
      name: 'Video Screening',
      desc: 'Screen video content for harmful material, dangerous activities, and policy violations.',
    },
    {
      icon: <FiMic size={24} />,
      name: 'Voice & Audio',
      desc: 'Process voice uploads and live speech with real-time transcription and content analysis.',
    },
    {
      icon: <FiBarChart2 size={24} />,
      name: 'Behavior Tracking',
      desc: 'Monitor user behavior patterns, track abuse scores, and categorize risk levels over time.',
    },
    {
      icon: <FiAlertTriangle size={24} />,
      name: 'Admin Alerts',
      desc: 'Automatic alert system that notifies administrators when users exceed abuse thresholds.',
    },
  ];

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-badge">
          <FiShield size={14} />
          AI-Powered Content Moderation
        </div>

        <h1 className="hero-title">
          Keep Your Platform{' '}
          <span className="hero-title-gradient">Safe & Civil</span>
        </h1>

        <p className="hero-description">
          Civility.ai uses advanced AI to automatically moderate text, images, videos, 
          and voice content in real-time — ensuring only safe and appropriate content 
          reaches your community.
        </p>

        <div className="hero-actions">
          <button
            className="btn btn-primary btn-lg"
            onClick={() => navigate('/dashboard')}
          >
            Start Moderation
            <FiArrowRight size={18} />
          </button>
          <button
            className="btn btn-secondary btn-lg"
            onClick={() => navigate('/behavior')}
          >
            View Dashboard
          </button>
        </div>

        <div className="hero-stats">
          <div className="hero-stat">
            <div className="hero-stat-value">5+</div>
            <div className="hero-stat-label">Content Types</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-value">Real-time</div>
            <div className="hero-stat-label">Analysis</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-value">AI</div>
            <div className="hero-stat-label">Gemini Powered</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-value">24/7</div>
            <div className="hero-stat-label">Monitoring</div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <h2 className="features-title">
          Powerful Features for <span className="text-gradient">Complete Protection</span>
        </h2>

        <div className="features-grid">
          {features.map((feature, index) => (
            <div
              key={index}
              className="feature-card animate-fade-in-up"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="feature-icon">{feature.icon}</div>
              <h3 className="feature-name">{feature.name}</h3>
              <p className="feature-desc">{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default HomePage;
