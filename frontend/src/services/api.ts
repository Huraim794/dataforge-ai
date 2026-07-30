import type { AuthTokens, Project, Target, Job, Proxy, Schedule, Stats, PaginatedResponse, ExtractionResult } from '../types'

const BASE_URL = '/api/v1'

let accessToken: string | null = localStorage.getItem('access_token')
let refreshPromise: Promise<boolean> | null = null

export function setTokens(access: string, refresh: string) {
  accessToken = access
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}

export function clearTokens() {
  accessToken = null
  refreshPromise = null
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export function isAuthenticated(): boolean {
  return !!accessToken
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`
      const retry = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers,
      })
      if (!retry.ok) {
        throw new ApiError(await retry.json(), retry.status)
      }
      return retry.json()
    }
    clearTokens()
    throw new ApiError({ error: 'Unauthorized' }, 401)
  }

  if (!response.ok) {
    throw new ApiError(await response.json(), response.status)
  }

  if (response.status === 204) return {} as T
  return response.json()
}

async function tryRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return false

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      })
      if (response.ok) {
        const data: AuthTokens = await response.json()
        setTokens(data.access_token, data.refresh_token)
        return true
      }
    } catch {
      return false
    } finally {
      refreshPromise = null
    }
    return false
  })()

  return refreshPromise
}

export class ApiError extends Error {
  constructor(public data: Record<string, unknown>, public status: number) {
    super((data?.message as string) || (data?.error as string) || 'API Error')
  }
}

// Auth
export const auth = {
  login: (email: string, password: string) =>
    request<AuthTokens & { expires_in: number }>(
      '/auth/login',
      { method: 'POST', body: JSON.stringify({ email, password }) }
    ),
  register: (data: { email: string; password: string; full_name: string }) =>
    request<{ id: string; email: string }>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request<{ id: string; email: string; full_name: string | null; role: string }>('/auth/me'),
  listApiKeys: () => request<Array<{ id: string; name: string; key_prefix: string; is_active: boolean; created_at: string }>>('/auth/api-keys'),
  createApiKey: (name: string) =>
    request<{ id: string; name: string; key: string }>(`/auth/api-keys?name=${encodeURIComponent(name)}`, { method: 'POST' }),
  deleteApiKey: (id: string) =>
    request<void>(`/auth/api-keys/${id}`, { method: 'DELETE' }),
}

// Projects
export const projects = {
  list: () => request<Project[]>('/projects'),
  create: (data: { name: string; description?: string }) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => request<Project & { member_count?: number; target_count?: number; job_count?: number }>(`/projects/${id}`),
  update: (id: string, data: Partial<Project>) =>
    request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => request<void>(`/projects/${id}`, { method: 'DELETE' }),
}

// Targets
export const targets = {
  list: (projectId: string) =>
    request<Target[]>(`/targets?project_id=${projectId}`),
  create: (data: Partial<Target> & { project_id: string; name: string; url: string }) =>
    request<Target>('/targets', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => request<Target>(`/targets/${id}`),
  update: (id: string, data: Partial<Target>) =>
    request<Target>(`/targets/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => request<void>(`/targets/${id}`, { method: 'DELETE' }),
}

// Jobs
export const jobs = {
  list: (params: { project_id?: string; status?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams()
    if (params.project_id) q.set('project_id', params.project_id)
    if (params.status) q.set('status', params.status)
    if (params.page) q.set('page', String(params.page))
    if (params.page_size) q.set('page_size', String(params.page_size))
    return request<PaginatedResponse<Job>>(`/jobs?${q}`)
  },
  create: (data: Partial<Job> & { url: string; project_id: string }) =>
    request<Job>('/jobs', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => request<Job>(`/jobs/${id}`),
  cancel: (id: string) =>
    request<Job>(`/jobs/${id}/cancel`, { method: 'POST' }),
  retry: (id: string) =>
    request<Job>(`/jobs/${id}/retry`, { method: 'POST' }),
  delete: (id: string) => request<void>(`/jobs/${id}`, { method: 'DELETE' }),
  getResults: (id: string) =>
    request<{
      scrape_results: Array<{ id: string; url: string; title: string | null; status_code: number | null; cleaned_text: string | null; load_time_ms: number | null; captcha_detected: number; blocked_detected: number; links: Record<string, string>[] | null; created_at: string }>;
      extraction_results: ExtractionResult[];
    }>(`/jobs/${id}/results`),
  getRuns: (id: string) => request<Array<{ id: string; job_id: string; status: string; attempt_number: number; url: string; total_time_ms: number | null; http_status_code: number | null; error_message: string | null; created_at: string }>>(`/jobs/${id}/runs`),
}

// Proxies
export const proxies = {
  list: (params: { project_id?: string; status?: string; page?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.project_id) q.set('project_id', params.project_id)
    if (params.status) q.set('status', params.status)
    if (params.page) q.set('page', String(params.page))
    return request<PaginatedResponse<Proxy>>(`/proxies?${q}`)
  },
  create: (data: { host: string; port: number; protocol?: string; username?: string; password?: string }) =>
    request<Proxy>('/proxies', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => request<Proxy>(`/proxies/${id}`),
  delete: (id: string) => request<void>(`/proxies/${id}`, { method: 'DELETE' }),
  check: (id: string) => request<{ id: string; alive: boolean; latency_ms: number | null }>(`/proxies/${id}/check`, { method: 'POST' }),
  checkAll: () => request<{ checked: number; alive: number; dead: number }>('/proxies/check-all', { method: 'POST' }),
}

// Schedules
export const schedules = {
  list: (projectId: string) =>
    request<PaginatedResponse<Schedule>>(`/schedules?project_id=${projectId}`),
  create: (data: Partial<Schedule> & { name: string; project_id: string; url: string }) =>
    request<Schedule>('/schedules', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => request<Schedule>(`/schedules/${id}`),
  update: (id: string, data: Partial<Schedule>) =>
    request<Schedule>(`/schedules/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => request<void>(`/schedules/${id}`, { method: 'DELETE' }),
  toggle: (id: string) =>
    request<Schedule>(`/schedules/${id}/toggle`, { method: 'POST' }),
}

// Extractions
export const extractions = {
  extract: (data: { content: string; schema?: Record<string, unknown>; fields?: Array<Record<string, unknown>>; url?: string }) =>
    request<{ success: boolean; data: unknown; error?: string; processing_time_ms?: number; model_used?: string; tokens_used: number; confidence_score?: number }>('/extractions/extract', { method: 'POST', body: JSON.stringify(data) }),
  classify: (data: { content: string; categories: string[] }) =>
    request<{ success: boolean; category: string; confidence: number }>('/extractions/classify', { method: 'POST', body: JSON.stringify(data) }),
  extractContacts: (content: string) =>
    request<{ success: boolean; contacts: Array<Record<string, unknown>> }>(`/extractions/extract-contacts?content=${encodeURIComponent(content)}`, { method: 'POST' }),
  getResult: (id: string) =>
    request<ExtractionResult>(`/extractions/results/${id}`),
}

// Monitoring
export const monitoring = {
  health: () => request<{ status: string; version: string; uptime_seconds: number }>('/monitoring/health'),
  stats: () => request<Stats>('/monitoring/stats'),
  queueStatus: () => request<Record<string, number>>('/monitoring/queue-status'),
}
