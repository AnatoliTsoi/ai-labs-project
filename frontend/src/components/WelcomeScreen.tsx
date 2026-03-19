import './WelcomeScreen.css';

interface WelcomeScreenProps {
  onStart: () => void;
}

export function WelcomeScreen({ onStart }: WelcomeScreenProps) {
  return (
    <div className="welcome" id="welcome-screen">
      <div className="welcome__content">
        <div className="welcome__icon">
          <img
            src="/strawberry_logo_footer.svg"
            alt="Concierge"
            width="72"
            height="72"
          />
        </div>

        <h2 className="welcome__heading font-display">
          Your personal concierge
        </h2>
        <p className="welcome__description">
          Tell us what you love and we'll craft the perfect day —
          the best restaurants, hidden gems, and a route that just flows.
        </p>

        <button
          className="welcome__cta"
          onClick={onStart}
          id="get-started-btn"
        >
          ✨ Let's plan your day
        </button>

        <p className="welcome__hint">Takes about 30 seconds</p>
      </div>
    </div>
  );
}
