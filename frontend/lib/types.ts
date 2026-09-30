export type UserRole = "artist" | "manager" | "finance" | "ar" | "admin";

export type User = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_2fa_enabled: boolean;
  requires_2fa: boolean;
  must_enable_2fa: boolean;
};

export type Label = {
  id: number;
  name: string;
  slug: string;
};

export type Artist = {
  id: number;
  label: number;
  name: string;
  slug: string;
  user: number | null;
  username: string;
};

export type TrackArtistRole = "primary" | "featured";

export type TrackArtist = {
  id: number;
  track: number;
  artist: number;
  artist_name: string;
  role: TrackArtistRole;
  billing_order: number;
};

export type TrackAsset = {
  id: number;
  isrc: string;
  asset_kind: "audio" | "music_video" | "other" | "unknown";
};

export type Track = {
  id: number;
  release: number;
  title: string;
  isrc: string | null;
  iswc: string | null;
  track_number: number;
  duration_seconds: number | null;
  artists: TrackArtist[];
  assets: TrackAsset[];
};

export type Release = {
  id: number;
  label: number;
  primary_artist: number;
  primary_artist_name: string;
  title: string;
  release_type: ReleaseType;
  upc: string | null;
  release_date: string | null;
  tracks: Track[];
  track_count: number;
};
export type ReleaseType = "album" | "ep" | "single" | "compilation";

export const RELEASE_TYPES: { value: ReleaseType; label: string }[] = [
  { value: "single", label: "Single" },
  { value: "ep", label: "EP" },
  { value: "album", label: "Album" },
  { value: "compilation", label: "Compilation" },
];

export type StatementStatus = "pending" | "processing" | "processed" | "failed";

export type RoyaltyStatement = {
  id: number;
  label: number;
  distributor: string;
  distributor_display: string;
  filename: string;
  period_start: string | null;
  period_end: string | null;
  status: StatementStatus;
  status_display: string;
  row_count: number | null;
  total_amount: string | null;
  currency: string;
  uploaded_by_username: string;
  error_message: string;
  created_at: string;
};

export type RoyaltyRun = {
  id: number;
  label: number;
  name: string;
  status: "draft" | "ready" | "closed";
  statement_count: number;
  payout_count: number;
  payout_batch_id: number | null;
  total_amount: string;
  currency: string;
  consolidation_error: string;
  created_at: string;
};

export type RoyaltyRunPayout = {
  id: number;
  run: number;
  track: number | null;
  isrc: string;
  track_title: string;
  participant_name: string;
  artist: number | null;
  role: string;
  role_display: string;
  share_percentage: string;
  track_gross: string;
  amount: string;
  unallocated_reason: string;
};

export type ArtistEarning = {
  id: number;
  run: number;
  run_name: string;
  run_status: string;
  run_created_at: string;
  currency: string;
  track: number | null;
  isrc: string;
  track_title: string;
  participant_name: string;
  role: string;
  role_display: string;
  share_percentage: string;
  track_gross: string;
  amount: string;
};

export type ContractType =
  | "recording"
  | "distribution"
  | "license"
  | "sync"
  | "publishing"
  | "other";

export type ContractStatus = "draft" | "active" | "expired" | "terminated";

export type ObligationStatus = "open" | "done" | "waived";

export type ContractObligation = {
  id: number;
  contract: number;
  title: string;
  status: ObligationStatus;
  status_display: string;
  due_date: string | null;
  notes: string;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export const OBLIGATION_STATUSES: { value: ObligationStatus; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "done", label: "Done" },
  { value: "waived", label: "Waived" },
];

export type Contract = {
  id: number;
  label: number;
  artist: number | null;
  artist_name: string;
  title: string;
  contract_type: ContractType;
  contract_type_display: string;
  status: ContractStatus;
  status_display: string;
  start_date: string | null;
  end_date: string | null;
  term_notes: string;
  file: string | null;
  filename: string;
  obligations?: ContractObligation[];
  open_obligation_count?: number;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export const CONTRACT_TYPES: { value: ContractType; label: string }[] = [
  { value: "recording", label: "Recording" },
  { value: "distribution", label: "Distribution" },
  { value: "license", label: "License" },
  { value: "sync", label: "Sync" },
  { value: "publishing", label: "Publishing" },
  { value: "other", label: "Other" },
];

export const CONTRACT_STATUSES: { value: ContractStatus; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "active", label: "Active" },
  { value: "expired", label: "Expired" },
  { value: "terminated", label: "Terminated" },
];

