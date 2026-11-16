export type MigrationPhase =
  | "initialize"
  | "planning"
  | "synthesizing"
  | "sandbox_testing"
  | "reflecting"
  | "human_review"
  | "verified"
  | "failed"
  | "escalated";

export interface ToolTrace {
  tool_name: string;
  args: Record<string, any>;
  execution_time_ms: number;
  success: boolean;
  output_summary: string;
}

export interface DiffHunk {
  file_path: string;
  diff_text: string;
  target_symbol?: string;
  explanation?: string;
}

export interface ReflectionFeedback {
  iteration: number;
  root_cause_analysis: string;
  suggested_patch_adjustments: string[];
  target_files_to_remediate: string[];
}

export interface MigrationState {
  task_id: string;
  repo_path: string;
  recipe: string;
  phase: MigrationPhase;
  plan?: {
    recipe: string;
    steps: Array<{
      step_number: number;
      file_path: string;
      transformation_description: string;
      target_symbol_ids: string[];
    }>;
    affected_files: string[];
  };
  patches: DiffHunk[];
  reflections: ReflectionFeedback[];
  tool_traces: ToolTrace[];
  retry_count: number;
  max_retries: number;
  error_message?: string;
  is_terminal: boolean;
}
