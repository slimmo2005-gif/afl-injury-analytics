/** Count words for feedback length limits. */
export function countWords(text: string): number {
  return text.trim().split(/\s+/).filter((w) => w.length > 0).length
}
