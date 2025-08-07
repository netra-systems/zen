export function getToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const match = document.cookie.match(new RegExp('(^| )access_token=([^;]+)'));
  if (match) {
    return match[2];
  }
  return null;
}
