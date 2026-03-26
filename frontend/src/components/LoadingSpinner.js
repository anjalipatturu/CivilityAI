import React from 'react';

function LoadingSpinner({ text = 'Analyzing content...' }) {
  return (
    <div className="spinner-overlay">
      <div className="spinner"></div>
      <p className="spinner-text">{text}</p>
    </div>
  );
}

export default LoadingSpinner;
