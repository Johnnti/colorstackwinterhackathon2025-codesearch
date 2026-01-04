import { useState } from "react";
import { toast } from "sonner";
import { HomePage } from "./components/HomePage";
import { ResultsPage } from "./components/ResultsPage";
import { Toaster } from "./components/ui/sonner";

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ||
  "http://localhost:8000";

export type AnalysisResult = {
  pr_summary: {
    what_changed: string;
    why_it_changed: string;
    key_files: string[];
  };
  findings: Array<{
    title: string;
    severity: "critical" | "high" | "medium" | "low";
    confidence: number;
    file: string;
    line_number?: number;
    evidence: string;
    recommendation: string;
  }>;
  risk_matrix: {
    security: "high" | "medium" | "low";
    performance: "high" | "medium" | "low";
    breaking_change: "high" | "medium" | "low";
    maintainability: "high" | "medium" | "low";
  };
  test_plan: {
    unit_tests: string[];
    integration_tests: string[];
    edge_cases: string[];
  };
  merge_readiness: {
    score: number;
    blockers: string[];
    notes: string;
  };
  markdown_comment?: string | null;
};

type RunStatus = "pending" | "processing" | "completed" | "failed";

type AnalyzeInput = {
  prUrl?: string;
  diffText?: string;
  useRepoRules: boolean;
  rulesYaml?: string;
  languageHint?: string;
};

type AnalyzeResponse = {
  run_id: number;
  status: RunStatus;
  message: string;
};

type RunResultResponse = {
  run_id: number;
  status: RunStatus;
  result?: AnalysisResult | null;
  error_message?: string | null;
  model_version?: string | null;
  markdown_comment?: string | null;
};

function App() {
  const [currentView, setCurrentView] = useState<"home" | "results">("home");
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null
  );
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const pollForResult = async (runId: number): Promise<AnalysisResult> => {
    const maxAttempts = 45; // ~90s at 2s interval
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const response = await fetch(
        `${API_BASE_URL.replace(/\/$/, "")}/api/runs/${runId}/result`
      );
      const data: RunResultResponse | { detail?: string } = await response
        .json()
        .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          (data as { detail?: string }).detail ||
            "Failed to fetch analysis result"
        );
      }

      if ((data as RunResultResponse).status === "failed") {
        throw new Error(
          (data as RunResultResponse).error_message || "Analysis failed"
        );
      }

      if (
        (data as RunResultResponse).status === "completed" &&
        (data as RunResultResponse).result
      ) {
        return (data as RunResultResponse).result as AnalysisResult;
      }

      setStatusMessage("Analysis in progress...");
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }

    throw new Error("Timed out waiting for analysis result");
  };

  const handleAnalyze = async (input: AnalyzeInput) => {
    if (!input.prUrl && !input.diffText) {
      toast.error("Please provide a PR URL or a diff to analyze");
      return;
    }

    setIsAnalyzing(true);
    setStatusMessage("Submitting analysis request...");
    setAnalysisResult(null);

    try {
      const response = await fetch(
        `${API_BASE_URL.replace(/\/$/, "")}/api/analyze`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pr_url: input.prUrl || null,
            diff_text: input.diffText || null,
            options: {
              use_repo_rules: input.useRepoRules,
              rules_yaml: input.rulesYaml,
              language_hint: input.languageHint,
            },
          }),
        }
      );

      const data: AnalyzeResponse | { detail?: string } = await response
        .json()
        .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          (data as { detail?: string }).detail || "Failed to start analysis"
        );
      }

      const analyzeData = data as AnalyzeResponse;
      setStatusMessage("Analysis started. Waiting for results...");

      const result = await pollForResult(analyzeData.run_id);
      setAnalysisResult(result);
      setCurrentView("results");
      toast.success("Analysis completed");
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unexpected error starting analysis";
      toast.error(message);
      setCurrentView("home");
    } finally {
      setIsAnalyzing(false);
      setStatusMessage(null);
    }
  };

  const handleBackToHome = () => {
    setCurrentView("home");
    setAnalysisResult(null);
    setStatusMessage(null);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {currentView === "home" ? (
        <HomePage
          onAnalyze={handleAnalyze}
          isAnalyzing={isAnalyzing}
          statusMessage={statusMessage}
        />
      ) : analysisResult ? (
        <ResultsPage result={analysisResult} onBack={handleBackToHome} />
      ) : null}
      <Toaster />
    </div>
  );
}

export default App;
