import "./WelcomeScreen.css";

interface WelcomeScreenProps {
  onStart: () => void;
}

export function WelcomeScreen({ onStart }: WelcomeScreenProps) {
  return (
    <div className="welcome" id="welcome-screen">
      <div className="welcome__content">
        <h2 className="welcome__heading font-display">
          Your personal concierge
        </h2>
        <p className="welcome__description">
          Tell us what you love and we'll craft the perfect day.
        </p>
        <button className="welcome__cta" onClick={onStart} id="get-started-btn">
          ✨ Let's plan your day
        </button>
      </div>
    </div>
  );
}
