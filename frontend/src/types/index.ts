export interface Call {
  id: string;
  tenant_id: string;
  vapi_call_id: string | null;
  caller_phone: string | null;
  caller_name: string | null;
  status: string | null;
  outcome: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  transcript: string | null;
  recording_url: string | null;
  summary: string | null;
  created_at: string;
}

export interface Booking {
  id: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string | null;
  service_id: string | null;
  scheduled_at: string;
  duration_minutes: number;
  status: string;
  created_at: string;
}

export interface DashboardStats {
  today: {
    calls: number;
    bookings: number;
    leads: number;
  };
  this_week: {
    calls: number;
    bookings: number;
    leads: number;
    conversion_rate: number;
  };
  recent_calls: Array<{
    id: string;
    caller_phone: string;
    caller_name: string | null;
    status: string;
    outcome: string;
    duration_seconds: number | null;
    created_at: string | null;
  }>;
  upcoming_bookings: Array<{
    id: string;
    customer_name: string;
    service_id: string | null;
    scheduled_at: string;
    status: string;
  }>;
}

export interface Tenant {
  id: string;
  business_name: string;
  vertical: string;
}

export interface AuthUser {
  id: string;
  email: string;
  tenant_id: string;
}
