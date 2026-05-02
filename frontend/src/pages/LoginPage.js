import React, { useState } from 'react';
import { useGoogleLogin } from '@react-oauth/google';
import { toast } from 'react-toastify';
import { FiShield, FiLock, FiGlobe } from 'react-icons/fi';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function LoginPage({ onLogin }) {
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const googleLogin = useGoogleLogin({
    scope: 'openid profile email',
    onSuccess: async (tokenResponse) => {
      setIsLoading(true);
      try {
        const response = await axios.post(`${API_URL}/auth/google-login`, {
          token: tokenResponse.access_token,
        });

        if (response.data.success) {
          onLogin(response.data.user, response.data.token);
          toast.success(`Welcome, ${response.data.user.name}!`);
        }
      } catch (error) {
        console.error('Login error:', error);
        toast.error('Login failed. Please try again.');
      } finally {
        setIsLoading(false);
      }
    },
    onError: (error) => {
      console.error('Google login error:', error);
      toast.error('Google login failed');
    },
  });

  const handleEmailLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await axios.post(`${API_URL}/auth/login`, {
        email,
        password,
      });

      if (response.data.success) {
        onLogin(response.data.user, response.data.token);
        toast.success(`Welcome back, ${response.data.user.name || response.data.user.email}!`);
      }
    } catch (error) {
      console.error('Email login error:', error);
      toast.error(error.response?.data?.error || 'Invalid email or password');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmailRegister = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await axios.post(`${API_URL}/auth/register`, {
        email,
        password,
      });

      if (response.data.success) {
        onLogin(response.data.user, response.data.token);
        toast.success(`Account created for ${response.data.user.email}`);
      }
    } catch (error) {
      console.error('Email register error:', error);
      toast.error(error.response?.data?.error || 'Could not register with these details');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* Background orbs */}
      <div className="login-bg-orb login-bg-orb-1"></div>
      <div className="login-bg-orb login-bg-orb-2"></div>

      <div className="login-card">
        <div className="login-logo">
          <FiShield size={28} color="white" />
        </div>

        <h1 className="login-title">Civility.ai</h1>
        <p className="login-subtitle">
          AI-powered content moderation to keep your platform safe, clean, and respectful.
        </p>

        {/* 1. Manual email/password login */}
        <div className="login-divider">Sign in with email</div>

        <form className="login-form" onSubmit={handleEmailLogin}>
          <input
            type="email"
            className="input"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            className="input"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading}
              style={{ flex: 1 }}
            >
              <FiLock size={16} />
              Login
            </button>
            <button
              type="button"
              className="btn btn-outline"
              onClick={handleEmailRegister}
              disabled={isLoading}
              style={{ flex: 1 }}
            >
              Create account
            </button>
          </div>
        </form>

        {/* 2. Google OAuth login */}
        <div className="login-divider">or continue with Google</div>

        <button
          className="btn btn-google"
          onClick={() => googleLogin()}
          disabled={isLoading}
          style={{ width: '100%' }}
        >
          <svg viewBox="0 0 24 24" width="20" height="20">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          {isLoading ? 'Signing in...' : 'Continue with Google'}
        </button>


        <div className="login-features">
          <div className="login-feature">
            <span className="login-feature-icon">🛡️</span>
            <span>AI Moderation</span>
          </div>
          <div className="login-feature">
            <span className="login-feature-icon"><FiLock size={18} /></span>
            <span>Secure</span>
          </div>
          <div className="login-feature">
            <span className="login-feature-icon"><FiGlobe size={18} /></span>
            <span>Real-time</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
