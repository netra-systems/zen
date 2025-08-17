import { useEffect, useRef, useState } from 'react';

export interface WSEventData {
  type: string;
  payload?: unknown;
  timestamp?: number;
  [key: string]: unknown;
}

export interface EventManagementState {
  events: WSEventData[];
  filteredEvents: WSEventData[];
  eventTypes: string[];
  eventFilter: string;
  searchQuery: string;
}

export interface EventManagementActions {
  setEventFilter: (filter: string) => void;
  setSearchQuery: (query: string) => void;
  updateEventsFromBuffer: () => void;
}

export const useEventManagement = (
  wsEventBuffer: any,
  wsEventBufferVersion: number
): EventManagementState & EventManagementActions => {
  const [events, setEvents] = useState<WSEventData[]>([]);
  const [eventFilter, setEventFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const updateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const updateEventsFromBuffer = () => {
    if (wsEventBuffer?.getAll) {
      setEvents(wsEventBuffer.getAll());
    }
  };

  const clearUpdateTimeout = () => {
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current);
    }
  };

  const scheduleEventUpdate = () => {
    clearUpdateTimeout();
    updateTimeoutRef.current = setTimeout(updateEventsFromBuffer, 100);
  };

  const filterEvents = () => {
    return events.filter((event: WSEventData) => {
      if (eventFilter && event.type !== eventFilter) return false;
      if (searchQuery) {
        const eventString = JSON.stringify(event).toLowerCase();
        return eventString.includes(searchQuery.toLowerCase());
      }
      return true;
    });
  };

  const getEventTypes = () => {
    return [...new Set(events.map((e: WSEventData) => e.type))];
  };

  // Update events reactively when buffer version changes (debounced for performance)
  useEffect(() => {
    scheduleEventUpdate();
    return () => clearUpdateTimeout();
  }, [wsEventBuffer, wsEventBufferVersion]);

  const filteredEvents = filterEvents();
  const eventTypes = getEventTypes();

  return {
    events,
    filteredEvents,
    eventTypes,
    eventFilter,
    searchQuery,
    setEventFilter,
    setSearchQuery,
    updateEventsFromBuffer,
  };
};