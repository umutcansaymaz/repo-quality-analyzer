/**
 * Comparator — ground truth vs actual categories.
 * Shared by audit/run.mjs and tests/audit.test.ts.
 *
 * precision = matched / actual   (1 = no false positives)
 * recall    = matched / expected (1 = no false negatives)
 */

export function compare(expected, actualCategories) {
  const exp = new Set(expected.map((e) => e.toLowerCase()));
  const act = new Set(actualCategories.map((c) => c.toLowerCase()));
  const matched = [...act].filter((a) => exp.has(a));
  const missing = [...exp].filter((e) => !act.has(e));
  const extra = [...act].filter((a) => !exp.has(a));
  return {
    precision: act.size > 0 ? matched.length / act.size : exp.size === 0 ? 1 : 0,
    recall: exp.size > 0 ? matched.length / exp.size : act.size === 0 ? 1 : 1,
    missing,
    extra,
  };
}
