import { request } from './client'
import type { ScanResult, OrganizeRequest, OrganizeJob, ExtensionMapping } from '@/types/organizer'

export const organizerApi = {
  scan(path: string, signal?: AbortSignal): Promise<ScanResult> {
    return request<ScanResult>('/api/scan', {
      method: 'POST',
      body: JSON.stringify({ path }),
      signal,
    })
  },

  startOrganize(options: OrganizeRequest, signal?: AbortSignal): Promise<{ job_id: string }> {
    return request<{ job_id: string }>('/api/organize', {
      method: 'POST',
      body: JSON.stringify(options),
      signal,
    })
  },

  getJobStatus(jobId: string, signal?: AbortSignal): Promise<OrganizeJob> {
    return request<OrganizeJob>(`/api/organize/${jobId}/status`, { signal })
  },

  getConfig(signal?: AbortSignal): Promise<{ extension_map: ExtensionMapping }> {
    return request<{ extension_map: ExtensionMapping }>('/api/config', {
      signal,
    })
  },

  updateConfig(
    map: ExtensionMapping,
    signal?: AbortSignal
  ): Promise<{ extension_map: ExtensionMapping }> {
    return request<{ extension_map: ExtensionMapping }>('/api/config', {
      method: 'PUT',
      body: JSON.stringify({ extension_map: map }),
      signal,
    })
  },
}
