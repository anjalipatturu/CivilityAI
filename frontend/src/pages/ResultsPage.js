import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { FiArrowLeft, FiUploadCloud } from 'react-icons/fi';
import ResultCard from '../components/ResultCard';

function ResultsPage({ user, token }) {
  const location = useLocation();
  const navigate = useNavigate();
  const results = location.state?.results || [];

  const approvedCount = results.filter(r => r.status === 'Approved').length;
  const flaggedCount = results.filter(r => r.status === 'Flagged').length;

  if (results.length === 0) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <p className="empty-state-text">No results to display</p>
          <p className="empty-state-hint">Submit content for moderation to see results here.</p>
          <button
            className="btn btn-primary"
            style={{ marginTop: '20px' }}
            onClick={() => navigate('/dashboard')}
          >
            <FiUploadCloud size={16} />
            Go to Moderation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="page-title">Moderation Results</h1>
          <p className="page-description">
            Analyzed {results.length} item(s) — {approvedCount} approved, {flaggedCount} flagged
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/dashboard')}>
            <FiArrowLeft size={14} />
            New Analysis
          </button>
          <button className="btn btn-outline btn-sm" onClick={() => navigate('/behavior')}>
            View Behavior
          </button>
        </div>
      </div>

      {/* Summary bar */}
      <div style={{
        display: 'flex',
        gap: '16px',
        marginBottom: '24px',
        flexWrap: 'wrap'
      }}>
        <div className="card" style={{
          flex: 1,
          minWidth: '200px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '16px 20px'
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'var(--success-bg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.125rem'
          }}>
            ✅
          </div>
          <div>
            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--success)' }}>
              {approvedCount}
            </div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Approved</div>
          </div>
        </div>

        <div className="card" style={{
          flex: 1,
          minWidth: '200px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '16px 20px'
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'var(--danger-bg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.125rem'
          }}>
            ⚠️
          </div>
          <div>
            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--danger)' }}>
              {flaggedCount}
            </div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Flagged</div>
          </div>
        </div>

        <div className="card" style={{
          flex: 1,
          minWidth: '200px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '16px 20px'
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'var(--primary-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.125rem'
          }}>
            📊
          </div>
          <div>
            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--primary)' }}>
              {results.length > 0 ? Math.round(results.reduce((acc, r) => acc + r.confidence_score, 0) / results.length) : 0}%
            </div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Avg Confidence</div>
          </div>
        </div>
      </div>

      {/* Result Cards */}
      <div className="results-list">
        {results.map((result, index) => (
          <ResultCard key={index} result={result} index={index} />
        ))}
      </div>
    </div>
  );
}

export default ResultsPage;
