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
  instagram: { username: string };
  _resolved_workspace?: string;
}

export interface Provider {
  name: string;
  description: string;
  has_key: boolean;
  key_url?: string;
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
