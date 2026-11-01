
import { useCallback, useEffect, useRef, useState } from 'react';
import './App.css';

// Uses the Vite proxy configured in vite.config.js.
const API = '/api';

const features = [
  { icon: '◎', title: 'Eye Control', desc: 'Move cursor with your eyes' },
  { icon: '⌁', title: 'Blink Click', desc: 'Click with a blink' },
  { icon: '▣', title: 'Screenshot', desc: 'Capture using a long blink' },
  { icon: '♫', title: 'Voice Typing', desc: 'Type using voice commands' },
  { icon: '▰', title: 'File Control', desc: 'Create files using voice' },
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
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const frameTimerRef = useRef(null);
  const sendingRef = useRef(false);
  const mountedRef = useRef(true);

  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [engineMessage, setEngineMessage] = useState('');
  const [activeNav, setActiveNav] = useState('Home');
  const [enabled, setEnabled] = useState(features.map(() => true));
  const [faceDetected, setFaceDetected] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [lastVoiceText, setLastVoiceText] = useState('');
  const [typingMode, setTypingMode] = useState(false);
  const [cursorLocked, setCursorLocked] = useState(false);

  // Stop webcam and frame processing.
  const stopCameraTracks = useCallback(() => {
    if (frameTimerRef.current) {
      clearInterval(frameTimerRef.current);
      frameTimerRef.current = null;
    }

    sendingRef.current = false;

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraOn(false);
    setFaceDetected(false);
  }, []);

  // Read backend and engine status.
  const checkStatus = useCallback(async () => {
    try {
      const [serverResponse, processResponse] = await Promise.all([
        fetch(`${API}/status`),
        fetch(`${API}/eyevox/status`)
      ]);

      if (!serverResponse.ok || !processResponse.ok) {
        throw new Error('Backend connection failed');
      }

      const serverData = await serverResponse.json();
      const processData = await processResponse.json();

      if (!mountedRef.current) return;

      setConnected(serverData.status === 'connected');
      setRunning(processData.running === true);
      setEngineMessage(processData.message || '');
      setVoiceAvailable(processData.voice_available === true);
      setLastVoiceText(processData.last_voice_text || '');
      setTypingMode(processData.typing_mode === true);
      setCursorLocked(processData.cursor_locked === true);

      if (!processData.running && streamRef.current) {
        stopCameraTracks();
      }
    } catch (error) {
      if (mountedRef.current) {
        setConnected(false);
        setRunning(false);
      }
    }
  }, [stopCameraTracks]);

  useEffect(() => {
    mountedRef.current = true;

    checkStatus();

    const timer = setInterval(checkStatus, 2000);

    return () => {
      mountedRef.current = false;
      clearInterval(timer);
      stopCameraTracks();
    };
  }, [checkStatus, stopCameraTracks]);

  // Send webcam frames to Python. No landmark dots are drawn.
  const sendFrame = useCallback(async () => {
    const video = videoRef.current;

    if (
      !video ||
      video.readyState < 2 ||
      sendingRef.current ||
      !running
    ) {
      return;
    }

    sendingRef.current = true;

    try {
      const width = 640;
      const height =
        Math.round((video.videoHeight / video.videoWidth) * width) || 480;

      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = width;
      tempCanvas.height = height;

      const ctx = tempCanvas.getContext('2d');

      if (!ctx) return;

      ctx.drawImage(video, 0, 0, width, height);

      const blob = await new Promise(resolve => {
        tempCanvas.toBlob(resolve, 'image/jpeg', 0.72);
      });

      if (!blob) return;

      const response = await fetch(`${API}/eyevox/frame`, {
        method: 'POST',
        headers: {
          'Content-Type': 'image/jpeg'
        },
        body: blob
      });

      const data = await response.json();

      if (!response.ok || data.success === false) {
        throw new Error(data.message || 'Frame processing failed');
      }

      setFaceDetected(data.face_detected === true);

      if (data.last_voice_text) {
        setLastVoiceText(data.last_voice_text);
      }

      if (data.message) {
        setEngineMessage(data.message);
      }
    } catch (error) {
      setMessage(error.message || 'Camera frame error');
    } finally {
      sendingRef.current = false;
    }
  }, [running]);

  // Start camera and Python engine.
  const startSystem = async () => {
    if (!connected || busy || running) return;

    setBusy(true);
    setMessage('');

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Browser camera access is unavailable');
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false
      });

      streamRef.current = stream;

      if (!videoRef.current) {
        throw new Error('Camera preview element is unavailable');
      }

      videoRef.current.srcObject = stream;
      await videoRef.current.play();

      const response = await fetch(`${API}/eyevox/start`, {
        method: 'POST'
      });

      const data = await response.json();

      if (!response.ok || data.success === false) {
        throw new Error(data.message || 'Could not start EYEVOX');
      }

      setRunning(true);
      setCameraOn(true);
      setMessage(data.message || 'EYEVOX started');
      setEngineMessage('EYEVOX is running');
    } catch (error) {
      stopCameraTracks();
      setRunning(false);

      setMessage(
        error.name === 'NotAllowedError'
          ? 'Camera permission denied. Allow camera access in browser settings.'
          : error.message || 'Could not start EYEVOX'
      );
    } finally {
      setBusy(false);
    }
  };

  // Send frames continuously while the system is active.
  useEffect(() => {
    if (running && cameraOn) {
      frameTimerRef.current = setInterval(sendFrame, 150);

      return () => {
        if (frameTimerRef.current) {
          clearInterval(frameTimerRef.current);
          frameTimerRef.current = null;
        }
      };
    }
  }, [running, cameraOn, sendFrame]);

  // Stop Python engine and webcam.
  const stopSystem = async () => {
    if (busy) return;

    setBusy(true);
    setMessage('');

    try {
      const response = await fetch(`${API}/eyevox/stop`, {
        method: 'POST'
      });

      const data = await response.json();

      if (!response.ok || data.success === false) {
        throw new Error(data.message || 'Could not stop EYEVOX');
      }

      setRunning(false);
      stopCameraTracks();
      setMessage(data.message || 'EYEVOX stopped');
      setEngineMessage('EYEVOX is stopped');
    } catch (error) {
      setMessage(error.message || 'Stop request failed');
    } finally {
      setBusy(false);
    }
  };

  const toggleFeature = index => {
    setEnabled(current =>
      current.map((value, i) => (i === index ? !value : value))
    );
  };

  const navItems = [
    { icon: '⌂', label: 'Home' },
    { icon: '⚙', label: 'Settings' },
    { icon: '▥', label: 'Features' },
    { icon: 'ⓘ', label: 'About' },
    { icon: '?', label: 'Help' }
  ];

  const navigate = label => {
    setActiveNav(label);

    if (label === 'Home') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (label === 'Features') {
      document
        .getElementById('features')
        ?.scrollIntoView({ behavior: 'smooth' });
    } else {
      setMessage(`${label} section is not configured yet.`);
    }
  };

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <a
          className="sidebar-brand"
          href="#home"
          onClick={() => navigate('Home')}
        >
          <span className="sidebar-logo"><EyeLogo /></span>
          <span>EYEVOX</span>
        </a>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="sidebar-nav">
          {navItems.map(item => (
            <button
              key={item.label}
              className={`nav-item ${
                activeNav === item.label ? 'selected' : ''
              }`}
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

        <div className="sidebar-version">EYEVOX · VERSION 1.0</div>
      </aside>

      <main className="main-area" id="home">
        <header className="topbar">
          <div className="brand">
            <div className="brand-symbol"><EyeLogo /></div>
            <div className="brand-copy">
              <h1>EYEVOX</h1>
              <p>Technology for more inclusive tomorrow</p>
            </div>
          </div>

          <div className="topbar-center">
            <span>See</span><i>·</i><span>Speak</span><i>·</i>
            <span>Control</span><span className="header-heart">♡</span>
          </div>

          <div className="topbar-right">
            <div className="connection-indicator">
              <i className={connected ? 'green' : 'red'} />
              {connected ? 'Helper Connected' : 'Disconnected'}
            </div>
            <div className="profile-icon">E</div>
          </div>
        </header>

        <section className="dashboard-grid">
          <div className="left-column">
            <section className="camera-card">
              <div className="card-heading">
                <h2>
                  <span className="heading-icon">▣</span>
                  Live Camera Feed
                </h2>

                <span className="camera-status">
                  <i className={cameraOn ? 'green' : 'gray'} />
                  {cameraOn
                    ? faceDetected
                      ? 'Face Detected'
                      : 'Camera Active'
                    : 'Camera Off'}
                </span>
              </div>

              <div className="camera-preview eyevox-camera-preview">
                <video
                  ref={videoRef}
                  className="eyevox-video"
                  autoPlay
                  playsInline
                  muted
                />

                {!cameraOn && (
                  <div className="camera-placeholder">
                    <h3>Camera Preview</h3>
                    <p>
                      Press Start System to allow camera access and begin
                      tracking.
                    </p>
                  </div>
                )}

                <span className="camera-overlay">
                  {cameraOn ? 'LIVE CAMERA' : 'SYSTEM STANDBY'}
                </span>
              </div>

              <div className="camera-controls">
                <button
                  className="start-system"
                  onClick={startSystem}
                  disabled={busy || running || !connected}
                >
                  <span>▶</span>
                  <div>{busy ? 'Please wait' : 'Start'}<br />System</div>
                </button>

                <button
                  className="stop-system"
                  onClick={stopSystem}
                  disabled={busy || !running}
                >
                  <span>■</span>
                  <div>Stop<br />System</div>
                </button>

                <button
                  className="settings-system"
                  onClick={() => navigate('Settings')}
                >
                  <span>⚙</span>
                  <div>Settings</div>
                </button>
              </div>

              {message && <div className="system-message">{message}</div>}
              {engineMessage && (
                <div className="system-message">{engineMessage}</div>
              )}
            </section>
          </div>

          <div className="right-column">
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
                  ['◎', 'Eye Tracking', running && faceDetected],
                  ['♫', 'Voice Control', running && voiceAvailable],
                  ['▣', 'Camera', cameraOn],
                  ['♬', 'Microphone', voiceAvailable]
                ].map(([icon, title, active]) => (
                  <div className="status-tile" key={title}>
                    <span className="status-icon">{icon}</span>
                    <strong>{title}</strong>
                    <small>
                      <i className={active ? 'green' : 'gray'} />
                      {active ? 'Active' : 'Standby'}
                    </small>
                  </div>
                ))}
              </div>
            </section>

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
                <p>{lastVoiceText || 'No commands recorded yet'}</p>
                <small>
                  {lastVoiceText
                    ? 'Latest recognized voice input'
                    : 'Recognized commands will appear here.'}
                </small>
              </div>
            </section>

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
                {lastVoiceText ||
                  (running
                    ? 'Waiting for voice input...'
                    : 'Voice recognition inactive')}
              </p>

              <small className="recognition-status">
                <i className={running && voiceAvailable ? 'green' : 'gray'} />
                {running && voiceAvailable
                  ? 'Voice listener started'
                  : 'Waiting for activation'}
              </small>

              {running && (
                <small className="recognition-status">
                  Typing mode: {typingMode ? 'ON' : 'OFF'} · Cursor:{' '}
                  {cursorLocked ? 'LOCKED' : 'UNLOCKED'}
                </small>
              )}
            </section>
          </div>
        </section>

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
                <div className="feature-tile-icon">{feature.icon}</div>
                <h3>{feature.title}</h3>
                <p>{feature.desc}</p>

                <button
                  className={`toggle ${enabled[index] ? 'on' : ''}`}
                  onClick={() => toggleFeature(index)}
                  aria-label={`Toggle ${feature.title}`}
                  aria-pressed={enabled[index]}
                >
                  <span />
                </button>
              </article>
            ))}
          </div>
        </section>

        <footer className="dashboard-footer">
          <span>EYEVOX · Technology for more inclusive tomorrow</span>
          <span>Local Windows Application</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
