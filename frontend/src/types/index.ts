/* ============================================================
   Types matching the backend ADK agent models
   ============================================================ */

export interface GuestProfile {
  guest_id: string;
  dietary_restrictions: string[];
  interests: string[];
  mobility: 'full' | 'limited' | 'wheelchair';
  budget_level: 'budget' | 'moderate' | 'luxury';
  pace: 'relaxed' | 'moderate' | 'packed';
  party_composition: 'solo' | 'couple' | 'family_young_kids' | 'group';
  time_available: {
    start_time: string;
    end_time: string;
  };
  location_context: string;
  special_requests: string[];
}

export interface DiscoveredOption {
  place_id: string;
  name: string;
  category: 'restaurant' | 'attraction' | 'activity' | 'cafe' | 'park' | 'museum' | 'nightlife';
  rating: number;
  price_level: number;
  address: string;
  lat_lng: [number, number];
  opening_hours: string[];
  dietary_compatibility: number;
  interest_match: number;
  travel_time_from_hotel: number;
  booking_available: boolean;
  source: 'places_api' | 'search' | 'curated';
  photo_url?: string;
}

export interface TravelSegment {
  mode: 'walking' | 'transit' | 'driving' | 'cycling';
  duration_minutes: number;
  distance_km: number;
}

export interface ItineraryStop {
  order: number;
  place: DiscoveredOption;
  arrival_time: string;
  departure_time: string;
  duration_minutes: number;
  travel_to_next: TravelSegment | null;
  notes: string;
}

export interface DayPlan {
  date: string;
  stops: ItineraryStop[];
  total_travel_time: number;
  estimated_total_cost: string;
  weather_contingency: string;
  back_at_hotel_by: string;
  map_url?: string;
}

export type FeedbackActionType =
  | 'approve'
  | 'swap_stop'
  | 'change_time'
  | 'add_activity'
  | 'remove_stop'
  | 'change_pace'
  | 'restart';

export interface FeedbackAction {
  action: FeedbackActionType;
  target_stop: number | null;
  details: string;
}

export type MessageRole = 'user' | 'agent';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  day_plan?: DayPlan;
  is_streaming?: boolean;
}

export interface SessionInfo {
  session_id: string;
  created_at: string;
  guest_name?: string;
}
