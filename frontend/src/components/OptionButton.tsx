import './OptionButton.css';

interface OptionButtonProps {
  emoji: string;
  label: string;
  selected: boolean;
  onClick: () => void;
}

export function OptionButton({ emoji, label, selected, onClick }: OptionButtonProps) {
  return (
    <button
      className={`option-btn ${selected ? 'option-btn--selected' : ''}`}
      onClick={onClick}
      type="button"
    >
      <span className="option-btn__emoji">{emoji}</span>
      <span className="option-btn__label">{label}</span>
      {selected && (
        <span className="option-btn__check">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </span>
      )}
    </button>
  );
}
