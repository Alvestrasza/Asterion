export function matchesExpectedActor(expected: string | null | undefined, actual: string): boolean {
  return Boolean(expected) && expected === actual;
}
