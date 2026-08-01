// Typed fetch wrappers for every REST route.

import type {
  AppSettings,
  FileMeta,
  SessionDetail,
  SessionSummary,
} from './types'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      if (body.detail) detail = body.detail
    } catch {
      /* not json */
    }
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  listSessions: () => request<SessionSummary[]>('/api/sessions'),
  createSession: () =>
    request<SessionSummary>('/api/sessions', { method: 'POST', body: '{}' }),
  getSession: (id: string) => request<SessionDetail>(`/api/sessions/${id}`),
  renameSession: (id: string, title: string) =>
    request(`/api/sessions/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  deleteSession: (id: string) =>
    request<void>(`/api/sessions/${id}`, { method: 'DELETE' }),

  sendMessage: (sessionId: string, content: string) =>
    request<{ run_id: string }>(`/api/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),

  startBuild: (sessionId: string) =>
    request<{ build_id: string }>(`/api/sessions/${sessionId}/builds`, {
      method: 'POST',
    }),
  getBuild: (buildId: string) => request<Record<string, unknown>>(`/api/builds/${buildId}`),
  cancelBuild: (buildId: string) =>
    request<{ ok: boolean }>(`/api/builds/${buildId}/cancel`, { method: 'POST' }),

  listFiles: (buildId: string) => request<FileMeta[]>(`/api/builds/${buildId}/files`),
  getFile: (buildId: string, filename: string) =>
    request<{ filename: string; content: string; revision: number }>(
      `/api/builds/${buildId}/files/${filename}`),
  putFile: (buildId: string, filename: string, content: string) =>
    request<{ filename: string; revision: number }>(
      `/api/builds/${buildId}/files/${filename}`,
      { method: 'PUT', body: JSON.stringify({ content }) }),

  exportToDesktop: (buildId: string) =>
    request<{ path: string }>(`/api/builds/${buildId}/export-to-desktop`, {
      method: 'POST',
    }),

  getSettings: () => request<AppSettings>('/api/settings'),
  putSettings: (settings: AppSettings) =>
    request<AppSettings>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),

  fetchModels: (base_url: string, api_key: string) =>
    request<{ models: string[]; source: string }>('/api/models/fetch', {
      method: 'POST',
      body: JSON.stringify({ base_url, api_key }),
    }),

  shutdown: () => request<{ ok: boolean }>('/api/shutdown', { method: 'POST' }),
}
