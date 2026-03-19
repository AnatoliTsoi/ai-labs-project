import type { ChatMessage, DayPlan, GuestProfile } from '../types';

const MOCK_DELAY = 2500;

// ── Mock itinerary data ────────────────────────────────────

const mockDayPlan: DayPlan = {
  date: new Date().toISOString().split('T')[0],
  stops: [
    {
      order: 1,
      place: {
        place_id: 'mock-1',
        name: 'Café Moro',
        category: 'cafe',
        rating: 4.7,
        price_level: 2,
        address: '23 Riverside Walk',
        lat_lng: [51.5074, -0.1278],
        opening_hours: ['08:00–18:00'],
        dietary_compatibility: 0.95,
        interest_match: 0.8,
        travel_time_from_hotel: 8,
        booking_available: false,
        source: 'places_api',
      },
      arrival_time: '09:00',
      departure_time: '10:15',
      duration_minutes: 75,
      travel_to_next: { mode: 'walking', duration_minutes: 12, distance_km: 0.9 },
      notes: 'Incredible vegan menu with a terrace overlooking the river.',
    },
    {
      order: 2,
      place: {
        place_id: 'mock-2',
        name: 'National Gallery of Modern Art',
        category: 'museum',
        rating: 4.8,
        price_level: 2,
        address: '1 Art Square',
        lat_lng: [51.5089, -0.1283],
        opening_hours: ['10:00–18:00'],
        dietary_compatibility: 1.0,
        interest_match: 0.95,
        travel_time_from_hotel: 15,
        booking_available: true,
        source: 'places_api',
      },
      arrival_time: '10:30',
      departure_time: '12:30',
      duration_minutes: 120,
      travel_to_next: { mode: 'walking', duration_minutes: 8, distance_km: 0.6 },
      notes: 'The contemporary wing has a stunning new installation this month.',
    },
    {
      order: 3,
      place: {
        place_id: 'mock-3',
        name: 'The Garden Table',
        category: 'restaurant',
        rating: 4.6,
        price_level: 3,
        address: '45 Green Lane',
        lat_lng: [51.5095, -0.129],
        opening_hours: ['11:30–22:00'],
        dietary_compatibility: 0.9,
        interest_match: 0.85,
        travel_time_from_hotel: 20,
        booking_available: true,
        source: 'curated',
      },
      arrival_time: '12:40',
      departure_time: '14:00',
      duration_minutes: 80,
      travel_to_next: { mode: 'transit', duration_minutes: 15, distance_km: 3.2 },
      notes: 'Farm-to-table restaurant with a beautiful courtyard. Reservation recommended.',
    },
    {
      order: 4,
      place: {
        place_id: 'mock-4',
        name: 'Botanical Gardens & Sculpture Park',
        category: 'park',
        rating: 4.5,
        price_level: 1,
        address: '100 Park Road',
        lat_lng: [51.512, -0.135],
        opening_hours: ['07:00–20:00'],
        dietary_compatibility: 1.0,
        interest_match: 0.75,
        travel_time_from_hotel: 25,
        booking_available: false,
        source: 'search',
      },
      arrival_time: '14:20',
      departure_time: '16:00',
      duration_minutes: 100,
      travel_to_next: { mode: 'walking', duration_minutes: 18, distance_km: 1.4 },
      notes: 'Perfect for a relaxed afternoon stroll. The Japanese garden is a hidden gem.',
    },
    {
      order: 5,
      place: {
        place_id: 'mock-5',
        name: 'Sunset Rooftop Bar',
        category: 'nightlife',
        rating: 4.4,
        price_level: 3,
        address: '12 Sky Tower, 8th Floor',
        lat_lng: [51.51, -0.13],
        opening_hours: ['16:00–00:00'],
        dietary_compatibility: 0.85,
        interest_match: 0.9,
        travel_time_from_hotel: 10,
        booking_available: true,
        source: 'curated',
      },
      arrival_time: '16:20',
      departure_time: '18:00',
      duration_minutes: 100,
      travel_to_next: null,
      notes: 'Panoramic city views. Arrive before 17:00 for the best sunset spot.',
    },
  ],
  total_travel_time: 53,
  estimated_total_cost: '€80–€120',
  weather_contingency:
    'If rain is forecast after 2pm, swap the Botanical Gardens for the Covered Market (10 min walk from The Garden Table).',
  back_at_hotel_by: '18:30',
  map_url:
    'https://www.google.com/maps/dir/51.507,-0.127/51.508,-0.128/51.509,-0.129/51.512,-0.135/51.510,-0.130',
};

// ── API client ─────────────────────────────────────────────

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

/**
 * Submit guest profile to the agent and get a day plan back.
 */
export async function submitProfile(
  profile: Partial<GuestProfile>,
  sessionId: string,
): Promise<DayPlan> {
  if (USE_MOCK) {
    // Simulate agent processing time
    await new Promise((resolve) => setTimeout(resolve, MOCK_DELAY));
    return mockDayPlan;
  }

  const response = await fetch(`${API_BASE}/plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId,
    },
    body: JSON.stringify({ profile }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  return data.day_plan;
}

export function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
