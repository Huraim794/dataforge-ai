import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, XCircle } from 'lucide-react'
import { jobs } from '../services/api'

export default function JobDetail() {
  const { id } = useParams<{ id: string }>()
  const [job, setJob] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'runs' | 'results' | 'extractions'>('runs')

  useEffect(() => {
    if (id) loadJob()
  }, [id])

  const loadJob = async () => {
    try {
      const data = await jobs.get(id!)
      setJob(data)
    } catch (err) {
      console.error('Failed to load job', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
      </div>
    )
  }

  if (!job) {
    return <div className="text-gray-500">Job not found</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/jobs" className="text-gray-400 hover:text-white">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white truncate max-w-2xl">{job.url}</h1>
          <p className="text-gray-500 mt-1">Job Details</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card">
          <p className="text-sm text-gray-500">Status</p>
          <StatusBadge status={job.status} />
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Duration</p>
          <p className="text-lg font-semibold text-white mt-1">
            {job.duration_ms ? `${(job.duration_ms / 1000).toFixed(1)}s` : '-'}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Retries</p>
          <p className="text-lg font-semibold text-white mt-1">
            {job.retry_count}/{job.max_retries}
          </p>
        </div>
      </div>

      {job.error_message && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
          <p className="text-sm font-medium text-red-400">Error</p>
          <p className="text-sm text-red-300 mt-1">{job.error_message}</p>
        </div>
      )}

      <div className="card">
        <div className="flex gap-4 border-b border-gray-800 pb-4 mb-4">
          <button
            onClick={() => setActiveTab('runs')}
            className={`text-sm font-medium pb-2 border-b-2 transition-colors ${
              activeTab === 'runs' ? 'text-brand-400 border-brand-400' : 'text-gray-500 border-transparent hover:text-gray-300'
            }`}
          >
            Runs ({job.runs?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('results')}
            className={`text-sm font-medium pb-2 border-b-2 transition-colors ${
              activeTab === 'results' ? 'text-brand-400 border-brand-400' : 'text-gray-500 border-transparent hover:text-gray-300'
            }`}
          >
            Results ({job.scrape_results?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('extractions')}
            className={`text-sm font-medium pb-2 border-b-2 transition-colors ${
              activeTab === 'extractions' ? 'text-brand-400 border-brand-400' : 'text-gray-500 border-transparent hover:text-gray-300'
            }`}
          >
            AI Extractions ({job.extraction_results?.length || 0})
          </button>
        </div>

        {activeTab === 'runs' && (
          <div className="space-y-3">
            {(!job.runs || job.runs.length === 0) ? (
              <p className="text-gray-500 text-sm">No runs recorded</p>
            ) : (
              job.runs.map((run: any) => (
                <div key={run.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50">
                  <div className="flex items-center gap-3">
                    {run.status === 'completed' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                    <div>
                      <p className="text-sm text-gray-300">Attempt {run.attempt_number}</p>
                      <p className="text-xs text-gray-500">{new Date(run.created_at).toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-400">{run.total_time_ms ? `${(run.total_time_ms / 1000).toFixed(1)}s` : '-'}</p>
                    {run.http_status_code && (
                      <p className="text-xs text-gray-500">HTTP {run.http_status_code}</p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'results' && (
          <div className="space-y-3">
            {(!job.scrape_results || job.scrape_results.length === 0) ? (
              <p className="text-gray-500 text-sm">No results yet</p>
            ) : (
              job.scrape_results.map((r: any) => (
                <div key={r.id} className="p-4 rounded-lg bg-gray-800/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-200">{r.title || 'Untitled'}</p>
                    <span className="text-xs text-gray-500">HTTP {r.status_code}</span>
                  </div>
                  {r.cleaned_text && (
                    <p className="text-xs text-gray-400 line-clamp-3">{r.cleaned_text}</p>
                  )}
                  <div className="flex gap-4 text-xs text-gray-500">
                    <span>Load: {r.load_time_ms ? `${r.load_time_ms.toFixed(0)}ms` : '-'}</span>
                    {r.captcha_detected && <span className="text-amber-400">CAPTCHA</span>}
                    {r.blocked_detected && <span className="text-red-400">Blocked</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'extractions' && (
          <div className="space-y-3">
            {(!job.extraction_results || job.extraction_results.length === 0) ? (
              <p className="text-gray-500 text-sm">No extractions performed</p>
            ) : (
              job.extraction_results.map((e: any) => (
                <div key={e.id} className="p-4 rounded-lg bg-gray-800/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`badge ${e.success ? 'badge-success' : 'badge-error'}`}>
                      {e.success ? 'Success' : 'Failed'}
                    </span>
                    <span className="text-xs text-gray-500">{e.llm_model || '-'}</span>
                  </div>
                  {e.extracted_data && (
                    <pre className="text-xs text-gray-400 overflow-auto max-h-40">
                      {JSON.stringify(e.extracted_data, null, 2)}
                    </pre>
                  )}
                  <div className="flex gap-4 text-xs text-gray-500">
                    <span>Confidence: {e.confidence_score ? `${(e.confidence_score * 100).toFixed(0)}%` : '-'}</span>
                    <span>Tokens: {e.tokens_total || '-'}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: 'badge-success',
    failed: 'badge-error',
    running: 'badge-info',
    queued: 'badge-info',
    pending: 'badge-neutral',
  }
  return <span className={`${colors[status] || 'badge-neutral'} mt-1`}>{status}</span>
}
