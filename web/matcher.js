// Port of src/safety_law_mapper/matcher.py for the offline static demo.
//
// This file exists only so the GitHub Pages demo can run with no server. It
// is a second implementation of the ranking, which is exactly the kind of
// thing that drifts — so tests/test_web_parity.py runs both against the
// golden fixtures and fails when they disagree. Do not change the ranking
// here without changing matcher.py; the test will catch you either way.
//
// When the page is served by `slm-serve`, it calls GET /search instead and
// none of this runs.

const EXACT_WEIGHT = 2;
const PARTIAL_WEIGHT = 1;

export function keywordScore(mapping, queryKeywords) {
  let score = 0;
  const eks = mapping.work_type.keywords;
  for (const qk of queryKeywords) {
    if (eks.includes(qk)) {
      score += EXACT_WEIGHT;
    } else if (eks.some((ek) => ek.includes(qk) || qk.includes(ek))) {
      score += PARTIAL_WEIGHT;
    } else if (mapping.work_type.name_ko.includes(qk)) {
      score += PARTIAL_WEIGHT;
    }
  }
  return score;
}

export function specificity(cond) {
  if (!cond) return 0;
  let n = 0;
  if (cond.min_employees != null) n += 1;
  if (cond.max_employees != null) n += 1;
  n += (cond.substances || []).length + (cond.equipment || []).length;
  return n;
}

// A mapping is excluded only when the query explicitly contradicts its
// conditions. An absent query field means "no constraint given", never a
// reason to drop a result.
export function conditionsAllow(cond, query) {
  if (!cond) return true;
  const { employees = null, substances = [], equipment = [] } = query;
  if (employees != null) {
    if (cond.min_employees != null && employees < cond.min_employees) return false;
    if (cond.max_employees != null && employees > cond.max_employees) return false;
  }
  const overlaps = (a, b) => a.some((x) => b.includes(x));
  if (substances.length && (cond.substances || []).length) {
    if (!overlaps(substances, cond.substances)) return false;
  }
  if (equipment.length && (cond.equipment || []).length) {
    if (!overlaps(equipment, cond.equipment)) return false;
  }
  return true;
}

// Ranking: category match, then keyword score, then condition specificity,
// then mapping_id so the order is deterministic.
export function match(mappings, query) {
  const { keywords = [], category = null } = query;
  const results = [];
  for (const m of mappings) {
    if (!conditionsAllow(m.conditions, query)) continue;
    const catMatch = !!category && m.work_type.category === category;
    const ks = keywords.length ? keywordScore(m, keywords) : 0;
    if (!catMatch && ks === 0) continue;
    results.push({
      mapping: m,
      category_match: catMatch,
      keyword_score: ks,
      specificity: specificity(m.conditions),
    });
  }
  results.sort(
    (a, b) =>
      b.category_match - a.category_match ||
      b.keyword_score - a.keyword_score ||
      b.specificity - a.specificity ||
      (a.mapping.mapping_id < b.mapping.mapping_id ? -1 : a.mapping.mapping_id > b.mapping.mapping_id ? 1 : 0),
  );
  return results;
}
