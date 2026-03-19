import "./Header.css";

export function Header() {
  return (
    <header className="header glass" id="app-header">
      <div className="header__inner">
        <div className="header__brand">
          <div className="header__logo">
            <img
              src="/strawberry_logo_footer.svg"
              alt="Concierge logo"
              width="150"
              height="150"
            />
          </div>
          <div className="header__text">
            <h1 className="header__title">Concierge</h1>
          </div>
        </div>

        <div className="header__actions">
          <div className="header__status">
            <span className="header__status-dot" />
            <span className="header__status-text">Online</span>
          </div>
        </div>
      </div>
    </header>
  );
}
