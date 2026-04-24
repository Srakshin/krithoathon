import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';

export default function Dashboard() {
  const [session, setSession] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        navigate('/login');
      } else {
        setSession(session);
        fetchPulse(session.access_token);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        navigate('/login');
      } else {
        setSession(session);
      }
    });

    return () => subscription.unsubscribe();
  }, [navigate]);

  const fetchPulse = async (token) => {
    try {
      const res = await fetch('http://127.0.0.1:8000/daily-brief', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error('Failed to fetch daily brief');
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="bg-grid"></div>
        <div className="pulse-dot" style={{ width: '20px', height: '20px' }}></div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', paddingTop: '80px', paddingBottom: '4rem' }}>
      <div className="bg-grid"></div>
      
      <nav className="navbar scrolled" style={{ position: 'fixed', top: 0, width: '100%' }}>
          <div className="nav-container">
              <div className="logo">
                  <span className="logo-icon"><i className="ph ph-hexagon"></i></span>
                  Morning Pulse
              </div>
              <div className="nav-actions">
                  <button onClick={handleSignOut} className="btn-ghost">Sign Out</button>
              </div>
          </div>
      </nav>

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 2rem' }}>
        <header style={{ marginBottom: '3rem', paddingTop: '2rem' }}>
          <div className="pill-badge" style={{ marginBottom: '1rem' }}>
            <span className="pulse-dot"></span>
            {data?.date || new Date().toISOString().split('T')[0]}
          </div>
          <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 'clamp(2rem, 4vw, 3rem)' }}>
            Your Daily <span className="text-gradient">Intelligence</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', marginTop: '1rem' }}>
            {data?.greeting || 'Analyzing global markets for your brief...'}
          </p>
        </header>

        {error && (
          <div style={{ background: 'rgba(255,50,50,0.1)', border: '1px solid rgba(255,50,50,0.3)', padding: '1rem', borderRadius: '8px', marginBottom: '2rem', color: '#ffaaaa' }}>
            {error}
          </div>
        )}

        {data && data.categories ? (
            Object.entries(data.categories).map(([category, items]) => (
              <section key={category} style={{ marginBottom: '4rem' }}>
                <h3 style={{ borderBottom: '1px solid var(--border-light)', paddingBottom: '0.8rem', marginBottom: '2rem', color: 'var(--accent-cyan)' }}>
                  {category}
                </h3>
                <div className="bento-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', autoRows: 'min-content' }}>
                  {items.map((item, idx) => (
                    <div key={idx} className="bento-card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
                        <h4 style={{ fontSize: '1.1rem', margin: 0, lineHeight: 1.4 }}>{item.title}</h4>
                      </div>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: 0 }}>
                        {item.summary}
                      </p>
                      <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.05)', padding: '0.2rem 0.6rem', borderRadius: '4px' }}>
                          {item.source || 'Web'}
                        </span>
                        {item.url && (
                          <a href={item.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-cyan)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            Read full <i className="ph ph-arrow-right"></i>
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ))
        ) : (
          !loading && !error && <p>No intelligence briefs generated for today yet.</p>
        )}
      </main>
    </div>
  );
}
