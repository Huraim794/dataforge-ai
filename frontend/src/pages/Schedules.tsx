import { useState, useEffect } from 'react'
import { Plus, Play, Pause, Trash2 } from 'lucide-react'
import { schedules } from '../services/api'

export default function Schedules() {
  const [scheduleList, setScheduleList] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSchedules()
  }, [])

  const loadSchedules = async () => {
    setLoading(true)
    try {
      const result = await schedules.list('all')
      setScheduleList(result.items || [])
    } catch (err) {
      console.error('Failed to load schedules', err)
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = async (id: string) => {
    try {
      await schedules.toggle(id)
      loadSchedules()
    } catch (err) {
      console.error('Failed to toggle schedule', err)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this schedule?')) return
    try {
      await schedules.delete(id)
      loadSchedules()
    } catch (err) {
      console.error('Failed to delete schedule', err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Schedules</h1>
          <p className="text-gray-500 mt-1">Automated scraping schedules</p>
        </div>
        <button className="btn-primary flex items-center gap-2 opacity-50 cursor-not-allowed" disabled>
          <Plus className="w-4 h-4" /> Add Schedule
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">URL</th>
                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Interval</th>
                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Last Run</th>
                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Runs</th>
                <th className="text-right px-6 py-4 text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {scheduleList.map((s: any) => (
                <tr key={s.id} className="hover:bg-gray-800/50">
                  <td className="px-6 py-4 text-sm text-gray-200">{s.name}</td>
                  <td className="px-6 py-4 text-sm text-gray-400 truncate max-w-xs">{s.url}</td>
                  <td className="px-6 py-4">
                    <span className="badge-info">{s.interval}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`badge ${s.is_active ? 'badge-success' : 'badge-neutral'}`}>
                      {s.is_active ? 'Active' : 'Paused'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {s.last_run_at ? new Date(s.last_run_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-400">{s.runs_so_far}/{s.max_runs || '∞'}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      <button onClick={() => handleToggle(s.id)} className="btn-secondary text-xs py-1 px-2">
                        {s.is_active ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                      </button>
                      <button onClick={() => handleDelete(s.id)} className="btn-danger text-xs py-1 px-2">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
