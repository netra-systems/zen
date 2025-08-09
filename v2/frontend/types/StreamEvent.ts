export interface StreamEvent {
  event_type: string;
  data: {
    [k: string]: any;
  };
}
