export interface FileExtensionInfo {
  extension: string // ex: ".jpg", ".pdf"
  count: number
  default_folder: string
  is_unmapped: boolean
}

export interface ScanRequest {
  path: string
}

export interface ScanResult {
  extensions: FileExtensionInfo[]
  total_files: number
  scan_path: string
}

export type ExtensionMapping = Record<string, string> // ".jpg" → "Images"

export interface OrganizeRequest {
  source_path: string
  destination_path: string
  extension_map: ExtensionMapping
  dry_run?: boolean
}

export interface OrganizeJob {
  job_id: string
  status: 'pending' | 'running' | 'complete' | 'error'
  progress: number // 0–100
  processed_files: number
  total_files: number
  errors: string[]
}

export interface ApiErrorBody {
  code: string
  message: string
  detail?: unknown
}
