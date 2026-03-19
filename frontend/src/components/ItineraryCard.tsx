import type { ItineraryStop } from '../types';
import './ItineraryCard.css';

interface ItineraryCardProps {
  stop: ItineraryStop;
  isLast: boolean;
}

const categoryIcons: Record<string, string> = {
  restaurant: '🍽️',
  cafe: '☕',
  attraction: '🏛️',
  museum: '🎨',
  park: '🌿',
  activity: '⚡',
  nightlife: '🌙',
};

const travelModeIcons: Record<string, string> = {
  walking: '🚶',
  transit: '🚇',
  driving: '🚗',
  cycling: '🚲',
};

function renderStars(rating: number) {
  const full = Math.floor(rating);
  const hasHalf = rating - full >= 0.3;
  const stars: string[] = [];
  for (let i = 0; i < full; i++) stars.push('★');
  if (hasHalf) stars.push('½');
  return stars.join('');
}

function priceDots(level: number) {
  return '€'.repeat(level);
}

export function ItineraryCard({ stop, isLast }: ItineraryCardProps) {
  const { place, arrival_time, departure_time, duration_minutes, travel_to_next, notes } = stop;
  const icon = categoryIcons[place.category] || '📍';

  return (
    <div className="itin-card" id={`itinerary-stop-${stop.order}`}>
      {/* Timeline connector */}
      <div className="itin-card__timeline">
        <div className="itin-card__dot" />
        {!isLast && <div className="itin-card__line" />}
      </div>

      {/* Card content */}
      <div className="itin-card__body">
        <div className="itin-card__header">
          <span className="itin-card__time">
            {arrival_time} – {departure_time}
          </span>
          <span className="itin-card__duration">{duration_minutes} min</span>
        </div>

        <div className="itin-card__main">
          <span className="itin-card__icon">{icon}</span>
          <div className="itin-card__info">
            <h4 className="itin-card__name">{place.name}</h4>
            <div className="itin-card__meta">
              <span className="itin-card__rating">
                <span className="itin-card__stars">{renderStars(place.rating)}</span>
                <span>{place.rating}</span>
              </span>
              <span className="itin-card__price">{priceDots(place.price_level)}</span>
              <span className="itin-card__category">{place.category}</span>
            </div>
            <p className="itin-card__address">{place.address}</p>
            {notes && <p className="itin-card__notes">{notes}</p>}
          </div>
        </div>

        {/* Travel segment to next stop */}
        {travel_to_next && !isLast && (
          <div className="itin-card__travel">
            <span className="itin-card__travel-icon">
              {travelModeIcons[travel_to_next.mode] || '🚶'}
            </span>
            <span className="itin-card__travel-text">
              {travel_to_next.duration_minutes} min {travel_to_next.mode}
              {travel_to_next.distance_km > 0 && ` · ${travel_to_next.distance_km} km`}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
