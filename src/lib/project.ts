/**
 * Project metadata sourced from `src/revenue_signal_copilot/project.json`.
 * Hardcoded as a TS module so it ships in the static bundle without runtime
 * file-system access.
 */

export interface ProjectSpec {
  slug: string;
  name: string;
  category: string;
  track: string;
  stage: string;
  summary: string;
  problem: string;
  users: string;
  stack: string[];
  why_now: string;
  mvp: string[];
  github_url: string;
  /** Slug returned by the system's `/api/stats` endpoint. */
  system_slug: string;
}

export const PROJECT: ProjectSpec = {
  slug: "revenue-signal-copilot",
  name: "Revenue Signal Copilot",
  category: "Business Tool",
  track: "AI/ML",
  stage: "Ready to build",
  summary:
    "A lead intelligence and prioritization system that scores accounts using public signals and internal notes.",
  problem:
    "Outbound teams chase low-signal leads because enrichment and prioritization are fragmented across tools.",
  users: "Sales teams, agencies, founder-led GTM teams",
  stack: ["Python", "FastAPI", "Pandas", "PostgreSQL", "LLMs"],
  why_now:
    "Small teams need leverage from AI systems that can turn scattered signals into action.",
  mvp: [
    "Ingest CRM exports and website data",
    "Score leads with transparent factors",
    "Generate account briefs and outreach angles",
    "Track conversion feedback to refine scoring",
  ],
  github_url: "https://github.com/IgnazioDS/revenue-signal-copilot",
  system_slug: "revenue-signal-copilot",
};
