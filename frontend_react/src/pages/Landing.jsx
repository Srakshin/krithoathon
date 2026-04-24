import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function Landing() {
  useEffect(() => {
    // Interactive Spotlight on Cards
    const interactiveCards = document.querySelectorAll('.interactive-card');
    
    const handleMouseMove = (e) => {
        const card = e.currentTarget;
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
    };

    interactiveCards.forEach(card => card.addEventListener('mousemove', handleMouseMove));

    // Scroll Reveal Animation using Intersection Observer
    const revealElements = document.querySelectorAll('.scroll-reveal');
    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15, rootMargin: "0px 0px -50px 0px" });

    revealElements.forEach(el => revealObserver.observe(el));

    return () => {
      interactiveCards.forEach(card => card.removeEventListener('mousemove', handleMouseMove));
      revealObserver.disconnect();
    };
  }, []);

  return (
    <>
      {/* Background grid */}
      <div className="bg-grid"></div>
      <div className="bg-glow"></div>

      {/* Navigation */}
      <nav className="navbar scrolled">
          <div className="nav-container">
              <Link to="/" className="logo">
                  <span className="logo-icon"><i className="ph ph-hexagon"></i></span>
                  Horizon
              </Link>
              <div className="nav-links">
                  <a href="#features">Features</a>
                  <a href="#docs">Documentation</a>
                  <a href="#pricing">Pricing</a>
              </div>
              <div className="nav-actions">
                  <Link to="/login" className="btn-ghost">Log in</Link>
                  <Link to="/signup" className="btn-primary">Get Started <i className="ph ph-arrow-right"></i></Link>
              </div>
          </div>
      </nav>

      {/* Hero Section */}
      <header className="hero">
          <div className="hero-content">
              <div className="pill-badge">
                  <span className="pulse-dot"></span>
                  Morning Pulse is now live
              </div>
              <h1 className="hero-title">
                  Intelligence at the speed of <br />
                  <span className="text-gradient">pure thought.</span>
              </h1>
              <p className="hero-subtitle">
                  The world-class AI ecosystem that combines bold aesthetics with unmatched analysis. Build, iterate, and deploy instantly.
              </p>
              
              <div className="hero-search-container">
                  <i className="ph ph-magnifying-glass search-icon"></i>
                  <input type="text" className="hero-input" placeholder="What are we researching today?" />
                  <button className="btn-primary input-btn">Generate</button>
              </div>
          </div>
          
          <div className="hero-visual scroll-reveal">
              <div className="glass-panel main-dashboard-mockup">
                  <div className="panel-header">
                      <div className="window-controls">
                          <span></span><span></span><span></span>
                      </div>
                      <div className="window-title">morning-pulse / daily-brief</div>
                  </div>
                  <div className="panel-body">
                      <div className="mockup-sidebar">
                          <div className="skeleton-line shimmer w-100"></div>
                          <div className="skeleton-line shimmer w-80"></div>
                          <div className="skeleton-line shimmer w-60"></div>
                          <div className="skeleton-line shimmer w-80"></div>
                      </div>
                      <div className="mockup-content">
                          <div className="skeleton-box shimmer mb-md"></div>
                          <div className="dashboard-grid">
                              <div className="skeleton-card shimmer"></div>
                              <div className="skeleton-card shimmer"></div>
                              <div className="skeleton-card shimmer"></div>
                          </div>
                      </div>
                  </div>
              </div>
          </div>
      </header>

      {/* Feature Section */}
      <section id="features" className="features-section">
          <div className="section-header scroll-reveal">
              <div className="section-label">Features</div>
              <h2>Everything you need. <br />Nothing you don't.</h2>
          </div>

          <div className="bento-grid">
              <div className="bento-card bento-large scroll-reveal interactive-card">
                  <div className="spotlight"></div>
                  <div className="card-content">
                      <div className="card-icon"><i className="ph ph-cpu"></i></div>
                      <h3>Next-Gen AI Filtering</h3>
                      <p>Harness the power of fluid micro-animations and deep predictive routing. Your users won't just use your app, they'll feel it.</p>
                  </div>
                  <div className="card-visual visual-glow-1">
                      <div className="floating-orb orb-1"></div>
                      <div className="floating-orb orb-2"></div>
                  </div>
              </div>

              <div className="bento-card scroll-reveal interactive-card">
                  <div className="spotlight"></div>
                  <div className="card-content">
                      <div className="card-icon"><i className="ph ph-rocket-launch"></i></div>
                      <h3>Instant Intelligence</h3>
                      <p>Push to global edge networks in milliseconds. Zero config required.</p>
                  </div>
              </div>

              <div className="bento-card scroll-reveal interactive-card">
                  <div className="spotlight"></div>
                  <div className="card-content">
                      <div className="card-icon"><i className="ph ph-shield-check"></i></div>
                      <h3>Engineered for Scale</h3>
                      <p>Enterprise-grade security natively baked into the foundation.</p>
                  </div>
              </div>
          </div>
      </section>

      <section className="onboarding-section">
          <div className="onboarding-container scroll-reveal interactive-card glass-panel">
              <div className="spotlight"></div>
              <div className="onboarding-content">
                  <h2>Ready to redefine your workflow?</h2>
                  <p>Join the future of insight creation. Check out your morning pulse now.</p>
                  <div className="onboarding-actions">
                      <Link to="/signup" className="btn-primary btn-large">Create Account</Link>
                  </div>
              </div>
              <div className="onboarding-bg-effect"></div>
          </div>
      </section>

      <footer className="footer">
          <div className="footer-container">
              <div className="footer-brand">
                  <Link to="/" className="logo">
                      <span className="logo-icon"><i className="ph ph-hexagon"></i></span>
                      Morning Pulse
                  </Link>
                  <p className="footer-tagline">Crafted with precision.</p>
              </div>
              <div className="footer-links">
                  <div className="link-column">
                      <h4>Product</h4>
                      <Link to="/signup">Get Started</Link>
                      <Link to="/login">Sign In</Link>
                  </div>
              </div>
          </div>
          <div className="footer-bottom">
              <p>&copy; 2026 Morning Pulse. All rights reserved.</p>
          </div>
      </footer>
    </>
  );
}
