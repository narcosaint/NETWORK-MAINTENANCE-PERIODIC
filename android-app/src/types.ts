export type User = {
  id: string;
  username: string;
  name: string;
  role: "technician" | "supervisor";
  active: boolean;
};
export type Status =
  "assigned" | "in_progress" | "submitted" | "revision_requested" | "approved";
export type Profile = {
  minimum_percent?: number | null;
  fo?: { download_mbps?: number | null; upload_mbps?: number | null };
  wireless?: { download_mbps?: number | null; upload_mbps?: number | null };
};
export type Hotel = {
  id: string;
  name: string;
  address: string;
  customer_name?: string | null;
  maintenance_profile?: Profile;
};
export type Backbone = {
  download_mbps?: number | null;
  upload_mbps?: number | null;
  agreement_download_mbps?: number | null;
  agreement_upload_mbps?: number | null;
  minimum_percent?: number | null;
  conformity?: "conforming" | "not_conforming" | null;
  conformity_reason?: string | null;
  agreement_mbps?: number | null;
  speedtest_mbps?: number | null;
  signal_dbm?: number | null;
  tx_mbps?: number | null;
  rx_mbps?: number | null;
  ccq_percent?: number | null;
  link_test_radio?: string | null;
  notes?: string | null;
  source?: "manual";
};
export type Report = {
  form_version?: 1 | 2;
  site_profile?: Profile | null;
  customer_company?: string | null;
  pic_name?: string | null;
  pic_contact?: string | null;
  backbone_mode?:
    "fo_only" | "wireless_only" | "both" | "failover" | "bonding" | null;
  fo?: Backbone | null;
  wireless?: Backbone | null;
  router_connector?: string | null;
  switch_connector?: string | null;
  signal_test?: string | null;
  blank_spot?: boolean | null;
  hotspot?: boolean | null;
  router_connector_notes?: string | null;
  switch_connector_notes?: string | null;
  signal_test_notes?: string | null;
  blank_spot_notes?: string | null;
  hotspot_notes?: string | null;
  lan_notes?: string | null;
  summary?: string | null;
  work_status?: "completed" | "pending" | null;
  pending_reason?: string | null;
  customer_feedback?: string | null;
  solution?: string | null;
  pic_exception_reason?: string | null;
};
export type Band = {
  status?: "measured" | "unavailable" | "not_tested";
  signal_dbm?: number | null;
  channel?: number | null;
  bandwidth_mbps?: number | null;
  ssid?: string | null;
  bssid?: string | null;
  reason?: string | null;
  source?: string;
};
export type Run = {
  id: string;
  band: string;
  status: string;
  created_at: string;
  finished_at?: string;
  context?: {
    transport?: string;
    network?: string;
    wifi_confirmed?: boolean;
    endpoint_origin?: string;
  };
  metrics?: {
    download_mbps?: number;
    upload_mbps?: number;
    ping_ms?: number;
    jitter_ms?: number;
  };
  error?: string | null;
};
export type Photo = { id: string; url: string; created_at: string };
export type Item = {
  id: string;
  device_id: string;
  device: { id: string; name: string; device_type: string };
  floor?: string | null;
  point?: string | null;
  result?: { outcome?: string; notes?: string; band_24?: Band; band_5?: Band };
  photos: Photo[];
  speedtests: Run[];
};
export type Visit = {
  id: string;
  hotel_id: string;
  technician_id: string;
  planned_date: string;
  status: Status;
  version: number;
  report: Report;
  maintenance_completed?: boolean;
  checkin?: {
    server_time?: string;
    latitude?: number;
    longitude?: number;
    accuracy_m?: number;
  };
  site?: Hotel;
  devices?: Item[];
  sampling_coverage?: SamplingCoverage;
};
export type ReportDraft = {
  report: Report;
  version: number;
  updatedAt: string;
};
export type PointDraft = {
  radio?: import("./services/wifi").RadioDraft;
  baseVisitVersion?: number;
  baseSessionVersion?: number;
  location?: string;
  notes?: string;
  findings?: string;
  action?: string;
  recommendation?: string;
  status?: string;
  updatedAt: string;
};
export type LocalPhoto = {
  id: string;
  pointId: string;
  category: string;
  caption: string;
  createdAt: string;
  blob: Blob;
};
export type Point = {
  id: string;
  name: string;
  item?: Item;
  session?: SamplingCoverage["floors"][number]["points"][number];
};
export type Floor = { id: string; name: string; points: Point[] };
export type CheckIn = {
  expected_version: number;
  device_time: string;
  latitude?: number;
  longitude?: number;
  accuracy_m?: number;
  gps_exception_reason?: string;
};

export type SamplingCoverage = {
  id: string;
  hotel_visit_id: string;
  period: string;
  completion_available: false;
  observations_enabled?: boolean;
  photo_policy: {
    sampling_categories: string[];
    infrastructure_categories: string[];
  };
  floors: {
    id: string;
    floor_id: string;
    name: string;
    target_count: number;
    points: {
      id: string;
      sampling_point_id: string;
      name: string;
      location: string | null;
      device: { id: string; name: string; mac_address: string | null } | null;
      status: string;
      version: number;
      observation?: SamplingObservation | null;
    }[];
  }[];
};

export type SamplingNotes = {
  condition: "untested" | "good" | "attention" | "problem";
  notes: string;
  findings: string;
  action: string;
  recommendation: string;
};
export type ObservationSubmission = {
  id: string;
  expected_visit_version: number;
  expected_session_version: number;
  captured_at: string;
  notes: SamplingNotes;
  wifi_connection?: ReturnType<
    typeof import("./services/wifi").radioPayload
  >["wifi_connection"];
  wifi_scan?: ReturnType<
    typeof import("./services/wifi").radioPayload
  >["wifi_scan"];
};
export type SamplingObservation = {
  id: string;
  session_id: string;
  session_version: number;
  visit_version: number;
  captured_at: string;
  received_at: string;
  notes: SamplingNotes;
  measurement_trust: "client_reported";
  radio_verified: false;
  completion_accepted: false;
  wifi_connection?: ObservationSubmission["wifi_connection"];
  wifi_scan?: ObservationSubmission["wifi_scan"];
};
