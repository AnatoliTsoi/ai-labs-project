import './Header.css';

interface HeaderProps {
  onNewChat: () => void;
}

export function Header({ onNewChat }: HeaderProps) {
  return (
    <header className="header glass" id="app-header">
      <div className="header__inner">
        <div className="header__brand">
          <div className="header__logo">
            <img
              src="/strawberry_logo_footer.svg"
              alt="Concierge logo"
              width="32"
              height="32"
            />
          </div>
          <div className="header__text">
            <h1 className="header__title">Concierge</h1>
            <span className="header__subtitle">AI Travel Companion</span>
          </div>
        </div>

        <div className="header__actions">
          <div className="header__status">
            <span className="header__status-dot" />
            <span className="header__status-text">Online</span>
          </div>
          <button
            className="header__new-chat"
            onClick={onNewChat}
            title="Start new conversation"
            id="new-chat-btn"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}