export type PipelineStage =
  | "lead"
  | "researching"
  | "contacting"
  | "meeting"
  | "negotiating"
  | "signed"
  | "passed"
  | "on_hold";

export type ProspectPriority = "low" | "medium" | "high" | "hot";

export type Prospect = {
  id: number;
  label: number;
  name: string;
  stage: PipelineStage;
  stage_display: string;
  priority: ProspectPriority;
  priority_display: string;
  genre: string;
  location: string;
  contact_email: string;
  contact_phone: string;
  spotify_url: string;
  instagram_url: string;
  other_links: string;
  source: string;
  notes: string;
  assigned_to: number | null;
  assigned_to_username: string;
  signed_artist: number | null;
  signed_artist_name: string;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export const PIPELINE_STAGES: { value: PipelineStage; label: string }[] = [
  { value: "lead", label: "Lead" },
  { value: "researching", label: "Researching" },
  { value: "contacting", label: "Contacting" },
  { value: "meeting", label: "Meeting" },
  { value: "negotiating", label: "Negotiating" },
  { value: "signed", label: "Signed" },
  { value: "passed", label: "Passed" },
  { value: "on_hold", label: "On hold" },
];

export const PROSPECT_PRIORITIES: { value: ProspectPriority; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "hot", label: "Hot" },
];

export type ProSociety = "ascap" | "bmi" | "sesac" | "socan" | "other" | "";

export type RegistrationStatus = "draft" | "ready" | "submitted" | "registered";

export type ContributorRole = "writer" | "composer" | "writer_composer" | "publisher" | "admin";

export type WorkShare = {
  id?: number;
  contributor_name: string;
  artist: number | null;
  artist_name?: string;
  role: ContributorRole;
  role_display?: string;
  percentage: string;
  ipi_cae: string;
  pro_affiliation: ProSociety;
  pro_affiliation_display?: string;
};

export type RegistrationEvent = {
  id: number;
  work: number;
  status: RegistrationStatus;
  status_display: string;
  pro_society: ProSociety;
  pro_society_display: string;
  reference: string;
  notes: string;
  occurred_on: string;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export type MusicalWork = {
  id: number;
  label: number;
  title: string;
  iswc: string | null;
  registration_status: RegistrationStatus;
  registration_status_display: string;
  target_pro: ProSociety;
  target_pro_display: string;
  notes: string;
  track_ids: number[];
  track_titles: string[];
  shares: WorkShare[];
  total_percentage: string;
  registration_events?: RegistrationEvent[];
  created_at: string;
  updated_at: string;
};

export const PRO_SOCIETIES: { value: ProSociety; label: string }[] = [
  { value: "", label: "Not set" },
  { value: "ascap", label: "ASCAP" },
  { value: "bmi", label: "BMI" },
  { value: "sesac", label: "SESAC" },
  { value: "socan", label: "SOCAN" },
  { value: "other", label: "Other" },
];

export const REGISTRATION_STATUSES: { value: RegistrationStatus; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "ready", label: "Ready to register" },
  { value: "submitted", label: "Submitted" },
  { value: "registered", label: "Registered" },
];

export const CONTRIBUTOR_ROLES: { value: ContributorRole; label: string }[] = [
  { value: "writer", label: "Writer" },
  { value: "composer", label: "Composer" },
  { value: "writer_composer", label: "Writer/Composer" },
  { value: "publisher", label: "Publisher" },
  { value: "admin", label: "Admin publisher" },
];

export type PayoutBatch = {
  id: number;
  label: number;
  run: number;
  run_name: string;
  name: string;
  status: "ready" | "partially_paid" | "paid" | "closed";
  total_amount: string;
  currency: string;
  payout_count: number;
  pending_count: number;
  paid_count: number;
  created_at: string;
};

export type Payout = {
  id: number;
  batch: number;
  artist: number | null;
  participant_name: string;
  amount: string;
  status: "pending" | "paid" | "cancelled";
  paid_at: string | null;
  payment_reference: string;
  created_at: string;
};

