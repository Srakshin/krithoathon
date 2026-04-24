import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';

export default function Auth() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const navigate = useNavigate();
  const location = useLocation();
  const isSignUp = location.pathname === '/signup';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isSignUp) {
        const { error } = await supabase.auth.signUp({
          email,
          password,
        });
        if (error) throw error;
        alert('Check your email for the login link!');
        navigate('/login');
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
      <div className="bg-grid"></div>
      <div className="bg-glow"></div>

      <div className="glass-panel" style={{ padding: '3rem', width: '100%', maxWidth: '400px', borderRadius: '24px' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <Link to="/" className="logo" style={{ justifyContent: 'center', marginBottom: '1rem' }}>
              <span className="logo-icon"><i className="ph ph-hexagon"></i></span>
              Morning Pulse
          </Link>
          <h2 style={{ fontFamily: 'var(--font-heading)' }}>
            {isSignUp ? 'Create an Account' : 'Welcome Back'}
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            {isSignUp ? 'Join the future of intelligence.' : 'Enter your credentials to continue.'}
          </p>
        </div>

        {error && (
          <div style={{ background: 'rgba(255,50,50,0.1)', border: '1px solid rgba(255,50,50,0.3)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', color: '#ffaaaa', fontSize: '0.9rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Email</label>
            <input 
              type="email" 
              className="hero-input" 
              style={{ padding: '0.8rem 1rem', width: '100%', border: '1px solid var(--border-light)', borderRadius: '12px', background: 'rgba(255,255,255,0.05)' }}
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Password</label>
            <input 
              type="password" 
              className="hero-input" 
              style={{ padding: '0.8rem 1rem', width: '100%', border: '1px solid var(--border-light)', borderRadius: '12px', background: 'rgba(255,255,255,0.05)' }}
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn-primary" style={{ justifyContent: 'center', marginTop: '1rem', width: '100%' }} disabled={loading}>
            {loading ? 'Processing...' : (isSignUp ? 'Sign Up' : 'Log In')}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '2rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          {isSignUp ? (
            <>Already have an account? <Link to="/login" style={{ color: 'var(--accent-cyan)' }}>Log in</Link></>
          ) : (
            <>Don't have an account? <Link to="/signup" style={{ color: 'var(--accent-cyan)' }}>Sign up</Link></>
          )}
        </div>
      </div>
    </div>
  );
}
