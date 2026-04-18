/** TypeScript interfaces matching the Python Pydantic models. */

export interface Config {
  provider: string;
  language: string;
  keep_media: boolean;
  output_format: string;
  diarize: boolean;
  prompt_download: string;
  local_file_media: string;
  workspace_path: string;
  local_model: string;
  instagram: { username: string };
  _resolved_workspace?: string;
}

export interface Provider {
  name: string;
  description: string;
  has_key: boolean;
  set_up: boolean;
  key_url?: string;
}

export interface ModelSpec {
  download_mb: number;
  ram_mb: number;
  relative_speed: string;
  quality: string;
}

export interface LocalModelEntry {
  size: string;
  cached: boolean;
  bytes: number;
  repo: string;
  spec: ModelSpec;
  downloading?: boolean;
  queued?: boolean;
  queue_position?: number;
  error?: string | null;
  last_error?: string | null;
}

export interface LocalStatusResponse {
  set_up: boolean;
  faster_whisper_installed: boolean;
  faster_whisper_version: string | null;
  ffmpeg_ok: boolean;
  ffmpeg_message: string;
  default_model: string;
  models: LocalModelEntry[];
  total_disk_bytes: number;
  install_method: string;
  setup_running: boolean;
  setup_phase: string | null;
  setup_error: string | null;
  setup_last_model: string | null;
  recommended_model: string;
  choices: string[];
}

export interface LocalModelsResponse {
  default: string;
  faster_whisper_installed: boolean;
  total_disk_bytes: number;
  models: LocalModelEntry[];
  queue?: string[];
}

export interface OnboardingStatus {
  completed: boolean;
  has_workspace: boolean;
  has_any_api_key: boolean;
  local_ready: boolean;
  provider_keys: Record<string, boolean>;
  current_provider: string;
  recommended_next_step: string;
}

export interface OnboardingPayload {
  provider: string;
  api_key?: string;
  workspace?: string;
  language?: string;
  keep_media?: boolean;
  output_format?: string;
  local_model?: string;
  extra_api_keys?: Record<string, string>;
  instagram_username?: string;
  instagram_password?: string;
}

export interface OnboardingResult {
  status: "onboarded" | "partial";
  provider: string;
  workspace: string;
  local_enabled: boolean;
  api_keys_set: string[];
  skill_installed: boolean;
  local_setup: unknown;
  config_file: string;
}

export interface SetupLogResponse {
  lines: string[];
  total: number;
  running: boolean;
}

export interface ProviderTestCheck {
  ok: boolean;
  message: string;
  size?: string;
}

export interface ProviderTestResult {
  success: boolean;
  message: string;
  checks?: {
    faster_whisper: ProviderTestCheck;
    ffmpeg: ProviderTestCheck;
    model_cached: ProviderTestCheck;
  };
}

export interface LanguageOption {
  code: string;
  name: string;
}

export interface ProviderLanguagesResponse {
  languages: LanguageOption[];
  freeform: boolean;
}

export interface TranscribeRequest {
  url: string;
  provider?: string;
  language?: string;
  diarize?: boolean;
  keep_media?: boolean;
  output_format?: string;
}

export interface ProgressEvent {
  step: string;   // download, transcribe, write, index, done, error
  status: string;  // started, completed, error
  message: string;
  percent?: number;
  data?: Record<string, unknown>;
}

export interface TranscriptMeta {
  id: string;
  title: string;
  date: string;
  platform: string;
  duration: string;
  language: string;
  word_count: number;
  provider: string;
  source_url: string;
  file_path: string;
  diarized: boolean;
}

export interface TranscriptDetail {
  id: string;
  frontmatter: Record<string, unknown>;
  body: string;
  file_path: string;
}

export interface JobResult {
  file_path: string;
  title: string;
  platform: string;
  duration: string;
  language: string;
  word_count: number;
  provider: string;
}

export interface WorkspaceInfo {
  path: string;
  file_count: number;
  total_words: number;
}