export type AuditEvent = {
  id: number;
  label: number;
  actor: number | null;
  actor_username: string | null;
  action: string;
  action_display: string;
  resource_type: string;
  resource_id: number;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type NotificationKind =
  | "statement_processed"
  | "statement_failed"
  | "payout_ready"
  | "payout_paid";

export type PortalNotification = {
  id: number;
  label: number;
  kind: NotificationKind;
  kind_display: string;
  title: string;
  body: string;
  link_path: string;
  resource_type: string;
  resource_id: number | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
};

export const DISTRIBUTORS = [
  { value: "distrokid", label: "DistroKid" },
  { value: "tunecore", label: "TuneCore" },
  { value: "cd_baby", label: "CD Baby" },
  { value: "symphonic", label: "Symphonic" },
  { value: "onerpm", label: "ONErpm" },
  { value: "routenote", label: "RouteNote" },
  { value: "toolost", label: "TooLost" },
  { value: "fuga", label: "FUGA" },
  { value: "vydia", label: "Vydia" },
  { value: "the_orchard", label: "The Orchard" },
  { value: "colonize", label: "Colonize Media" },
  { value: "lujo", label: "Lujo Network" },
  { value: "other", label: "Other" },
] as const;

export type SplitRole =
  | "artist"
  | "producer"
  | "featured"
  | "writer"
  | "label"
  | "other";

export type SplitEntry = {
  id?: number;
  participant_name: string;
  artist: number | null;
  role: SplitRole;
  role_display?: string;
  percentage: string;
};

export type SplitSheet = {
  id: number;
  track: number;
  track_title: string;
  track_isrc: string | null;
  release_id: number;
  release_title: string;
  primary_artist_name: string;
  status: "draft" | "finalized";
  notes: string;
  entries: SplitEntry[];
  total_percentage: string;
  created_at: string;
  updated_at: string;
};

export type RoyaltyLineItem = {
  id: number;
  statement: number;
  track: number | null;
  sale_period: string | null;
  store: string;
  country: string;
  artist_name: string;
  track_title: string;
  isrc: string;
  upc: string;
  quantity: number;
  amount: string;
};

export const SPLIT_ROLES: { value: SplitRole; label: string }[] = [
  { value: "artist", label: "Artist" },
  { value: "producer", label: "Producer" },
  { value: "featured", label: "Featured Artist" },
  { value: "writer", label: "Writer" },
  { value: "label", label: "Label" },
  { value: "other", label: "Other" },
];

export type AnalyticsAmountRow = {
  amount: string;
};

export type AnalyticsDistributorRow = AnalyticsAmountRow & {
  distributor: string;
  distributor_display: string;
  statement_count: number;
};

export type AnalyticsPeriodRow = AnalyticsAmountRow & {
  period: string;
};

export type AnalyticsArtistRow = AnalyticsAmountRow & {
  artist_id: number;
  artist_name: string;
};

export type AnalyticsTrackRow = AnalyticsAmountRow & {
  track_id: number | null;
  track_title: string;
  isrc: string;
};

export type AnalyticsRunRow = AnalyticsAmountRow & {
  run_id: number;
  run_name: string;
  currency: string;
};

export type AnalyticsPipelineStageRow = {
  stage: string;
  stage_display: string;
  count: number;
};

export type LabelAnalyticsSummary = {
  scope: "label";
  currency: string;
  totals: {
    statement_gross: string;
    statement_count: number;
    run_allocated: string;
    payout_pending: string;
    payout_paid: string;
    artists: number;
    releases: number;
    tracks: number;
  };
  by_distributor: AnalyticsDistributorRow[];
  by_period: AnalyticsPeriodRow[];
  by_artist: AnalyticsArtistRow[];
  by_track: AnalyticsTrackRow[];
  pipeline?: {
    total: number;
    by_stage: AnalyticsPipelineStageRow[];
  };
};

export type ArtistAnalyticsSummary = {
  scope: "artist";
  currency: string;
  artist_id: number | null;
  artist_name: string | null;
  totals: {
    earnings: string;
    payout_pending: string;
    payout_paid: string;
  };
  by_period: AnalyticsPeriodRow[];
  by_track: AnalyticsTrackRow[];
  by_run: AnalyticsRunRow[];
};

export type OpsAnalyticsSummary = {
  scope: "ops";
  catalog: {
    artists: number;
    releases: number;
    tracks: number;
  };
  pipeline: {
    total: number;
    by_stage: AnalyticsPipelineStageRow[];
  };
};

export type AnalyticsSummary =
  | LabelAnalyticsSummary
  | ArtistAnalyticsSummary
  | OpsAnalyticsSummary;

export type SyncStatus =
  | "inquiry"
  | "pitched"
  | "shortlisted"
  | "cleared"
  | "licensed"
  | "passed"
  | "on_hold";

export type SyncMediaType =
  | "film"
  | "tv"
  | "ad"
  | "trailer"
  | "game"
  | "social"
  | "other";

export type SyncOpportunity = {
  id: number;
  label: number;
  title: string;
  status: SyncStatus;
  status_display: string;
  media_type: SyncMediaType;
  media_type_display: string;
  client_name: string;
  supervisor_name: string;
  supervisor_email: string;
  territory: string;
  exclusivity: string;
  fee_amount: string | null;
  currency: string;
  term_notes: string;
  track: number | null;
  track_title: string;
  release: number | null;
  release_title: string;
  artist: number | null;
  artist_name: string;
  contract: number | null;
  contract_title: string;
  pitched_at: string | null;
  licensed_at: string | null;
  notes: string;
  assigned_to: number | null;
  assigned_to_username: string;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export const SYNC_STATUSES: { value: SyncStatus; label: string }[] = [
  { value: "inquiry", label: "Inquiry" },
  { value: "pitched", label: "Pitched" },
  { value: "shortlisted", label: "Shortlisted" },
  { value: "cleared", label: "Cleared" },
  { value: "licensed", label: "Licensed" },
  { value: "passed", label: "Passed" },
  { value: "on_hold", label: "On hold" },
];

export const SYNC_MEDIA_TYPES: { value: SyncMediaType; label: string }[] = [
  { value: "film", label: "Film" },
  { value: "tv", label: "TV" },
  { value: "ad", label: "Advertising" },
  { value: "trailer", label: "Trailer" },
  { value: "game", label: "Game" },
  { value: "social", label: "Social / digital" },
  { value: "other", label: "Other" },
];

export type CampaignStatus =
  | "draft"
  | "planned"
  | "active"
  | "completed"
  | "cancelled";

export type CampaignType =
  | "release"
  | "playlist"
  | "press"
  | "social"
  | "ads"
  | "other";

export type MarketingCampaign = {
  id: number;
  label: number;
  title: string;
  status: CampaignStatus;
  status_display: string;
  campaign_type: CampaignType;
  campaign_type_display: string;
  artist: number | null;
  artist_name: string;
  release: number | null;
  release_title: string;
  start_date: string | null;
  end_date: string | null;
  smart_link_url: string;
  channels: string;
  goals: string;
  notes: string;
  assigned_to: number | null;
  assigned_to_username: string;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export const CAMPAIGN_STATUSES: { value: CampaignStatus; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "planned", label: "Planned" },
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

export const CAMPAIGN_TYPES: { value: CampaignType; label: string }[] = [
  { value: "release", label: "Release campaign" },
  { value: "playlist", label: "Playlist pitch" },
  { value: "press", label: "Press / PR" },
  { value: "social", label: "Social" },
  { value: "ads", label: "Paid ads" },
  { value: "other", label: "Other" },
];

export type ExpenseCategory =
  | "advance"
  | "recording"
  | "marketing"
  | "video"
  | "touring"
  | "legal"
  | "other";

export type LabelExpense = {
  id: number;
  label: number;
  artist: number | null;
  artist_name: string;
  release: number | null;
  release_title: string;
  category: ExpenseCategory;
  category_display: string;
  description: string;
  amount: string;
  currency: string;
  incurred_on: string;
  is_recoupable: boolean;
  notes: string;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export type Budget = {
  id: number;
  label: number;
  artist: number | null;
  artist_name: string;
  release: number | null;
  release_title: string;
  name: string;
  category: ExpenseCategory;
  category_display: string;
  amount: string;
  currency: string;
  period_start: string | null;
  period_end: string | null;
  notes: string;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export type RecoupmentEntryType = "charge" | "credit" | "adjustment";

export type RecoupmentEntry = {
  id: number;
  label: number;
  artist: number;
  artist_name: string;
  release: number | null;
  release_title: string;
  expense: number | null;
  entry_type: RecoupmentEntryType;
  entry_type_display: string;
  amount: string;
  signed_amount: string;
  currency: string;
  effective_on: string;
  description: string;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export type RecoupmentBalance = {
  artist: number;
  artist_name: string;
  unrecouped: string;
  currency: string;
};

export const EXPENSE_CATEGORIES: { value: ExpenseCategory; label: string }[] = [
  { value: "advance", label: "Advance" },
  { value: "recording", label: "Recording" },
  { value: "marketing", label: "Marketing" },
  { value: "video", label: "Video" },
  { value: "touring", label: "Touring" },
  { value: "legal", label: "Legal" },
  { value: "other", label: "Other" },
];

export const RECOUPMENT_ENTRY_TYPES: { value: RecoupmentEntryType; label: string }[] = [
  { value: "charge", label: "Charge (unrecouped)" },
  { value: "credit", label: "Credit (recouped)" },
  { value: "adjustment", label: "Adjustment" },
];

export type TaskStatus = "todo" | "in_progress" | "blocked" | "done";

export type TaskPriority = "low" | "medium" | "high";

export type ReleaseTask = {
  id: number;
  label: number;
  release: number;
  release_title: string;
  title: string;
  status: TaskStatus;
  status_display: string;
  priority: TaskPriority;
  priority_display: string;
  due_date: string | null;
  notes: string;
  assigned_to: number | null;
  assigned_to_username: string;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export const TASK_STATUSES: { value: TaskStatus; label: string }[] = [
  { value: "todo", label: "To do" },
  { value: "in_progress", label: "In progress" },
  { value: "blocked", label: "Blocked" },
  { value: "done", label: "Done" },
];

export const TASK_PRIORITIES: { value: TaskPriority; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

export type DeliveryStatus =
  | "planned"
  | "submitted"
  | "live"
  | "taken_down"
  | "failed";

export type DspTarget =
  | "spotify"
  | "apple"
  | "amazon"
  | "youtube"
  | "tidal"
  | "deezer"
  | "other";

export type DspDelivery = {
  id: number;
  label: number;
  release: number;
  release_title: string;
  dsp: DspTarget;
  dsp_display: string;
  status: DeliveryStatus;
  status_display: string;
  distributor: string;
  target_live_date: string | null;
  submitted_at: string | null;
  live_at: string | null;
  store_url: string;
  notes: string;
  created_by: number | null;
  created_by_username: string;
  created_at: string;
  updated_at: string;
};

export const DELIVERY_STATUSES: { value: DeliveryStatus; label: string }[] = [
  { value: "planned", label: "Planned" },
  { value: "submitted", label: "Submitted" },
  { value: "live", label: "Live" },
  { value: "taken_down", label: "Taken down" },
  { value: "failed", label: "Failed" },
];

export const DSP_TARGETS: { value: DspTarget; label: string }[] = [
  { value: "spotify", label: "Spotify" },
  { value: "apple", label: "Apple Music" },
  { value: "amazon", label: "Amazon Music" },
  { value: "youtube", label: "YouTube Music" },
  { value: "tidal", label: "Tidal" },
  { value: "deezer", label: "Deezer" },
  { value: "other", label: "Other" },
];

export type AssetType =
  | "master"
  | "stem"
  | "artwork"
  | "video"
  | "document"
  | "other";

export type DigitalAsset = {
  id: number;
  label: number;
  artist: number | null;
  artist_name: string;
  release: number | null;
  release_title: string;
  track: number | null;
  track_title: string;
  asset_type: AssetType;
  asset_type_display: string;
  title: string;
  version_label: string;
  file: string;
  file_url: string;
  notes: string;
  uploaded_by: number | null;
  uploaded_by_username: string;
  created_at: string;
  updated_at: string;
};

export const ASSET_TYPES: { value: AssetType; label: string }[] = [
  { value: "master", label: "Master audio" },
  { value: "stem", label: "Stem" },
  { value: "artwork", label: "Artwork" },
  { value: "video", label: "Video" },
  { value: "document", label: "Document" },
  { value: "other", label: "Other" },
];
