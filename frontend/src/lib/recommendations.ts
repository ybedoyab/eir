import type { IconName } from "@/components/ui/Icon";
import {
  BASELINE_RECOVERY_GUIDANCE,
  RECOVERY_RECOMMENDATION_CATEGORIES,
  RECOVERY_RECOMMENDATION_FALLBACK,
  type RecoveryRecommendationCategory,
} from "@/config/recovery";

export type RecommendationSource = "care-plan" | "general";

export interface RecoveryRecommendation {
  text: string;
  source: RecommendationSource;
}

export interface RecommendationGroup {
  id: string;
  label: string;
  icon: IconName;
  items: RecoveryRecommendation[];
}

/** First matching category wins; anything unrecognised stays under the neutral fallback. */
export function categorize(text: string): RecoveryRecommendationCategory {
  return (
    RECOVERY_RECOMMENDATION_CATEGORIES.find((category) => category.match.test(text)) ??
    RECOVERY_RECOMMENDATION_FALLBACK
  );
}

function clean(items: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of items) {
    const text = String(item ?? "").trim();
    if (!text) continue;
    const key = text.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(text);
  }
  return out;
}

/**
 * Groups the episode's care-plan items by theme, then lets the generic baseline fill only
 * the themes the clinician's plan does not already speak to.
 *
 * The wording is never rewritten: care-plan text renders exactly as the clinician wrote it,
 * and the baseline lines are the fixed strings shared with the video handler. This function
 * only sorts existing sentences into buckets — it does not author clinical advice.
 */
export function buildRecommendationGroups(tasks: string[]): RecommendationGroup[] {
  const groups = new Map<string, RecommendationGroup>();

  const add = (text: string, source: RecommendationSource) => {
    const category = categorize(text);
    let group = groups.get(category.id);
    if (!group) {
      group = { id: category.id, label: category.label, icon: category.icon, items: [] };
      groups.set(category.id, group);
    }
    group.items.push({ text, source });
  };

  for (const task of clean(tasks)) {
    add(task, "care-plan");
  }

  // Baseline guidance is a gap-filler, not a second opinion: skip any theme the care plan
  // already covers so the patient never sees generic text next to their clinician's version
  // of the same instruction.
  const covered = new Set(groups.keys());
  for (const line of clean(BASELINE_RECOVERY_GUIDANCE)) {
    if (covered.has(categorize(line).id)) continue;
    add(line, "general");
  }

  const order = [
    ...RECOVERY_RECOMMENDATION_CATEGORIES.map((category) => category.id),
    RECOVERY_RECOMMENDATION_FALLBACK.id,
  ];
  return order
    .map((id) => groups.get(id))
    .filter((group): group is RecommendationGroup => Boolean(group));
}
