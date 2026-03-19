import { useState, useCallback } from 'react';
import type { GuestProfile, DayPlan } from './types';
import { Header } from './components/Header';
import { WelcomeScreen } from './components/WelcomeScreen';
import { QuestionnaireFlow } from './components/QuestionnaireFlow';
import { LoadingScreen } from './components/LoadingScreen';
import { DayPlanView } from './components/DayPlanView';
import { useSession } from './hooks/useSession';
import { submitProfile } from './api/agent';
import './App.css';

type AppState = 'welcome' | 'questionnaire' | 'loading' | 'itinerary';

function App() {
  const { sessionId } = useSession();
  const [appState, setAppState] = useState<AppState>('welcome');
  const [dayPlan, setDayPlan] = useState<DayPlan | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleStart = useCallback(() => {
    setAppState('questionnaire');
  }, []);

  const handleProfileComplete = useCallback(
    async (profile: Partial<GuestProfile>) => {
      setAppState('loading');
      setError(null);

      try {
        const plan = await submitProfile(profile, sessionId);
        setDayPlan(plan);
        setAppState('itinerary');
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Something went wrong';
        setError(message);
        setAppState('questionnaire');
      }
    },
    [sessionId],
  );

  const handleStartOver = useCallback(() => {
    setDayPlan(null);
    setError(null);
    setAppState('questionnaire');
  }, []);

  const handleNewChat = useCallback(() => {
    setDayPlan(null);
    setError(null);
    setAppState('welcome');
  }, []);

  return (
    <div className="app" id="concierge-app">
      <Header onNewChat={handleNewChat} />

      <main className="app__main">
        {appState === 'welcome' && (
          <WelcomeScreen onStart={handleStart} />
        )}

        {appState === 'questionnaire' && (
          <QuestionnaireFlow onComplete={handleProfileComplete} />
        )}

        {appState === 'loading' && <LoadingScreen />}

        {appState === 'itinerary' && dayPlan && (
          <div className="app__itinerary">
            <div className="app__itinerary-inner">
              <DayPlanView
                plan={dayPlan}
                onApprove={() => alert('Plan confirmed! 🎉')}
                onRequestChanges={handleStartOver}
              />
            </div>
          </div>
        )}
      </main>

      {error && (
        <div className="app__error" role="alert" id="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}
    </div>
  );
}

export default App;
