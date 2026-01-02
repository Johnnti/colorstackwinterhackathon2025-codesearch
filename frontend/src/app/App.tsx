import { useState } from 'react';
import { HomePage } from './components/HomePage';
import { ResultsPage } from './components/ResultsPage';
import { Toaster } from './components/ui/sonner';

export type AnalysisResult = {
  pr_summary: {
    what_changed: string;
    why_it_changed: string;
    key_files: string[];
  };
  findings: Array<{
    title: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    confidence: number;
    file: string;
    evidence: string;
    recommendation: string;
  }>;
  risk_matrix: {
    security: 'critical' | 'high' | 'medium' | 'low';
    performance: 'critical' | 'high' | 'medium' | 'low';
    breaking_change: 'critical' | 'high' | 'medium' | 'low';
    maintainability: 'critical' | 'high' | 'medium' | 'low';
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
};

function App() {
  const [currentView, setCurrentView] = useState<'home' | 'results'>('home');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyze = async (prUrl: string, options: any) => {
    setIsAnalyzing(true);
    
    // Simulate API call with mock data
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const mockResult: AnalysisResult = {
      pr_summary: {
        what_changed: "Refactored authentication middleware to use JWT tokens instead of session cookies. Added new user role management system with granular permissions.",
        why_it_changed: "Session-based auth was causing scaling issues with multiple server instances. The new JWT approach enables stateless authentication and better horizontal scaling.",
        key_files: [
          "api/auth/middleware.py",
          "api/auth/jwt_handler.py",
          "api/models/user.py",
          "api/routes/auth.py"
        ]
      },
      findings: [
        {
          title: "Potential auth bypass in middleware",
          severity: "critical",
          confidence: 0.87,
          file: "api/auth/middleware.py",
          evidence: "Line 45-52: JWT validation skipped when 'X-Internal-Request' header is present without additional verification",
          recommendation: "Add IP whitelist validation or service account verification before bypassing JWT check. Consider using a separate internal service token instead."
        },
        {
          title: "Missing rate limiting on new auth endpoints",
          severity: "high",
          confidence: 0.92,
          file: "api/routes/auth.py",
          evidence: "Lines 78-95: /api/auth/refresh endpoint has no rate limiting, vulnerable to token refresh abuse",
          recommendation: "Implement rate limiting (e.g., 5 requests per minute per user) on token refresh endpoint"
        },
        {
          title: "Hardcoded JWT secret in test file",
          severity: "high",
          confidence: 0.95,
          file: "tests/test_auth.py",
          evidence: "Line 12: JWT_SECRET = 'test-secret-key-do-not-use-in-production'",
          recommendation: "While this is a test file, ensure CI/CD pipelines use environment variables and this secret is never used in production"
        },
        {
          title: "Database migration missing rollback script",
          severity: "medium",
          confidence: 0.78,
          file: "migrations/0024_add_user_roles.sql",
          evidence: "Migration adds new columns but doesn't include a corresponding down migration",
          recommendation: "Add rollback migration script in case deployment needs to be reverted"
        },
        {
          title: "Deprecated bcrypt rounds parameter",
          severity: "medium",
          confidence: 0.65,
          file: "api/auth/password.py",
          evidence: "Line 23: Using bcrypt with 10 rounds, industry standard is now 12-14 rounds",
          recommendation: "Update to 12 rounds minimum for better security. Consider implementing gradual migration for existing passwords."
        },
        {
          title: "Missing error logging in exception handler",
          severity: "low",
          confidence: 0.71,
          file: "api/auth/middleware.py",
          evidence: "Lines 67-70: Exception caught but not logged, making debugging difficult",
          recommendation: "Add structured logging for authentication failures to aid in security monitoring"
        }
      ],
      risk_matrix: {
        security: "high",
        performance: "medium",
        breaking_change: "high",
        maintainability: "medium"
      },
      test_plan: {
        unit_tests: [
          "Test JWT token generation with various user roles",
          "Test JWT validation with expired tokens",
          "Test JWT validation with malformed tokens",
          "Test middleware behavior with missing auth headers",
          "Test password hashing with new bcrypt rounds",
          "Test user role permission checks"
        ],
        integration_tests: [
          "Test full authentication flow from login to protected endpoint access",
          "Test token refresh flow with valid and invalid tokens",
          "Test session migration from old auth to new JWT auth",
          "Test auth failure scenarios and error responses",
          "Test concurrent requests with same JWT token"
        ],
        edge_cases: [
          "User with multiple active tokens accessing system",
          "Token refresh during role permission changes",
          "Clock skew scenarios for JWT expiration",
          "Database rollback scenarios for user roles",
          "Requests with both old session cookie and new JWT token"
        ]
      },
      merge_readiness: {
        score: 62,
        blockers: [
          "Critical: Auth bypass vulnerability must be fixed",
          "High: Rate limiting must be implemented on auth endpoints"
        ],
        notes: "This PR introduces significant security improvements but has critical vulnerabilities that must be addressed before merge. The architectural change is sound, but implementation details need hardening."
      }
    };

    setAnalysisResult(mockResult);
    setIsAnalyzing(false);
    setCurrentView('results');
  };

  const handleBackToHome = () => {
    setCurrentView('home');
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {currentView === 'home' ? (
        <HomePage onAnalyze={handleAnalyze} isAnalyzing={isAnalyzing} />
      ) : (
        <ResultsPage 
          result={analysisResult!} 
          onBack={handleBackToHome}
        />
      )}
      <Toaster />
    </div>
  );
}

export default App;