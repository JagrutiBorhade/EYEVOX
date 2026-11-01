import { useState } from "react";
import "./App.css";

function App() {
  const [menuOpen, setMenuOpen] = useState(false);

  const features = [
    {
      icon: "👁️",
      title: "Eye Movement",
      description:
        "Move the mouse pointer naturally using eye movements tracked by your webcam.",
    },
    {
      icon: "😉",
      title: "Blink Detection",
      description:
        "Use intentional blinks to click and interact with your computer.",
    },
    {
      icon: "🎙️",
      title: "Voice Commands",
      description:
        "Speak commands to type text, open applications, and perform supported tasks.",
    },
    {
      icon: "♿",
      title: "Accessible Computing",
      description:
        "Explore hands-free computer interaction designed with accessibility in mind.",
    },
  ];

  return (
    <div className="app">
      <header className="navbar">
        <a className="brand" href="#home">
          <span className="brand-icon">◉</span>
          VisionVoice
        </a>

        <button
          className="menu-toggle"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle navigation"
        >
          ☰
        </button>

        <nav className={menuOpen ? "nav-links open" : "nav-links"}>
          <a href="#home" onClick={() => setMenuOpen(false)}>Home</a>
          <a href="#features" onClick={() => setMenuOpen(false)}>Features</a>
          <a href="#how-it-works" onClick={() => setMenuOpen(false)}>
            How It Works
          </a>
          <a href="#about" onClick={() => setMenuOpen(false)}>About</a>
          <a className="nav-button" href="#download">Get Started</a>
        </nav>
      </header>

      <main>
        <section className="hero" id="home">
          <div className="hero-content">
            <span className="eyebrow">
              TECHNOLOGY FOR INDEPENDENCE
            </span>

            <h1>
              Control your computer.
              <span> On your terms.</span>
            </h1>

            <p>
              Discover a new way to interact with your computer using
              eye movements, intentional blinks, and voice commands.
              Technology should be accessible to everyone.
            </p>

            <div className="hero-actions">
              <a className="primary-button" href="#features">
                Explore Features <span>→</span>
              </a>
              <a className="secondary-button" href="#how-it-works">
                How It Works
              </a>
            </div>

            <div className="hero-note">
              <span className="status-dot" />
              Designed with accessibility in mind
            </div>
          </div>

          <div className="hero-visual">
            <div className="visual-glow" />
            <div className="interface-card">
              <div className="interface-top">
                <div>
                  <span className="mini-label">VISIONVOICE</span>
                  <h3>Assistive Control</h3>
                </div>
                <span className="demo-badge">DEMO UI</span>
              </div>

              <div className="eye-display">
                <div className="eye-ring">
                  <div className="eye-center">
                    <span />
                  </div>
                </div>
                <p>Eye tracking concept</p>
                <span className="tracking-label">ILLUSTRATION ONLY</span>
              </div>

              <div className="control-row">
                <span className="control-icon">👁️</span>
                <div>
                  <strong>Eye tracking</strong>
                  <small>Example interface</small>
                </div>
                <span className="control-arrow">→</span>
              </div>

              <div className="control-row">
                <span className="control-icon">🎙️</span>
                <div>
                  <strong>Voice control</strong>
                  <small>Example interface</small>
                </div>
                <span className="control-arrow">→</span>
              </div>

              <div className="privacy-note">
                <span>🔒</span>
                Local processing depends on your setup
              </div>
            </div>

            <div className="floating-tag tag-one">👁️ Eye interaction</div>
            <div className="floating-tag tag-two">🎙️ Voice input</div>
          </div>
        </section>

        <section className="features section" id="features">
          <div className="section-heading">
            <span className="eyebrow">WHAT IT CAN DO</span>
            <h2>Interaction made more accessible.</h2>
            <p>
              Explore the core capabilities planned for VisionVoice.
              Actual functions depend on the installed helper application.
            </p>
          </div>

          <div className="feature-grid">
            {features.map((feature) => (
              <article className="feature-card" key={feature.title}>
                <div className="feature-icon">{feature.icon}</div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
                <a href="#how-it-works" className="learn-link">
                  Learn more <span>→</span>
                </a>
              </article>
            ))}
          </div>
        </section>

        <section className="how-section section" id="how-it-works">
          <div className="section-heading">
            <span className="eyebrow">SIMPLE BY DESIGN</span>
            <h2>How VisionVoice works</h2>
            <p>
              The website introduces the project. The Windows helper
              performs the actual computer-control tasks locally.
            </p>
          </div>

          <div className="steps-grid">
            <article className="step-card">
              <span className="step-number">01</span>
              <h3>Open the website</h3>
              <p>Learn about the system and read the setup instructions.</p>
            </article>
            <article className="step-card">
              <span className="step-number">02</span>
              <h3>Run the helper</h3>
              <p>Start the Windows application and grant the required permissions.</p>
            </article>
            <article className="step-card">
              <span className="step-number">03</span>
              <h3>Interact hands-free</h3>
              <p>Use supported eye, blink, and voice controls with clear stop controls.</p>
            </article>
          </div>
        </section>

        <section className="about-section section" id="about">
          <div>
            <span className="eyebrow">OUR MISSION</span>
            <h2>Technology should create possibilities.</h2>
          </div>
          <p>
            VisionVoice is an accessibility-focused final-year project
            exploring alternative ways to control a computer. Its goal
            is to help people with limited hand or arm mobility access
            digital tools more independently.
          </p>
        </section>

        <section className="download-section section" id="download">
          <span className="eyebrow">WINDOWS APPLICATION</span>
          <h2>Your hands-free journey starts here.</h2>
          <p>
            The Windows helper is being prepared. A verified download
            will be added after the application is packaged and tested.
          </p>
          <span className="coming-soon">WINDOWS HELPER · COMING SOON</span>
        </section>
      </main>

      <footer className="footer">
        <a className="brand" href="#home">
          <span className="brand-icon">◉</span>
          VisionVoice
        </a>
        <p>Designed for accessibility. Built for independence.</p>
        <a href="#home">Back to top ↑</a>
        <small>VisionVoice · Final-Year Project</small>
      </footer>
    </div>
  );
}

export default App;
