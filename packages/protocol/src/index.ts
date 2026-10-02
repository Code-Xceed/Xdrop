import {
  DownloadJob,
  ResolveStatus,
  AppSettings,
  DownloadStatus,
} from '@xdrop/shared-types';

export type ServerMessageType =
  | 'JOB_CREATED'
  | 'JOB_UPDATED'
  | 'JOB_PROGRESS'
  | 'JOB_COMPLETED'
  | 'JOB_FAILED'
  | 'JOB_REMOVED'
  | 'RESOLVE_STATUS_CHANGED'
  | 'SETTINGS_UPDATED'
  | 'PONG'
  | 'ERROR';

export interface BaseServerMessage {
  type: ServerMessageType;
  timestamp: string;
}

export interface JobProgressPayload {
  id: string;
  status: DownloadStatus;
  progress: number;
  speed?: string;
  eta?: string;
  downloadedBytes: number;
  totalBytes?: number;
  errorMessage?: string;
  resolveImported?: boolean;
}

export interface ServerMessage extends BaseServerMessage {
  payload:
    | { job: DownloadJob }
    | { progress: JobProgressPayload }
    | { resolveStatus: ResolveStatus }
    | { settings: AppSettings }
    | { jobId: string }
    | { message: string; code?: string };
}

export type ClientMessageType =
  | 'PING'
  | 'CANCEL_JOB'
  | 'PAUSE_JOB'
  | 'RESUME_JOB'
  | 'RETRY_JOB'
  | 'REMOVE_JOB'
  | 'TRIGGER_RESOLVE_IMPORT'
  | 'CHECK_RESOLVE';

export interface ClientMessage {
  type: ClientMessageType;
  jobId?: string;
  timestamp?: string;
}
