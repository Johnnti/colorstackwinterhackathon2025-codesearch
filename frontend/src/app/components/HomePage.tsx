import { useState } from 'react';
import { Github, Sparkles, Shield, Target, FileSearch, Zap } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import { Card, CardContent } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

interface HomePageProps {
  onAnalyze: (prUrl: string, options: any) => void;
  isAnalyzing: boolean;
}

export function HomePage({ onAnalyze, isAnalyzing }: HomePageProps) {
  const [prUrl, setPrUrl] = useState('');
  const [diffText, setDiffText] = useState('');
  const [useRepoRules, setUseRepoRules] = useState(false);
  const [inputMethod, setInputMethod] = useState<'url' | 'diff'>('url');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const input = inputMethod === 'url' ? prUrl : diffText;
    if (input.trim()) {
      onAnalyze(input, { useRepoRules });
    }
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b bg-white">
        <div className="container mx-auto px-4 py-4 max-w-6xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-violet-600 to-indigo-600 rounded-lg flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-slate-900">AI PR Reviewer</h1>
              <p className="text-sm text-slate-500">Intelligent code review analysis</p>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <div className="bg-gradient-to-b from-white to-slate-50 border-b">
        <div className="container mx-auto px-4 py-16 max-w-4xl text-center">
          <div className="inline-flex items-center gap-2 bg-violet-100 text-violet-700 px-4 py-2 rounded-full text-sm mb-6">
            <Zap className="w-4 h-4" />
            <span>Powered by Advanced AI Analysis</span>
          </div>
          <h2 className="text-4xl mb-4 text-slate-900">
            Get Comprehensive Code Reviews in Seconds
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Paste a GitHub PR URL or diff to receive prioritized findings, risk analysis, 
            security insights, and automated test plans.
          </p>
        </div>
      </div>

      {/* Features Grid */}
      <div className="container mx-auto px-4 py-12 max-w-6xl">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
          <Card>
            <CardContent className="pt-6">
              <div className="w-12 h-12 bg-violet-100 rounded-lg flex items-center justify-center mb-4">
                <FileSearch className="w-6 h-6 text-violet-600" />
              </div>
              <h3 className="mb-2 text-slate-900">Smart Analysis</h3>
              <p className="text-sm text-slate-600">
                AI-powered review identifies critical issues across your entire PR
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="w-12 h-12 bg-rose-100 rounded-lg flex items-center justify-center mb-4">
                <Shield className="w-6 h-6 text-rose-600" />
              </div>
              <h3 className="mb-2 text-slate-900">Risk Matrix</h3>
              <p className="text-sm text-slate-600">
                Evaluate security, performance, and breaking change risks
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="w-12 h-12 bg-amber-100 rounded-lg flex items-center justify-center mb-4">
                <Target className="w-6 h-6 text-amber-600" />
              </div>
              <h3 className="mb-2 text-slate-900">Test Plans</h3>
              <p className="text-sm text-slate-600">
                Get targeted test suggestions for unit, integration, and edge cases
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center mb-4">
                <Sparkles className="w-6 h-6 text-emerald-600" />
              </div>
              <h3 className="mb-2 text-slate-900">Merge Score</h3>
              <p className="text-sm text-slate-600">
                Instant readiness assessment with actionable blockers
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Input Form */}
        <Card className="max-w-3xl mx-auto shadow-lg">
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit}>
              <Tabs value={inputMethod} onValueChange={(v) => setInputMethod(v as 'url' | 'diff')}>
                <TabsList className="grid w-full grid-cols-2 mb-6">
                  <TabsTrigger value="url">
                    <Github className="w-4 h-4 mr-2" />
                    GitHub PR URL
                  </TabsTrigger>
                  <TabsTrigger value="diff">
                    <FileSearch className="w-4 h-4 mr-2" />
                    Paste Diff
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="url" className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="pr-url">Pull Request URL</Label>
                    <Input
                      id="pr-url"
                      type="url"
                      placeholder="https://github.com/owner/repo/pull/123"
                      value={prUrl}
                      onChange={(e) => setPrUrl(e.target.value)}
                      className="text-base"
                    />
                    <p className="text-sm text-slate-500">
                      Enter a public GitHub PR URL to analyze
                    </p>
                  </div>
                </TabsContent>

                <TabsContent value="diff" className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="diff-text">Diff Content</Label>
                    <Textarea
                      id="diff-text"
                      placeholder="Paste your git diff here..."
                      value={diffText}
                      onChange={(e) => setDiffText(e.target.value)}
                      rows={12}
                      className="font-mono text-sm"
                    />
                    <p className="text-sm text-slate-500">
                      Paste the output of 'git diff' or exported PR diff
                    </p>
                  </div>
                </TabsContent>
              </Tabs>

              {/* Options */}
              <div className="mt-6 pt-6 border-t space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label htmlFor="repo-rules">Use Repository Rules</Label>
                    <p className="text-sm text-slate-500">
                      Apply custom review rules from review_rules.yml
                    </p>
                  </div>
                  <Switch
                    id="repo-rules"
                    checked={useRepoRules}
                    onCheckedChange={setUseRepoRules}
                  />
                </div>

                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Github className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="text-sm text-slate-700">Post review to GitHub</p>
                      <p className="text-xs text-slate-500">Sign in to enable</p>
                    </div>
                  </div>
                  <Switch disabled />
                </div>
              </div>

              {/* Submit Button */}
              <div className="mt-6">
                <Button
                  type="submit"
                  className="w-full h-12"
                  disabled={isAnalyzing || (inputMethod === 'url' ? !prUrl.trim() : !diffText.trim())}
                >
                  {isAnalyzing ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                      Analyzing PR...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-2" />
                      Analyze Pull Request
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Example PRs */}
        <div className="max-w-3xl mx-auto mt-8">
          <p className="text-sm text-slate-500 text-center mb-4">Try an example:</p>
          <div className="flex flex-wrap gap-2 justify-center">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setPrUrl('https://github.com/facebook/react/pull/28177');
                setInputMethod('url');
              }}
            >
              React PR Example
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setPrUrl('https://github.com/microsoft/vscode/pull/198234');
                setInputMethod('url');
              }}
            >
              VSCode PR Example
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setPrUrl('https://github.com/vercel/next.js/pull/59567');
                setInputMethod('url');
              }}
            >
              Next.js PR Example
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
