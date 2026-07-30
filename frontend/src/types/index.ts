export interface User {
  id: string
  email: string
  full_name: string | null
  role: string
  company: string | null
  is_active: boolean
  created_at: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface Project {
  id: string
  name: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Target {
  id: string
  project_id: string
  name: string
  url: string
  target_type: string
  description: string | null
  is_active: boolean
  javascript_enabled: boolean
  timeout_ms: number
  created_at: string
  updated_at: string
  tags: string[] | null
}

export interface Job {
  id: string
  project_id: string
  url: string
  status: JobStatus
  priority: number
  retry_count: number
  max_retries: number
  duration_ms: number | null
  error_message: string | null
  error_type: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
  tags: string[] | null
  runs?: Run[]
  scrape_results?: ScrapeResult[]
  extraction_results?: ExtractionResult[]
}

export type JobStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'retrying'
  | 'cancelled'
  | 'blocked'
  | 'rate_limited'
  | 'captcha_required'

export interface Run {
  id: string
  job_id: string
  status: string
  attempt_number: number
  url: string
  total_time_ms: number | null
  http_status_code: number | null
  captcha_detected: boolean
  blocked_detected: boolean
  error_message: string | null
  created_at: string
}

export interface ScrapeResult {
  id: string
  job_id: string
  url: string
  title: string | null
  status_code: number | null
  cleaned_text: string | null
  load_time_ms: number | null
  captcha_detected: boolean
  blocked_detected: boolean
  links: Record<string, string>[] | null
  created_at: string
}

export interface ExtractionResult {
  id: string
  job_id: string
  extracted_data: Record<string, unknown> | null
  structured_output: Record<string, unknown> | null
  confidence_score: number | null
  llm_model: string | null
  tokens_total: number | null
  success: boolean
  created_at: string
}

export interface Proxy {
  id: string
  host: string
  port: number
  protocol: string
  status: ProxyStatus
  latency_ms: number | null
  success_count: number
  failure_count: number
  consecutive_failures: number
  country: string | null
  isp: string | null
  weight: number
  is_usable: boolean
  url: string
  created_at: string
  updated_at: string
}

export type ProxyStatus = 'active' | 'inactive' | 'banned' | 'checking' | 'rate_limited' | 'error'

export interface Schedule {
  id: string
  project_id: string
  name: string
  url: string
  interval: string
  description: string | null
  is_active: boolean
  last_run_at: string | null
  next_run_at: string | null
  max_runs: number
  runs_so_far: number
  created_at: string
  updated_at: string
}

export interface Stats {
  total_jobs: number
  active_jobs: number
  completed_24h: number
  failed_24h: number
  success_rate_24h: number
  total_proxies: number
  active_proxies: number
  timestamp: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface ApiKey {
  id: string
  name: string
  key_prefix: string
  key?: string
  is_active: boolean
  created_at: string
}
