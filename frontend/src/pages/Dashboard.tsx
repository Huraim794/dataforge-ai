import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  FileJson,
  Globe,
  Activity,
  Calendar,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
} from 'lucide-react'
import { monitoring, jobs, proxies } from '../services/api'

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  href,
}: {
  title: string
  value: string | number
  icon: any
  color: string
  href: string
}) {
  return (
    <Link to={href} className="card hover:bg-gray-800/80 transition-colors group">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </Link>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)
  const [recentJobs, setRecentJobs] = useState<any[]>([])
  const [queueStatus, setQueueStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [statsData, jobsData, queueData] = await Promise.all([
        monitoring.stats(),
        jobs.list({ page_size: 5 }),
        monitoring.queueStatus(),
      ])
      setStats(statsData)
      setRecentJobs(jobsData.items || [])
      setQueueStatus(queueData)
    } catch (err) {
      console.error('Failed to load dashboard data', err)
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-500 mt-1">Overview of your scraping infrastructure</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Jobs"
          value={stats?.active_jobs ?? 0}
          icon={FileJson}
          color="bg-blue-500/20 text-blue-400"
          href="/jobs"
        />
        <StatCard
          title="Completed (24h)"
          value={stats?.completed_24h ?? 0}
          icon={CheckCircle2}
          color="bg-emerald-500/20 text-emerald-400"
          href="/jobs?status=completed"
        />
        <StatCard
          title="Failed (24h)"
          value={stats?.failed_24h ?? 0}
          icon={XCircle}
          color="bg-red-500/20 text-red-400"
          href="/jobs?status=failed"
        />
        <StatCard
          title="Active Proxies"
          value={stats?.active_proxies ?? 0}
          icon={Globe}
          color="bg-purple-500/20 text-purple-400"
          href="/proxies"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="card-header">Recent Jobs</h2>
          <div className="space-y-3">
            {recentJobs.length === 0 ? (
              <p className="text-gray-500 text-sm">No jobs yet</p>
            ) : (
              recentJobs.map((job: any) => (
                <Link
                  key={job.id}
                  to={`/jobs/${job.id}`}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <StatusIcon status={job.status} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-200 truncate">
                        {job.url}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(job.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <StatusBadge status={job.status} />
                </Link>
              ))
            )}
          </div>
          <Link
            to="/jobs"
            className="block text-center text-sm text-brand-400 hover:text-brand-300 mt-4 pt-4 border-t border-gray-800"
          >
            View all jobs →
          </Link>
        </div>

        <div className="card">
          <h2 className="card-header">Queue Status</h2>
          <div className="space-y-3">
            {queueStatus ? (
              Object.entries(queueStatus).map(([queue, depth]: [string, any]) => (
                <div
                  key={queue}
                  className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50"
                >
                  <span className="text-sm text-gray-300 capitalize">
                    {queue.replace('_', ' ')}
                  </span>
                  <div className="flex items-center gap-2">
                    <QueueIndicator depth={depth} />
                    <span className="text-sm font-mono text-gray-400">{depth}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-500 text-sm">Loading queue data...</p>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="card-header">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Link
            to="/jobs"
            className="flex flex-col items-center gap-2 p-4 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-colors"
          >
            <FileJson className="w-6 h-6 text-brand-400" />
            <span className="text-sm text-gray-300">New Job</span>
          </Link>
          <Link
            to="/targets"
            className="flex flex-col items-center gap-2 p-4 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-colors"
          >
            <Globe className="w-6 h-6 text-emerald-400" />
            <span className="text-sm text-gray-300">Add Target</span>
          </Link>
          <Link
            to="/proxies"
            className="flex flex-col items-center gap-2 p-4 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-colors"
          >
            <Activity className="w-6 h-6 text-purple-400" />
            <span className="text-sm text-gray-300">Add Proxy</span>
          </Link>
          <Link
            to="/schedules"
            className="flex flex-col items-center gap-2 p-4 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-colors"
          >
            <Calendar className="w-6 h-6 text-amber-400" />
            <span className="text-sm text-gray-300">Schedule</span>
          </Link>
        </div>
      </div>
    </div>
  )
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
    case 'running':
    case 'queued':
      return <Clock className="w-4 h-4 text-blue-400 flex-shrink-0" />
    default:
      return <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
  }
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: 'badge-success',
    failed: 'badge-error',
    running: 'badge-info',
    queued: 'badge-info',
    pending: 'badge-neutral',
    cancelled: 'badge-neutral',
  }

  return (
    <span className={colors[status] || 'badge-neutral'}>
      {status}
    </span>
  )
}

function QueueIndicator({ depth }: { depth: number }) {
  const color = depth === 0 ? 'bg-emerald-500' : depth < 10 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className={`w-2 h-2 rounded-full ${color}`} />
  )
}
