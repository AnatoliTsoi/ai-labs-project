import { useState, useCallback } from 'react';
import type { GuestProfile } from '../types';
import { OptionButton } from './OptionButton';
import { ProgressBar } from './ProgressBar';
import './QuestionnaireFlow.css';

interface QuestionnaireFlowProps {
  onComplete: (profile: Partial<GuestProfile>) => void;
}

interface StepConfig {
  title: string;
  subtitle: string;
  type: 'multi' | 'single' | 'time';
  field: string;
  options?: { emoji: string; value: string; label: string }[];
}

const STEPS: StepConfig[] = [
  {
    title: 'What are you in the mood for?',
    subtitle: 'Select all that interest you',
    type: 'multi',
    field: 'interests',
    options: [
      { emoji: '🎨', value: 'art', label: 'Art & Culture' },
      { emoji: '🍽️', value: 'food', label: 'Food & Dining' },
      { emoji: '🌿', value: 'nature', label: 'Nature' },
      { emoji: '🌙', value: 'nightlife', label: 'Nightlife' },
      { emoji: '🏛️', value: 'history', label: 'History' },
      { emoji: '🛍️', value: 'shopping', label: 'Shopping' },
      { emoji: '⚡', value: 'adventure', label: 'Adventure' },
      { emoji: '💆', value: 'wellness', label: 'Wellness' },
    ],
  },
  {
    title: 'Any dietary needs?',
    subtitle: 'Select all that apply',
    type: 'multi',
    field: 'dietary_restrictions',
    options: [
      { emoji: '🥬', value: 'vegan', label: 'Vegan' },
      { emoji: '🥗', value: 'vegetarian', label: 'Vegetarian' },
      { emoji: '🌾', value: 'gluten-free', label: 'Gluten-free' },
      { emoji: '☪️', value: 'halal', label: 'Halal' },
      { emoji: '✡️', value: 'kosher', label: 'Kosher' },
      { emoji: '🥜', value: 'nut-free', label: 'Nut-free' },
      { emoji: '✅', value: 'none', label: 'No restrictions' },
    ],
  },
  {
    title: "What's your ideal pace?",
    subtitle: 'How do you like to explore?',
    type: 'single',
    field: 'pace',
    options: [
      { emoji: '🐢', value: 'relaxed', label: 'Relaxed — fewer stops, long visits' },
      { emoji: '⚖️', value: 'moderate', label: 'Moderate — balanced mix' },
      { emoji: '🚀', value: 'packed', label: 'Packed — see as much as possible' },
    ],
  },
  {
    title: "What's your budget?",
    subtitle: "So we match the right places",
    type: 'single',
    field: 'budget_level',
    options: [
      { emoji: '💰', value: 'budget', label: 'Budget-friendly' },
      { emoji: '💎', value: 'moderate', label: 'Moderate' },
      { emoji: '👑', value: 'luxury', label: 'Luxury — treat yourself' },
    ],
  },
  {
    title: "Who's coming along?",
    subtitle: "This helps us pick the best spots",
    type: 'single',
    field: 'party_composition',
    options: [
      { emoji: '🧑', value: 'solo', label: 'Just me' },
      { emoji: '💑', value: 'couple', label: 'With my partner' },
      { emoji: '👨‍👩‍👧', value: 'family_young_kids', label: 'Family with kids' },
      { emoji: '👥', value: 'group', label: 'Group of friends' },
    ],
  },
  {
    title: 'When are you free?',
    subtitle: "We'll build your day around this window",
    type: 'time',
    field: 'time_available',
  },
];

