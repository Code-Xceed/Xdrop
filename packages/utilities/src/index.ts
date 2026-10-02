/**
 * Shared utility functions: formatting, string sanitization, and URL helpers
 */

const WINDOWS_RESERVED_NAMES = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$/i;
const INVALID_FILENAME_CHARS = /[<>:"/\\|?*\x00-\x1F]/g;

/**
 * Sanitize a string to be safely used as a filename across all OSes (especially Windows).
 */
export function sanitizeFilename(input: string, fallback = 'untitled_asset'): string {
  if (!input || !input.trim()) {
    return fallback;
  }

  let sanitized = input
    .replace(INVALID_FILENAME_CHARS, '_')
    .replace(/\s+/g, ' ')
    .trim();

  // Strip trailing dots and spaces (Windows restriction)
  sanitized = sanitized.replace(/[. ]+$/, '');

  if (WINDOWS_RESERVED_NAMES.test(sanitized)) {
    sanitized = `${sanitized}_asset`;
  }

  // Cap length to avoid MAX_PATH issues
  if (sanitized.length > 120) {
    sanitized = sanitized.substring(0, 120).trim();
  }

  return sanitized || fallback;
}

/**
 * Format bytes to human readable format (e.g. 14.2 MB)
 */
export function formatBytes(bytes?: number | null, decimals = 1): string {
  if (bytes === undefined || bytes === null || isNaN(bytes) || bytes < 0) {
    return '0 B';
  }
  if (bytes === 0) return '0 B';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

/**
 * Format duration in seconds to mm:ss or hh:mm:ss
 */
export function formatDuration(seconds?: number | null): string {
  if (seconds === undefined || seconds === null || isNaN(seconds) || seconds < 0) {
    return '00:00';
  }

  const sec = Math.floor(seconds);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;

  const mm = m.toString().padStart(2, '0');
  const ss = s.toString().padStart(2, '0');

  if (h > 0) {
    return `${h.toString().padStart(2, '0')}:${mm}:${ss}`;
  }
  return `${mm}:${ss}`;
}

/**
 * Validate that a string is an HTTP or HTTPS URL
 */
export function isValidHttpUrl(stringToTest: string): boolean {
  try {
    const url = new URL(stringToTest.trim());
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch (_) {
    return false;
  }
}

/**
 * Extract URLs from a multi-line or text block input
 */
export function extractUrlsFromText(text: string): string[] {
  if (!text) return [];
  const lines = text.split(/[\r\n\s]+/);
  const urls: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && isValidHttpUrl(trimmed)) {
      if (!urls.includes(trimmed)) {
        urls.push(trimmed);
      }
    }
  }

  return urls;
}
