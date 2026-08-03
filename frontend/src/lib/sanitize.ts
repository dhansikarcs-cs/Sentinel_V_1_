import DOMPurify from "dompurify";

export function sanitize(t: string): string {
  return DOMPurify.sanitize(t, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
}
