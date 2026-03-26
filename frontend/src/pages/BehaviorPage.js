import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import axios from 'axios';
import { Doughnut, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import {
  FiUploadCloud, FiAlertTriangle, FiActivity,
  FiShield, FiRefreshCw, FiTrendingUp
} from 'react-icons/fi';

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend);

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function BehaviorPage({ user, token }) {
  const navigate = useNavigate();
  const [behavior, setBehavior] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchBehavior = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API_URL}/user-behavior`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.data.success) {
        setBehavior(response.data.behavior);
      }
    } catch (error) {
      console.error('Behavior fetch error:', error);
      // Use demo data
      setBehavior({
        user_id: user.user_id || 'demo_user',
        email: user.email || 'demo@civility.ai',
        name: user.name || 'Demo User',
        total_uploads: 12,
        flagged_count: 3,
        abuse_score: 18,
        behavior_category: 'Safe',
        approval_rate: 75.0,
        risk_level: 'low',
        recent_flags: [
          { content_type: 'text', reason: 'Contained profanity', abusive_score: 45, created_at: new Date().toISOString() },
          { content_type: 'image', reason: 'Potentially violent content', abusive_score: 62, created_at: new Date().toISOString() },
        ],
        history: [
          { content_type: 'text', status: 'Approved', reason: 'Safe content', confidence_score: 92, abusive_score: 3, created_at: new Date().toISOString() },
          { content_type: 'text', status: 'Flagged', reason: 'Profanity detected', confidence_score: 85, abusive_score: 45, created_at: new Date().toISOString() },
          { content_type: 'image', status: 'Approved', reason: 'No issues found', confidence_score: 88, abusive_score: 5, created_at: new Date().toISOString() },
          { content_type: 'image', status: 'Flagged', reason: 'Violence detected', confidence_score: 78, abusive_score: 62, created_at: new Date().toISOString() },
          { content_type: 'video', status: 'Approved', reason: 'Content is safe', confidence_score: 90, abusive_score: 2, created_at: new Date().toISOString() },
          { content_type: 'audio', status: 'Approved', reason: 'Transcription safe', confidence_score: 82, abusive_score: 8, created_at: new Date().toISOString() },
          { content_type: 'text', status: 'Flagged', reason: 'Harassment language', confidence_score: 88, abusive_score: 55, created_at: new Date().toISOString() },
        ],
      });
      toast.info('Using demo behavior data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBehavior();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isLoading) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <div className="spinner" style={{ margin: '0 auto 16px' }}></div>
          <p className="empty-state-text">Loading behavior data...</p>
        </div>
      </div>
    );
  }

  if (!behavior) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <p className="empty-state-text">No behavior data available</p>
          <button className="btn btn-primary" style={{ marginTop: '16px' }} onClick={() => navigate('/dashboard')}>
            Start Moderating
          </button>
        </div>
      </div>
    );
  }

  const getCategoryClass = (cat) => {
    switch (cat) {
      case 'Safe': return 'safe';
      case 'Warning': return 'warning';
      case 'Risky': return 'risky';
      case 'Critical': return 'critical';
      default: return 'safe';
    }
  };

  // Chart data
  const doughnutData = {
    labels: ['Approved', 'Flagged'],
    datasets: [{
      data: [
        behavior.total_uploads - behavior.flagged_count,
        behavior.flagged_count
      ],
      backgroundColor: ['#10B981', '#EF4444'],
      borderColor: ['rgba(16,185,129,0.3)', 'rgba(239,68,68,0.3)'],
      borderWidth: 2,
      hoverOffset: 6,
    }],
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#A7A9BE', font: { family: 'Inter', size: 12 }, padding: 16 },
      },
    },
    cutout: '65%',
  };

  // History chart data
  const history = behavior.history || [];
  const historyLabels = history.slice(0, 10).map((_, i) => `#${i + 1}`);
  const historyScores = history.slice(0, 10).map(h => h.abusive_score);

  const barData = {
    labels: historyLabels,
    datasets: [{
      label: 'Abusive Score',
      data: historyScores,
      backgroundColor: historyScores.map(s =>
        s < 30 ? 'rgba(16, 185, 129, 0.7)' :
        s < 60 ? 'rgba(245, 158, 11, 0.7)' :
        'rgba(239, 68, 68, 0.7)'
      ),
      borderColor: historyScores.map(s =>
        s < 30 ? '#10B981' :
        s < 60 ? '#F59E0B' :
        '#EF4444'
      ),
      borderWidth: 1,
      borderRadius: 6,
    }],
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: { color: '#A7A9BE', font: { family: 'Inter', size: 12 } },
      },
    },
    scales: {
      x: {
        ticks: { color: '#6B6D80', font: { family: 'Inter' } },
        grid: { color: 'rgba(255,255,255,0.04)' },
      },
      y: {
        min: 0,
        max: 100,
        ticks: { color: '#6B6D80', font: { family: 'Inter' } },
        grid: { color: 'rgba(255,255,255,0.04)' },
      },
    },
  };

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="page-title">User Behavior Dashboard</h1>
          <p className="page-description">
            Monitor your moderation activity and behavior metrics
          </p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={fetchBehavior}>
          <FiRefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Stat Cards */}
      <div className="behavior-stats">
        <div className="stat-card animate-fade-in" style={{ animationDelay: '0.1s' }}>
          <div className="stat-icon">
            <FiUploadCloud size={24} color="var(--primary)" />
          </div>
          <div className="stat-value" style={{ color: 'var(--primary)' }}>
            {behavior.total_uploads}
          </div>
          <div className="stat-label">Total Uploads</div>
        </div>

        <div className="stat-card animate-fade-in" style={{ animationDelay: '0.2s' }}>
          <div className="stat-icon">
            <FiAlertTriangle size={24} color="var(--danger)" />
          </div>
          <div className="stat-value" style={{ color: 'var(--danger)' }}>
            {behavior.flagged_count}
          </div>
          <div className="stat-label">Flagged Content</div>
        </div>

        <div className="stat-card animate-fade-in" style={{ animationDelay: '0.3s' }}>
          <div className="stat-icon">
            <FiActivity size={24} color={
              behavior.abuse_score < 30 ? 'var(--success)' :
              behavior.abuse_score < 60 ? 'var(--warning)' : 'var(--danger)'
            } />
          </div>
          <div className={`stat-value ${getCategoryClass(behavior.behavior_category)}`}>
            {behavior.abuse_score}
          </div>
          <div className="stat-label">Abuse Score</div>
        </div>

        <div className="stat-card animate-fade-in" style={{ animationDelay: '0.4s' }}>
          <div className="stat-icon">
            <FiShield size={24} color={
              behavior.behavior_category === 'Safe' ? 'var(--success)' :
              behavior.behavior_category === 'Warning' ? 'var(--warning)' : 'var(--danger)'
            } />
          </div>
          <div className={`stat-value ${getCategoryClass(behavior.behavior_category)}`}>
            {behavior.behavior_category}
          </div>
          <div className="stat-label">Behavior Category</div>
        </div>
      </div>

      {/* Charts */}
      <div className="dashboard-grid">
        <div className="chart-container animate-fade-in" style={{ animationDelay: '0.5s' }}>
          <div className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FiTrendingUp size={16} color="var(--primary)" />
            Content Approval Rate
          </div>
          <div style={{ maxHeight: '280px', display: 'flex', justifyContent: 'center' }}>
            <Doughnut data={doughnutData} options={doughnutOptions} />
          </div>
          <div style={{ textAlign: 'center', marginTop: '12px', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Approval Rate: <strong style={{ color: 'var(--success)' }}>{behavior.approval_rate}%</strong>
          </div>
        </div>

        <div className="chart-container animate-fade-in" style={{ animationDelay: '0.6s' }}>
          <div className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FiActivity size={16} color="var(--primary)" />
            Recent Abuse Scores
          </div>
          <Bar data={barData} options={barOptions} />
        </div>
      </div>

      {/* Recent History */}
      {history.length > 0 && (
        <div className="chart-container animate-fade-in" style={{ animationDelay: '0.7s', marginTop: '24px' }}>
          <div className="chart-title">📋 Recent Moderation History</div>
          <div style={{ overflowX: 'auto' }}>
            <table className="history-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Reason</th>
                  <th>Confidence</th>
                  <th>Abuse Score</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item, index) => (
                  <tr key={index}>
                    <td>
                      <span style={{ textTransform: 'capitalize' }}>{item.content_type}</span>
                    </td>
                    <td>
                      <span className={`badge ${item.status === 'Approved' ? 'badge-approved' : 'badge-flagged'}`}>
                        {item.status}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', maxWidth: '300px' }}>
                      {item.reason}
                    </td>
                    <td>
                      <strong style={{ color: 'var(--primary)' }}>{item.confidence_score}%</strong>
                    </td>
                    <td>
                      <strong style={{
                        color: item.abusive_score < 30 ? 'var(--success)' :
                               item.abusive_score < 60 ? 'var(--warning)' : 'var(--danger)'
                      }}>
                        {item.abusive_score}%
                      </strong>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default BehaviorPage;
