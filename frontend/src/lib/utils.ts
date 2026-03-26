import { formatDistanceToNow } from 'date-fns';

export function formatTimeAgo(dateString: string | null | undefined): string {
  if (!dateString) return '\u2014';
  try {
    // Backend stores naive UTC timestamps — ensure JS parses them as UTC
    const utcString = dateString.endsWith('Z') || dateString.includes('+') ? dateString : dateString + 'Z';
    return formatDistanceToNow(new Date(utcString), { addSuffix: true });
  } catch {
    return '\u2014';
  }
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || seconds <= 0) return '\u2014';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

export function formatDate(dateString: string): string {
  try {
    const utcString = dateString.endsWith('Z') || dateString.includes('+') ? dateString : dateString + 'Z';
    return new Date(utcString).toLocaleDateString('en-AU', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}

export function formatTime(dateString: string): string {
  try {
    const utcString = dateString.endsWith('Z') || dateString.includes('+') ? dateString : dateString + 'Z';
    return new Date(utcString).toLocaleTimeString('en-AU', {
      hour: 'numeric',
      minute: 'numeric',
    });
  } catch {
    return '';
  }
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback: create a temporary textarea
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      return true;
    } catch {
      return false;
    } finally {
      document.body.removeChild(textarea);
    }
  }
}
