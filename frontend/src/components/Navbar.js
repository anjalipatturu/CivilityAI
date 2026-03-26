import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { FiHome, FiUploadCloud, FiBarChart2, FiLogOut, FiShield } from 'react-icons/fi';

function Navbar({ user, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="navbar">
      <div
        className="navbar-brand"
        onClick={() => navigate('/home')}
      >
        <div className="brand-icon">
          <FiShield />
        </div>
        <span>Civility.ai</span>
      </div>

      <div className="navbar-links">
        <button
          className={`nav-link ${isActive('/home') ? 'active' : ''}`}
          onClick={() => navigate('/home')}
        >
          <FiHome size={16} />
          <span>Home</span>
        </button>
        <button
          className={`nav-link ${isActive('/dashboard') ? 'active' : ''}`}
          onClick={() => navigate('/dashboard')}
        >
          <FiUploadCloud size={16} />
          <span>Moderate</span>
        </button>
        <button
          className={`nav-link ${isActive('/behavior') ? 'active' : ''}`}
          onClick={() => navigate('/behavior')}
        >
          <FiBarChart2 size={16} />
          <span>Behavior</span>
        </button>

        <div className="nav-user" onClick={() => navigate('/behavior')}>
          <div className="nav-user-avatar">
            {user.picture ? (
              <img src={user.picture} alt={user.name} />
            ) : (
              user.name?.charAt(0)?.toUpperCase() || 'U'
            )}
          </div>
          <span className="nav-user-name">{user.name || 'User'}</span>
        </div>

        <button className="btn-logout" onClick={onLogout}>
          <FiLogOut size={14} />
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
