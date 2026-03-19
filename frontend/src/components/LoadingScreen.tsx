import './LoadingScreen.css';

export function LoadingScreen() {
  return (
    <div className="loading-screen" id="loading-screen">
      <div className="loading-screen__content">
        <div className="loading-screen__logo">
          <img
            src="/strawberry_logo_footer.svg"
            alt="Loading"
            width="56"
            height="56"
            className="loading-screen__img"
          />
        </div>

        <div className="loading-screen__spinner">
          <div className="loading-screen__ring" />
        </div>

        <h3 className="loading-screen__title font-display">
          Crafting your perfect day...
        </h3>
        <p className="loading-screen__text">
          Discovering the best places, checking opening hours, and building
          an optimized route just for you.
        </p>

        <div className="loading-screen__steps">
          <div className="loading-screen__step loading-screen__step--done">
            <span className="loading-screen__step-icon">✓</span>
            Analyzing preferences
          </div>
          <div className="loading-screen__step loading-screen__step--active">
            <span className="loading-screen__step-icon">⟳</span>
            Finding matching places
          </div>
          <div className="loading-screen__step">
            <span className="loading-screen__step-icon">○</span>
            Building your route
          </div>
        </div>
      </div>
    </div>
  );
}
