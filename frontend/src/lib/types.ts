export type Role = "creator" | "entrepreneur" | "admin";
export interface User { id: number; email: string; full_name: string; role: Role; is_active: boolean; is_verified: boolean; created_at: string; last_login_at?: string | null }
export interface UserBrief { id: number; name: string; role: Role; headline: string; is_verified: boolean }
export interface Scores { technical_feasibility: number; market_opportunity: number; innovation_differentiation: number; overall: number; mode: string | null; evaluated_at: string | null }
export interface MatchInfo { score: number; reasons: string[]; breakdown: Record<string, { score: number; max: number; reason: string }> }
export interface IdeaCard {
  id: number; title: string; short_description: string; industry: string; technologies: string[]; stage: string;
  visibility: "public" | "restricted" | "private"; created_at: string; updated_at: string; access: "full" | "teaser";
  creator: UserBrief; scores: Scores | null; is_saved: boolean; my_request: { id: number; status: string } | null;
  funding_needed: number | null; moderation_status?: string; relevance?: number; match?: MatchInfo; pending_requests?: number;
  evaluation?: { id: number; status: string; progress: number; mode: string | null } | null;
}
export interface IdeaDoc { id: number; filename: string; size: number; content_type: string; uploaded_at: string }
export interface IdeaDetail extends IdeaCard {
  problem?: string; solution?: string; target_audience?: string; expected_impact?: string; business_potential?: string;
  documents?: IdeaDoc[]; latest_evaluation?: { id: number; status: string; stage: string; progress: number } | null;
}
export interface SimilarProject { ref_id: string; kind: string; title: string; url: string | null; similarity_pct: number; key_differences: string; is_competitor?: boolean }
export interface Report {
  meta: { mode: "demo" | "live_llm"; provider: string; model: string; notice: string | null; generated_at: string; fallback_reason?: string; embedding?: { name: string; kind: string } };
  idea_summary: string; problem_statement: string; proposed_solution: string; similar_projects: SimilarProject[];
  novelty_assessment: { level: string; rationale: string };
  scores: { technical_feasibility: number; market_opportunity: number; innovation_differentiation: number; overall: number };
  development_complexity: { level: string; rationale: string }; target_users: string[]; revenue_models: string[];
  competitors: { ref_id: string; name: string; url: string | null; similarity_pct: number }[];
  strengths: string[]; weaknesses: string[]; risks: string[]; recommended_improvements: string[]; overall_evaluation: string;
  evidence: { retrieved_count: number; max_similarity_pct: number; reference_projects_searched: number; platform_ideas_searched: number; research_papers_searched: number; similarity_method: string; limitation: string };
}
export interface Evaluation {
  id: number; idea_id: number; version: number; status: "queued" | "running" | "completed" | "failed"; stage: string; progress: number;
  mode: string | null; provider: string | null; model: string | null; error: string | null; created_at: string; completed_at: string | null;
  outdated: boolean; scores: Scores | null; report?: Report; idea_title?: string;
}
export interface Collab { id: number; idea_id: number; idea_title: string; kind: string; message: string; status: string; response_message: string; created_at: string; entrepreneur: UserBrief; creator: UserBrief }
export interface Conversation { user_id: number; user: UserBrief; last_message: string; last_at: string; last_from_me: boolean; unread: number }
export interface Msg { id: number; sender_id: number; body: string; idea_id: number | null; created_at: string }
export interface Notice { id: number; kind: string; title: string; body: string; link: string | null; is_read: boolean; created_at: string }
export interface Categories { industries: { id: number; name: string; description: string }[]; technologies: { id: number; name: string; description: string }[] }
export interface SystemStatus { evaluation_mode: "demo" | "live_llm"; llm_provider: string | null; llm_model: string | null; embedding: { name: string; kind: string; model: string }; external_retrieval: string; demo_notice: string | null }
export interface Paged<T> { items: T[]; total: number; page: number; page_size?: number }
export const STAGES = ["concept", "research", "prototype", "mvp", "launched"] as const;
export const STAGE_LABEL: Record<string, string> = { concept: "Concept", research: "Research", prototype: "Prototype", mvp: "MVP", launched: "Launched" };
