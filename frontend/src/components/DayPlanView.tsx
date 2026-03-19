import type { DayPlan } from '../types';
import { ItineraryCard } from './ItineraryCard';
import './DayPlanView.css';

interface DayPlanViewProps {
  plan: DayPlan;
  onApprove?: () => void;
  onRequestChanges?: () => void;
}

export function DayPlanView({ plan, onApprove, onRequestChanges }: DayPlanViewProps) {
  return (
    <div className="day-plan" id="day-plan-view">
      {/* Plan header */}
      <div className="day-plan__header">
        <h3 className="day-plan__title font-display">Your Day Plan</h3>
        <span className="day-plan__date">{plan.date}</span>
      </div>

      {/* Summary stats */}
      <div className="day-plan__stats">
        <div className="day-plan__stat">
          <span className="day-plan__stat-value">{plan.stops.length}</span>
          <span className="day-plan__stat-label">Stops</span>
        </div>
        <div className="day-plan__stat-divider" />
        <div className="day-plan__stat">
          <span className="day-plan__stat-value">{plan.total_travel_time}m</span>
          <span className="day-plan__stat-label">Travel</span>
        </div>
        <div className="day-plan__stat-divider" />
        <div className="day-plan__stat">
          <span className="day-plan__stat-value">{plan.estimated_total_cost}</span>
          <span className="day-plan__stat-label">Est. Cost</span>
        </div>
        <div className="day-plan__stat-divider" />
        <div className="day-plan__stat">
          <span className="day-plan__stat-value">{plan.back_at_hotel_by}</span>
          <span className="day-plan__stat-label">Return</span>
        </div>
      </div>

      {/* Timeline */}
      <div className="day-plan__timeline">
        {plan.stops.map((stop, i) => (
          <ItineraryCard
            key={stop.order}
            stop={stop}
            isLast={i === plan.stops.length - 1}
          />
        ))}
      </div>

      {/* Weather note */}
      {plan.weather_contingency && (
        <div className="day-plan__weather">
          <span className="day-plan__weather-icon">🌦️</span>
          <p className="day-plan__weather-text">{plan.weather_contingency}</p>
        </div>
      )}

      {/* Map link */}
      {plan.map_url && (
        <a
          href={plan.map_url}
          target="_blank"
          rel="noopener noreferrer"
          className="day-plan__map-link"
          id="view-map-link"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
            <line x1="8" y1="2" x2="8" y2="18" />
            <line x1="16" y1="6" x2="16" y2="22" />
          </svg>
          View full route on Google Maps
        </a>
      )}

      {/* Action buttons */}
      <div className="day-plan__actions">
        <button
          className="day-plan__btn day-plan__btn--approve"
          onClick={onApprove}
          id="approve-plan-btn"
        >
          ✨ Looks great!
        </button>
        <button
          className="day-plan__btn day-plan__btn--change"
          onClick={onRequestChanges}
          id="request-changes-btn"
        >
          Make changes
        </button>
      </div>
    </div>
  );
}
