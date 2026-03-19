import './ProgressBar.css';

interface ProgressBarProps {
  currentStep: number;
  totalSteps: number;
}

export function ProgressBar({ currentStep, totalSteps }: ProgressBarProps) {
  const progress = ((currentStep + 1) / totalSteps) * 100;

  return (
    <div className="progress" id="progress-bar">
      <div className="progress__track">
        <div
          className="progress__fill"
          style={{ width: `${progress}%` }}
        />
      </div>
      <span className="progress__label">
        {currentStep + 1} of {totalSteps}
      </span>
    </div>
  );
}
