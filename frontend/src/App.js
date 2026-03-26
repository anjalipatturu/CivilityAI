import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import ResultsPage from './pages/ResultsPage';
import BehaviorPage from './pages/BehaviorPage';

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const savedToken = localStorage.getItem('civility_token');
    const savedUser = localStorage.getItem('civility_user');

    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
    setIsLoading(false);
  }, []);

  const handleLogin = (userData, jwtToken) => {
    setUser(userData);
    setToken(jwtToken);
    localStorage.setItem('civility_token', jwtToken);
    localStorage.setItem('civility_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('civility_token');
    localStorage.removeItem('civility_user');
  };

  if (isLoading) {
    return (
      <div className="spinner-overlay">
        <div className="spinner"></div>
        <p className="spinner-text">Loading Civility.ai...</p>
      </div>
    );
  }

  return (
    <Router>
      <div className="app">
        {user && <Navbar user={user} onLogout={handleLogout} />}
        <Routes>
          <Route
            path="/login"
            element={
              user ? <Navigate to="/home" /> : <LoginPage onLogin={handleLogin} />
            }
          />
          <Route
            path="/home"
            element={
              user ? <HomePage user={user} /> : <Navigate to="/login" />
            }
          />
          <Route
            path="/dashboard"
            element={
              user ? <DashboardPage user={user} token={token} /> : <Navigate to="/login" />
            }
          />
          <Route
            path="/results"
            element={
              user ? <ResultsPage user={user} token={token} /> : <Navigate to="/login" />
            }
          />
          <Route
            path="/behavior"
            element={
              user ? <BehaviorPage user={user} token={token} /> : <Navigate to="/login" />
            }
          />
          <Route path="/" element={<Navigate to={user ? "/home" : "/login"} />} />
          <Route path="*" element={<Navigate to={user ? "/home" : "/login"} />} />
        </Routes>
        <ToastContainer
          position="bottom-right"
          autoClose={4000}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme="dark"
        />
      </div>
    </Router>
  );
}

export default App;
