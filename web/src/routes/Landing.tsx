import { Link } from 'react-router-dom';
import './Landing.css';
import { LineageIllustration } from '../components/LineageIllustration';
import { ThemeToggle } from '../components/ThemeToggle';

const FEATURES = [
  {
    title: 'Lineage-aware retrieval',
    body: 'Every answer is resolved against the full amendment and supersession chain, not just the most recent document in the index.',
  },
  {
    title: 'Clause-level citations',
    body: 'Answers cite the exact clause, not the document. Click through to the source text and its regulator reference.',
  },
  {
    title: 'Bring your own model',
    body: 'Connect the chat model and embedding provider you already have credentials for. Amend never holds a default key on your behalf.',
  },
];

export function Landing() {
  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-header-inner">
          <span className="landing-logo">Amend</span>
          <nav className="landing-nav">
            <a href="#product">Product</a>
            <a href="#docs">Docs</a>
          </nav>
          <ThemeToggle />
          <Link to="/login" className="landing-cta-ghost">
            Log in
          </Link>
        </div>
      </header>

      <main>
        <section className="landing-hero">
          <div className="landing-hero-copy">
            <h1>Ask what the regulation actually says.</h1>
            <p className="landing-subhead">
              Query public RBI and SEBI publications with clause-level citations, grounded in the
              graph of amendments and supersessions between them.
            </p>
            <Link to="/login" className="landing-cta">
              Get started
            </Link>
          </div>
          <div className="landing-hero-illustration">
            <LineageIllustration />
          </div>
        </section>

        <section id="product" className="landing-features">
          {FEATURES.map((feature) => (
            <article key={feature.title} className="landing-feature">
              <h2>{feature.title}</h2>
              <p>{feature.body}</p>
            </article>
          ))}
        </section>

        <section className="landing-cta-band">
          <h2>Start asking questions grounded in the actual regulatory text.</h2>
          <Link to="/login" className="landing-cta">
            Get started
          </Link>
        </section>
      </main>

      <footer className="landing-footer">
        <span>Amend</span>
        <span className="landing-footer-muted">Graph-grounded regulatory research</span>
      </footer>
    </div>
  );
}
