import { http, HttpResponse } from 'msw'
import { API_BASE_URL } from '@/lib/constants'
import type { ScanResult, OrganizeJob } from '@/types/organizer'

const B = API_BASE_URL

const mockJob: OrganizeJob = {
  job_id: 'mock-job-1',
  status: 'running',
  progress: 0,
  processed_files: 0,
  total_files: 68,
  errors: [],
}

export const handlers = [
  http.post(`${B}/api/scan`, async ({ request }) => {
    const body = (await request.json()) as { path: string }
    if (!body.path) {
      return HttpResponse.json(
        { code: 'INVALID_PATH', message: 'Path is required' },
        { status: 400 }
      )
    }
    const result: ScanResult = {
      scan_path: body.path,
      total_files: 68,
      extensions: [
        { extension: '.jpg', count: 45, default_folder: 'Images', is_unmapped: false },
        { extension: '.pdf', count: 23, default_folder: 'Documents', is_unmapped: false },
      ],
    }
    return HttpResponse.json(result)
  }),

  http.post(`${B}/api/organize`, () =>
    HttpResponse.json({ job_id: mockJob.job_id }, { status: 202 })
  ),

  http.get(`${B}/api/organize/:jobId/status`, () =>
    HttpResponse.json({ ...mockJob, progress: 42, processed_files: 28 })
  ),

  http.get(`${B}/api/config`, () =>
    HttpResponse.json({
      extension_map: { '.jpg': 'Images', '.pdf': 'Documents' },
    })
  ),

  http.put(`${B}/api/config`, async ({ request }) => {
    const body = (await request.json()) as { extension_map: Record<string, string> }
    return HttpResponse.json({ extension_map: body.extension_map })
  }),
]
