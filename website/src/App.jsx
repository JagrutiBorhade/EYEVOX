import { useCallback, useEffect, useRef, useState } from 'react';
import './App.css';

const API = 'http://127.0.0.1:5000';

const features = [
  { icon: '◎', title: 'Eye Control', desc: 'Move cursor with your eyes' },
  { icon: '⌁', title: 'Blink Click', desc: 'Click with a blink (0.15s)' },
  { icon: '▣', title: 'Screenshot', desc: 'Capture using a long blink' },
  { icon: '♫', title: 'Voice Assistant', desc: 'Open websites, dictate text and control apps by voice' },
  { icon: '▰', title: 'File Control', desc: 'Create, open and manage files' },
  { icon: '⊞', title: 'Smart App Control', desc: 'Launch WhatsApp, Google, YouTube and desktop apps' }
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
      <circle
        cx="32"
        cy="22"
        r="11"
        stroke="currentColor"
        strokeWidth="3"
      />
      <circle cx="32" cy="22" r="4" fill="currentColor" />
    </svg>
  );
}

function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const frameTimerRef = useRef(null);
  const sendingRef = useRef(false);
  const mountedRef = useRef(true);

  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [activeNav, setActiveNav] = useState('Home');
  const [enabled, setEnabled] = useState(features.map(() => true));
  const [faceDetected, setFaceDetected] = useState(false);
  const [lastVoiceText, setLastVoiceText] = useState('');
  const [engineMessage, setEngineMessage] = useState('');

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

    const canvas = canvasRef.current;

    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx?.clearRect(0, 0, canvas.width, canvas.height);
    }
  }, []);

  const checkStatus = useCallback(async () => {
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

      if (!mountedRef.current) return;

      setConnected(serverData.status === 'connected');
      setRunning(processData.running === true);
      setEngineMessage(processData.message || '');
      setLastVoiceText(processData.last_voice_text || '');

      if (processData.running !== true && streamRef.current) {
        stopCameraTracks();
      }
    } catch {
      if (mountedRef.current) {
        setConnected(false);
        setRunning(false);
      }
    }
  }, [stopCameraTracks]);

  useEffect(() => {
    mountedRef.current = true;

    checkStatus();

    const timer = setInterval(checkStatus, 3000);

    return () => {
      mountedRef.current = false;
      clearInterval(timer);
      stopCameraTracks();
    };
  }, [checkStatus, stopCameraTracks]);

  const drawLandmarks = useCallback((payload, width, height) => {
    const canvas = canvasRef.current;

    if (!canvas) return;

    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');

    ctx.clearRect(0, 0, width, height);

    const points = payload.landmarks || [];

    if (!payload.face_detected || points.length === 0) {
      setFaceDetected(payload.face_detected === true);
      return;
    }

    setFaceDetected(true);

    ctx.fillStyle = '#35e0a1';

    for (let i = 0; i < points.length; i++) {
      const x = (1 - points[i].x) * width;
      const y = points[i].y * height;

      ctx.beginPath();
      ctx.arc(
        x,
        y,
        i >= 468 ? 2.8 : 1.35,
        0,
        Math.PI * 2
      );
      ctx.fill();
    }
  }, []);

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
        Math.round(
          (video.videoHeight / video.videoWidth) * width
        ) || 480;

      const temp = document.createElement('canvas');

      temp.width = width;
      temp.height = height;

      const ctx = temp.getContext('2d');

      ctx.drawImage(video, 0, 0, width, height);

      const blob = await new Promise(resolve =>
        temp.toBlob(resolve, 'image/jpeg', 0.72)
      );

      if (!blob) return;

      const response = await fetch(`${API}/eyevox/frame`, {
        method: 'POST',
        headers: {
          'Content-Type': 'image/jpeg'
        },
        body: blob
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));

        throw new Error(
          errorData.message || 'Frame processing failed'
        );
      }

      const data = await response.json();

      if (!mountedRef.current) return;

      drawLandmarks(data, width, height);

      setFaceDetected(data.face_detected === true);

      if (data.last_voice_text) {
        setLastVoiceText(data.last_voice_text);
      }

      if (data.message) {
        setEngineMessage(data.message);
      }
    } catch (error) {
      if (mountedRef.current) {
        setMessage(error.message);
      }
    } finally {
      sendingRef.current = false;
    }
  }, [running, drawLandmarks]);

  const startSystem = async () => {
    if (!connected || busy) return;

    setBusy(true);
    setMessage('');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      const response = await fetch(`${API}/eyevox/start`, {
        method: 'POST'
      });

      const data = await response.json();

      if (!response.ok || data.success === false) {
        throw new Error(
          data.message || 'Could not start EYEVOX'
        );
      }

      setRunning(true);
      setCameraOn(true);

      setMessage(
        data.message || 'Camera and EYEVOX started'
      );
    } catch (error) {
      stopCameraTracks();
      setRunning(false);

      setMessage(
        error.name === 'NotAllowedError'
          ? 'Camera permission was denied. Allow camera access in your browser.'
          : error.message || 'Could not start camera'
      );
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (running && cameraOn) {
      frameTimerRef.current = setInterval(sendFrame, 100);

      return () => {
        if (frameTimerRef.current) {
          clearInterval(frameTimerRef.current);
        }

        frameTimerRef.current = null;
      };
    }
  }, [running, cameraOn, sendFrame]);

  const stopSystem = async () => {
    setBusy(true);
    setMessage('');

    try {
      const response = await fetch(`${API}/eyevox/stop`, {
        method: 'POST'
      });

      const data = await response.json();

      if (!response.ok || data.success === false) {
        throw new Error(
          data.message || 'Could not stop EYEVOX'
        );
      }

      setRunning(false);
      stopCameraTracks();

      setMessage(data.message || 'EYEVOX stopped');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };

  const toggleFeature = index => {
    setEnabled(current =>
      current.map((value, i) =>
        i === index ? !value : value
      )
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
      setMessage(
        `${label} section will be configured in a future update.`
      );
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

        <div className="sidebar-version">
          EYEVOX · VERSION 1.0
        </div>
      </aside>

      <main className="main-area" id="home">
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

        <section className="dashboard-grid">
          <div className="left-column">
            <section className="camera-card">
              <div className="card-heading">
                <h2>
                  <span className="heading-icon">▣</span>
                  Live Camera Feed
                </h2>

                <span className="camera-status">
                  <i className={cameraOn ? 'green' : 'gray'}></i>
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

                <canvas
                  ref={canvasRef}
                  className="eyevox-landmarks"
                />

                {!cameraOn && (
                  <div className="camera-placeholder">
                    <h3>Camera Preview</h3>
                    <p>
                      Press Start System to allow camera access
                      and begin tracking.
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
                  <div>
                    {busy ? 'Please wait' : 'Start'}
                    <br />
                    System
                  </div>
                </button>

                <button
                  className="stop-system"
                  onClick={stopSystem}
                  disabled={busy || !running}
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

              {engineMessage && (
                <div className="system-message">
                  {engineMessage}
                </div>
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
                  ['♫', 'Voice Control', running],
                  ['▣', 'Camera', cameraOn],
                  ['♬', 'Microphone', running]
                ].map(([icon, title, active]) => (
                  <div className="status-tile" key={title}>
                    <span className="status-icon">{icon}</span>
                    <strong>{title}</strong>

                    <small>
                      <i className={active ? 'green' : 'gray'}></i>
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

                <p>
                  {lastVoiceText || 'No commands recorded yet'}
                </p>

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
                <i className={running ? 'green' : 'gray'}></i>
                {running
                  ? 'Voice listener started'
                  : 'Waiting for activation'}
              </small>
            </section>

            <section className="info-card voice-commands-card">
              <div className="card-heading">
                <h2>
                  <span className="heading-icon">✦</span>
                  Voice Command Ideas
                </h2>
                <span className="small-caption">HANDS-FREE</span>
              </div>

              <div className="voice-command-list">
                <p>
                  <strong>Websites:</strong> “Open WhatsApp”,
                  “Open Google”, “Open YouTube”, “Open Gmail”,
                  “Open ChatGPT”, “Open Instagram”.
                </p>

                <p>
                  <strong>Search:</strong> “Search Google for Python
                  tutorials”, “Search YouTube for eye tracking”.
                </p>

                <p>
                  <strong>WhatsApp:</strong> “Open WhatsApp chat”
                  followed by a phone number. “WhatsApp message”
                  followed by a number and “saying” your message
                  opens a pre-filled chat.
                </p>

                <p>
                  <strong>Dictation:</strong> “Start dictation”,
                  speak your text, then “Stop dictation”. Or say
                  “Type” followed by your sentence.
                </p>

                <p>
                  <strong>Computer:</strong> “Open Notepad”,
                  “Open Calculator”, “Open File Explorer”,
                  “Scroll down”, “Go back”, “Refresh page”,
                  “Close tab”.
                </p>
              </div>
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
                  <span />
                </button>
              </article>
            ))}
          </div>
        </section>

        <footer className="dashboard-footer">
          <span>
            EYEVOX · Technology for more inclusive tomorrow
          </span>
          <span>Local Windows Application</span>
        </footer>
      </main>
    </div>
  );
}

export default App;