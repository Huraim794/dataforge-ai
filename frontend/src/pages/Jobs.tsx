import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, RefreshCw, CheckCircle2, XCircle, Clock } from 'lucide-react'
import { jobs } from '../services/api'

const STATUSES = ['', 'completed', 'failed', 'running', 'queued', 'pending', 'cancelled']

export default function Jobs() {
  const [jobList, setJobList] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const pageSize = 20

  useEffect(() => {
    loadJobs()
  }, [page, statusFilter])

  const loadJobs = async () => {
    setLoading(true)
    try {
      const result = await jobs.list({ status: statusFilter || undefined, page, page_size: pageSize })
      setJobList(result.items || [])
      setTotal(result.total || 0)
    } catch (err) {
      console.error('Failed to load jobs', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async (id: string) => {
    try {
      await jobs.cancel(id)
      loadJobs()
    } catch (err) {
      console.error('Failed to cancel job', err)
    }
  }

  const handleRetry = async (id: string) => {
    try {
      await jobs.retry(id)
      loadJobs()
    } catch (err) {
      console.error('Failed to retry job', err)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const filtered = jobList.filter(j =>
    search ? j.url.toLowerCase().includes(search.toLowerCase()) : true
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Jobs</h1>
          <p className="text-gray-500 mt-1">Manage and monitor scraping jobs</p>
        </div>
        <div className="flex gap-3">
          <button onClick={loadJobs} className="btn-secondary">
            <RefreshCw className="w-4 h-4" />
          </button>
          <Link to="/targets" className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            New Job
          </Link>
        </div>
      </div>

      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by URL..."
            className="input pl-10"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="select w-40"
        >
          <option value="">All Status</option>
          {STATUSES.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
        </div>
      ) : (
        <>
          <div className="card p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">URL</th>
                    <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Priority</th>
                    <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                    <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                    <th className="text-right px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {filtered.map((job: any) => (
                    <tr key={job.id} className="hover:bg-gray-800/50 transition-colors">
                      <td className="px-6 py-4">
                        <Link to={`/jobs/${job.id}`} className="text-sm text-brand-400 hover:text-brand-300 truncate block max-w-md">
                          {job.url}
                        </Link>
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={job.status} />
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-400">{job.priority}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-400">
                          {job.duration_ms ? `${(job.duration_ms / 1000).toFixed(1)}s` : '-'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-500">
                          {new Date(job.created_at).toLocaleDateString()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {job.status === 'running' && (
                            <button onClick={() => handleCancel(job.id)} className="btn-secondary text-xs py-1 px-2">
                              Cancel
                            </button>
                          )}
                          {(job.status === 'failed' || job.status === 'cancelled') && (
                            <button onClick={() => handleRetry(job.id)} className="btn-primary text-xs py-1 px-2">
                              Retry
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Showing {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} of {total}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="btn-secondary text-sm"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="btn-secondary text-sm"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { class: string; icon: any }> = {
    completed: { class: 'badge-success', icon: CheckCircle2 },
    failed: { class: 'badge-error', icon: XCircle },
    running: { class: 'badge-info', icon: Clock },
    queued: { class: 'badge-info', icon: Clock },
    pending: { class: 'badge-neutral', icon: Clock },
    cancelled: { class: 'badge-neutral', icon: XCircle },
  }
  const c = config[status] || { class: 'badge-neutral', icon: Clock }
  const Icon = c.icon
  return (
    <span className={`${c.class} gap-1`}>
      <Icon className="w-3 h-3" />
      {status}
    </span>
  )
}
