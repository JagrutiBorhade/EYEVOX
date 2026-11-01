
import { useEffect, useState } from 'react';
import './App.css';

const API = 'http://127.0.0.1:5000';

const features = [
  { icon: '◎', title: 'Eye Control', desc: 'Move cursor with your eyes' },
  { icon: '⌁', title: 'Blink Click', desc: 'Click with a blink (0.15s)' },
  { icon: '▣', title: 'Screenshot', desc: 'Capture using a long blink' },
  { icon: '♫', title: 'Voice Typing', desc: 'Type using voice commands' },
  { icon: '▰', title: 'File Control', desc: 'Create, open and manage files' },
  { icon: '⊞', title: 'App Control', desc: 'Open or close applications' }
];

function EyeLogo({ className = '' }) {
  return (
    <svg
      className={className}
      viewBox="0 0 64 44"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="EYEVOX logo"
      role="img"
    >
      <path
        d="M3 22C11 9 21 3 32 3C43 3 53 9 61 22C53 35 43 41 32 41C21 41 11 35 3 22Z"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <circle cx="32" cy="22" r="11" stroke="currentColor" strokeWidth="3" />
      <circle cx="32" cy="22" r="4" fill="currentColor" />
    </svg>
  );
}

function App() {
  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [activeNav, setActiveNav] = useState('Home');
  const [enabled, setEnabled] = useState(features.map(() => true));

  useEffect(() => {
    let active = true;

    const checkStatus = async () => {
      try {
        const [serverResponse, processResponse] = await Promise.all([
          fetch(`${API}/status`),
          fetch(`${API}/eyevox/status`)
        ]);

        if (!serverResponse.ok || !processResponse.ok) {
          throw new Error('Connection failed');
        }

        const serverData = await serverResponse.json();
        const processData = await processResponse.json();

        if (active) {
          setConnected(serverData.status === 'connected');
          setRunning(processData.running === true);
        }
      } catch {
        if (active) {
          setConnected(false);
          setRunning(false);
        }
      }
    };

    checkStatus();
    const timer = setInterval(checkStatus, 3000);

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const controlSystem = async (action) => {
    setBusy(true);
    setMessage('');

    try {
      const response = await fetch(`${API}/eyevox/${action}`, {
        method: 'POST'
      });

      const data = await response.json();

      if (!response.ok || data.success === false) {
        throw new Error(data.message || 'Operation failed');
      }

      const statusResponse = await fetch(`${API}/eyevox/status`);

      if (!statusResponse.ok) {
        throw new Error('Could not verify EYEVOX status');
      }

      const statusData = await statusResponse.json();

      setRunning(statusData.running === true);
      setMessage(data.message || `EYEVOX ${action} request completed`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };

  const toggleFeature = (index) => {
    setEnabled(current =>
      current.map((value, i) => i === index ? !value : value)
    );
  };

  const navItems = [
    { icon: '⌂', label: 'Home' },
    { icon: '⚙', label: 'Settings' },
    { icon: '▥', label: 'Features' },
    { icon: 'ⓘ', label: 'About' },
    { icon: '?', label: 'Help' }
  ];

  const navigate = (label) => {
    setActiveNav(label);

    if (label === 'Home') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (label === 'Features') {
      document.getElementById('features')?.scrollIntoView({
        behavior: 'smooth'
      });
    } else {
      setMessage(`${label} section will be configured in a future update.`);
    }
  };

  return (
    <div className="dashboard">

      {/* SIDEBAR */}

      <aside className="sidebar">

        <a
          className="sidebar-brand"
          href="#home"
          onClick={() => navigate('Home')}
        >
          <span className="sidebar-logo">
            <EyeLogo />
          </span>
          <span>EYEVOX</span>
        </a>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="sidebar-nav">
          {navItems.map(item => (
            <button
              key={item.label}
              className={`nav-item ${activeNav === item.label ? 'selected' : ''}`}
              onClick={() => navigate(item.label)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <p>Assistive technology</p>
          <span>ACCESSIBILITY TECHNOLOGY</span>
        </div>

        <div className="sidebar-version">
          EYEVOX · VERSION 1.0
        </div>

      </aside>

      {/* MAIN AREA */}

      <main className="main-area" id="home">

        {/* HEADER */}

        <header className="topbar">

          <div className="brand">

            <div className="brand-symbol">
              <EyeLogo />
            </div>

            <div className="brand-copy">
              <h1>EYEVOX</h1>
              <p>Technology for more inclusive tomorrow</p>
            </div>

          </div>

          <div className="topbar-center">
            <span>See</span>
            <i>·</i>
            <span>Speak</span>
            <i>·</i>
            <span>Control</span>
            <span className="header-heart">♡</span>
          </div>

          <div className="topbar-right">

            <div className="connection-indicator">
              <i className={connected ? 'green' : 'red'}></i>
              {connected ? 'Helper Connected' : 'Disconnected'}
            </div>

            <div className="profile-icon">E</div>

          </div>

        </header>

        {/* DASHBOARD */}

        <section className="dashboard-grid">

          {/* CAMERA */}

          <div className="left-column">

            <section className="camera-card">

              <div className="card-heading">
                <h2>
                  <span className="heading-icon">▣</span>
                  Live Camera Feed
                </h2>

                <span className="camera-status">
                  <i className={running ? 'green' : 'gray'}></i>
                  {running ? 'Process Running' : 'Awaiting Start'}
                </span>
              </div>

              <div className="camera-preview">

                <div className="camera-placeholder">

                  <h3>
                    {running ? 'EYEVOX is running' : 'Camera Preview'}
                  </h3>

                  <p>
                    {running
                      ? 'Check the camera window opened by the Python application.'
                      : 'Start EYEVOX to activate your camera session.'}
                  </p>

                </div>

                <span className="camera-overlay">
                  {running ? 'SESSION ACTIVE' : 'SYSTEM STANDBY'}
                </span>

              </div>

              <div className="camera-controls">

                <button
                  className="start-system"
                  onClick={() => controlSystem('start')}
                  disabled={busy || running || !connected}
                >
                  <span>▶</span>
                  <div>
                    {busy ? 'Please wait' : 'Start'}
                    <br />
                    System
                  </div>
                </button>

                <button
                  className="stop-system"
                  onClick={() => controlSystem('stop')}
                  disabled={busy || !running || !connected}
                >
                  <span>■</span>
                  <div>
                    Stop
                    <br />
                    System
                  </div>
                </button>

                <button
                  className="settings-system"
                  onClick={() => navigate('Settings')}
                >
                  <span>⚙</span>
                  <div>Settings</div>
                </button>

              </div>

              {message && (
                <div className="system-message">
                  {message}
                </div>
              )}

            </section>

          </div>

          {/* RIGHT SIDE */}

          <div className="right-column">

            {/* SYSTEM STATUS */}

            <section className="info-card status-card">

              <div className="card-heading">
                <h2>
                  <span className="heading-icon">⌁</span>
                  System Status
                </h2>
                <span className="small-caption">LIVE CHECK</span>
              </div>

              <div className="status-grid">

                {[
                  ['◎', 'Eye Tracking'],
                  ['♫', 'Voice Control'],
                  ['▣', 'Camera'],
                  ['♬', 'Microphone']
                ].map(([icon, title]) => (
                  <div className="status-tile" key={title}>
                    <span className="status-icon">{icon}</span>
                    <strong>{title}</strong>

                    <small>
                      <i className={running && connected ? 'green' : 'gray'}></i>
                      {running && connected ? 'Process Active' : 'Standby'}
                    </small>
                  </div>
                ))}

              </div>

            </section>

            {/* RECENT COMMANDS */}

            <section className="info-card commands-card">

              <div className="card-heading">
                <h2>
                  <span className="heading-icon">◷</span>
                  Recent Commands
                </h2>
                <span className="small-caption">COMMAND LOG</span>
              </div>

              <div className="command-empty">
                <span>⌁</span>
                <p>No commands recorded yet</p>
                <small>Recognized commands will appear here.</small>
              </div>

            </section>

            {/* VOICE TRANSCRIPT */}

            <section className="info-card transcript-card">

              <div className="card-heading">
                <h2>
                  <span className="heading-icon">♫</span>
                  Voice Transcript
                </h2>
                <span className="small-caption">VOICE INPUT</span>
              </div>

              <div className="voice-visual" aria-hidden="true">
                {Array.from({ length: 35 }, (_, i) => (
                  <span
                    key={i}
                    style={{
                      height: `${10 + ((i * 17 + 11) % 35)}px`
                    }}
                  />
                ))}
              </div>

              <p className="transcript-text">
                {running
                  ? 'Waiting for voice input...'
                  : 'Voice recognition inactive'}
              </p>

              <small className="recognition-status">
                <i className={running ? 'green' : 'gray'}></i>
                {running ? 'Process started' : 'Waiting for activation'}
              </small>

            </section>

          </div>

        </section>

        {/* FEATURES */}

        <section className="features-area" id="features">

          <div className="features-heading">

            <div>
              <span className="section-kicker">
                PERSONALIZE YOUR EXPERIENCE
              </span>
              <h2>Interaction Features</h2>
            </div>

            <span className="feature-count">06 FEATURES</span>

          </div>

          <div className="feature-grid">

            {features.map((feature, index) => (
              <article className="feature-tile" key={feature.title}>

                <div className="feature-tile-icon">
                  {feature.icon}
                </div>

                <h3>{feature.title}</h3>
                <p>{feature.desc}</p>

                <button
                  className={`toggle ${enabled[index] ? 'on' : ''}`}
                  onClick={() => toggleFeature(index)}
                  aria-label={`Toggle ${feature.title}`}
                  aria-pressed={enabled[index]}
                >
                  <span></span>
                </button>

              </article>
            ))}

          </div>

        </section>

        {/* FOOTER */}

        <footer className="dashboard-footer">
          <span>EYEVOX · Technology for more inclusive tomorrow</span>
          <span>Local Windows Application</span>
        </footer>

      </main>

    </div>
  );
}

export default App;