export function QuestionnaireFlow({ onComplete }: QuestionnaireFlowProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('21:00');

  const step = STEPS[currentStep];
  const isLastStep = currentStep === STEPS.length - 1;

  const currentValue = answers[step.field];
  const isMulti = step.type === 'multi';
  const isTime = step.type === 'time';

  const canProceed =
    isTime ||
    (isMulti && Array.isArray(currentValue) && currentValue.length > 0) ||
    (!isMulti && !isTime && typeof currentValue === 'string' && currentValue.length > 0);

  const handleOptionClick = useCallback(
    (value: string) => {
      setAnswers((prev) => {
        if (isMulti) {
          const arr = (prev[step.field] as string[]) || [];
          // "No restrictions" clears others; selecting others clears "none"
          if (value === 'none') {
            return { ...prev, [step.field]: ['none'] };
          }
          const filtered = arr.filter((v) => v !== 'none');
          if (filtered.includes(value)) {
            return { ...prev, [step.field]: filtered.filter((v) => v !== value) };
          }
          return { ...prev, [step.field]: [...filtered, value] };
        }
        return { ...prev, [step.field]: value };
      });
    },
    [step.field, isMulti],
  );

  const handleNext = useCallback(() => {
    if (isLastStep) {
      // Build profile and submit
      const profile: Partial<GuestProfile> = {
        interests: (answers.interests as string[]) || [],
        dietary_restrictions: (answers.dietary_restrictions as string[]) || [],
        pace: (answers.pace as GuestProfile['pace']) || 'moderate',
        budget_level: (answers.budget_level as GuestProfile['budget_level']) || 'moderate',
        party_composition: (answers.party_composition as GuestProfile['party_composition']) || 'solo',
        time_available: { start_time: startTime, end_time: endTime },
      };
      onComplete(profile);
    } else {
      setCurrentStep((s) => s + 1);
    }
  }, [isLastStep, answers, startTime, endTime, onComplete]);

  const handleBack = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((s) => s - 1);
    }
  }, [currentStep]);

  const isOptionSelected = (value: string) => {
    if (isMulti) {
      return Array.isArray(currentValue) && currentValue.includes(value);
    }
    return currentValue === value;
  };

  return (
    <div className="questionnaire" id="questionnaire-flow">
      <div className="questionnaire__container">
        <ProgressBar currentStep={currentStep} totalSteps={STEPS.length} />

        <div className="questionnaire__step" key={currentStep}>
          <div className="questionnaire__header">
            <h2 className="questionnaire__title font-display">{step.title}</h2>
            <p className="questionnaire__subtitle">{step.subtitle}</p>
          </div>

          {!isTime && step.options && (
            <div className={`questionnaire__options ${isMulti ? 'questionnaire__options--grid' : ''}`}>
              {step.options.map((opt) => (
                <OptionButton
                  key={opt.value}
                  emoji={opt.emoji}
                  label={opt.label}
                  selected={isOptionSelected(opt.value)}
                  onClick={() => handleOptionClick(opt.value)}
                />
              ))}
            </div>
          )}

          {isTime && (
            <div className="questionnaire__time">
              <div className="questionnaire__time-field">
                <label htmlFor="start-time" className="questionnaire__time-label">
                  Start
                </label>
                <input
                  id="start-time"
                  type="time"
                  className="questionnaire__time-input"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                />
              </div>
              <span className="questionnaire__time-sep">→</span>
              <div className="questionnaire__time-field">
                <label htmlFor="end-time" className="questionnaire__time-label">
                  End
                </label>
                <input
                  id="end-time"
                  type="time"
                  className="questionnaire__time-input"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                />
              </div>
            </div>
          )}
        </div>

        <div className="questionnaire__nav">
          <button
            className="questionnaire__btn questionnaire__btn--back"
            onClick={handleBack}
            disabled={currentStep === 0}
            type="button"
          >
            ← Back
          </button>
          <button
            className="questionnaire__btn questionnaire__btn--next"
            onClick={handleNext}
            disabled={!canProceed && !isTime}
            type="button"
            id={isLastStep ? 'submit-profile-btn' : 'next-step-btn'}
          >
            {isLastStep ? '✨ Build my day' : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  );
}
