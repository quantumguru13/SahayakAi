// Strict TypeScript interfaces mirroring the FastAPI Pydantic models (1:1).

export type PriorityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type TaskStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED";
export type GovernmentIdType = "Aadhaar" | "PAN" | "Ration Card" | "Voter ID";

export interface CriticalDeadline {
  date: string;
  context: string;
}

export interface ExtractedDocument {
  beneficiary_name: string | null;
  government_id_type: GovernmentIdType | null;
  government_id_number: string | null;
  critical_deadlines: CriticalDeadline[];
  detected_medical_conditions: string[];
  estimated_household_income: number | null;
  age?: number | null;
  gender?: string | null;
  state_location?: string | null;
  is_disabled?: boolean;
  dob?: string | null;
  address?: string | null;
}

export type PipelineMode = "LIVE" | "DEMO";

export type AadhaarSide = "front" | "back" | "combined" | "unknown";
export type VerificationStatus = "VERIFIED" | "MANUAL_REVIEW" | "NOT_AADHAAR";

export interface AadhaarFields {
  full_name: string | null;
  /** Always masked server-side: "XXXX XXXX 1234". */
  aadhaar_number: string | null;
  date_of_birth: string | null;
  year_of_birth: number | null;
  gender: string | null;
  address: string | null;
  state: string | null;
  district: string | null;
  pin_code: string | null;
  mobile: string | null;
  qr_detected: boolean;
  qr_preview: string | null;
  side: AadhaarSide;
}

export interface AadhaarVerification {
  status: VerificationStatus;
  checks: Record<string, boolean>;
  reasons: string[];
  missing_fields: string[];
  manual_review: boolean;
  front_back_conflicts: string[];
}

export interface AadhaarAnalysis {
  fields: AadhaarFields;
  verification: AadhaarVerification;
  ocr_confidence: number;
  low_confidence: boolean;
}

export interface UploadHistoryEntry {
  session_id: string;
  created_at: string;
  document_type: string;
  mode: PipelineMode;
  ocr_engine: string;
  processing_ms: number;
  status: string;
  verification_status: string | null;
  user_id: string;
  user_role: string;
  file_name: string;
  beneficiary_id: string | null;
}

export interface PipelineDebug {
  mode: PipelineMode;
  ocr_engine: string;
  ocr_confidence: number;
  extraction_confidence: number;
  ai_status: string;
  scheme_matching_status: string;
  engines_attempted: string[];
  original_image: string | null;
  preprocessed_image: string | null;
  notes: string[];
}

export interface UrgencyAssessment {
  priority: PriorityLevel;
  score: number;
  reasoning: string;
  medical_severity: number;
  deadline_pressure: number;
}

export interface Beneficiary {
  id: string;
  name: string;
  age: number | null;
  gender: string | null;
  annual_income: number | null;
  state_location: string | null;
  is_disabled: boolean;
  government_id_type: GovernmentIdType | null;
  government_id_number_masked: string | null;
  medical_conditions: string[];
  current_priority: PriorityLevel;
  urgency: UrgencyAssessment | null;
  created_at: string;
  source?: string;
}

export interface WelfareScheme {
  id: string;
  title: string;
  description: string;
  eligibility_criteria_summary: string;
  category: string;
  created_at: string;
}

export interface SchemeMatch {
  scheme: WelfareScheme;
  confidence: number;
  semantic_similarity: number;
  rule_score: number;
  matched_reasons: string[];
  is_alternative: boolean;
}

export interface Task {
  id: string;
  beneficiary_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  status: TaskStatus;
  created_at: string;
}

export interface DashboardMetrics {
  total_beneficiaries: number;
  critical_cases: number;
  high_cases: number;
  pending_tasks: number;
  overdue_tasks: number;
  schemes_available: number;
}

export interface BriefAction {
  beneficiary_id: string | null;
  beneficiary_name: string | null;
  action: string;
  reason: string;
  priority: PriorityLevel;
}

export interface DailyBrief {
  generated_at: string;
  headline: string;
  summary_markdown: string;
  top_actions: BriefAction[];
  metrics: DashboardMetrics;
  system_healthy: boolean;
}

export interface DocumentUploadResponse {
  document_id: string;
  beneficiary: Beneficiary;
  extraction: ExtractedDocument;
  urgency: UrgencyAssessment;
  extracted_text: string;
  processing_ms: number;
  scheme_matches: SchemeMatch[];
  generated_tasks: Task[];
  demo_mode: boolean;
  mode: PipelineMode;
  debug: PipelineDebug | null;
  /** Present only when the upload was recognised as an Aadhaar document. */
  aadhaar: AadhaarAnalysis | null;
  session_id: string | null;
}

export interface OcrUnavailableResponse {
  ocr_available: false;
  mode: PipelineMode;
  message: string;
  engines_attempted: string[];
  can_switch_to_demo: boolean;
}

export type UploadResult = DocumentUploadResponse | OcrUnavailableResponse;

export function isOcrUnavailable(
  r: UploadResult
): r is OcrUnavailableResponse {
  return (r as OcrUnavailableResponse).ocr_available === false;
}

export interface ImpactReport {
  generated_at: string;
  title: string;
  period: string;
  markdown: string;
  stats: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  demo_mode: boolean;
  openai_configured: boolean;
  supabase_configured: boolean;
  auth_enabled?: boolean;
  default_mode?: PipelineMode;
  live_ocr_available?: boolean;
  ocr_engines?: string[];
  active_mode?: PipelineMode;
}
