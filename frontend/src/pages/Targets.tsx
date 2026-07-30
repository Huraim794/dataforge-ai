import { useState, useEffect } from 'react'
import { Plus, Globe, Trash2 } from 'lucide-react'
import { targets, jobs, projects } from '../services/api'

export default function Targets() {
  const [targetList, setTargetList] = useState<any[]>([])
  const [projectList, setProjectList] = useState<any[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [scraping, setScraping] = useState<string | null>(null)
  const [form, setForm] = useState({
    project_id: '', name: '', url: '', target_type: 'webpage', javascript_enabled: true
  })

  useEffect(() => {
    loadProjects()
  }, [])

  useEffect(() => {
    if (selectedProjectId) {
      loadTargets()
    } else {
      setTargetList([])
      setLoading(false)
    }
  }, [selectedProjectId])

  const loadProjects = async () => {
    try {
      const result = await projects.list()
      setProjectList(result || [])
      if (result && result.length > 0) {
        setSelectedProjectId(result[0].id)
        setForm(f => ({ ...f, project_id: result[0].id }))
      }
      setLoading(false)
    } catch (err) {
      console.error('Failed to load projects', err)
      setLoading(false)
    }
  }

  const loadTargets = async () => {
    setLoading(true)
    try {
      const result = await targets.list(selectedProjectId)
      setTargetList(result || [])
    } catch (err) {
      console.error('Failed to load targets', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await targets.create(form)
      setShowAdd(false)
      setForm({ project_id: selectedProjectId, name: '', url: '', target_type: 'webpage', javascript_enabled: true })
      loadTargets()
    } catch (err) {
      console.error('Failed to add target', err)
    }
  }

  const handleScrape = async (url: string) => {
    setScraping(url)
    try {
      await jobs.create({ url, project_id: selectedProjectId, priority: 5 })
      loadTargets()
    } catch (err) {
      console.error('Failed to start scrape', err)
    } finally {
      setScraping(null)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this target?')) return
    try {
      await targets.delete(id)
      loadTargets()
    } catch (err) {
      console.error('Failed to delete target', err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Targets</h1>
          <p className="text-gray-500 mt-1">Websites and pages to scrape</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add Target
        </button>
      </div>

      <div className="card p-4 mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-1.5">Project</label>
        <select
          value={selectedProjectId}
          onChange={e => setSelectedProjectId(e.target.value)}
          className="input"
        >
          <option value="">Select a project...</option>
          {projectList.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="card space-y-4">
          <h3 className="text-lg font-semibold text-white">New Target</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Name</label>
              <input type="text" value={form.name} onChange={e => setForm({...form, name: e.target.value})}
                className="input" placeholder="My Target" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">URL</label>
              <input type="url" value={form.url} onChange={e => setForm({...form, url: e.target.value})}
                className="input" placeholder="https://example.com" required />
            </div>
          </div>
          <div className="flex gap-3 justify-end">
            <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary">Cancel</button>
            <button type="submit" className="btn-primary">Save Target</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {targetList.map((t: any) => (
            <div key={t.id} className="card hover:bg-gray-800/80 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Globe className="w-5 h-5 text-brand-400" />
                  <h3 className="font-semibold text-white">{t.name}</h3>
                </div>
                <button onClick={() => handleDelete(t.id)} className="text-gray-500 hover:text-red-400">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <p className="text-sm text-gray-400 truncate mb-3">{t.url}</p>
              <div className="flex items-center gap-2 mb-4">
                <span className="badge-info text-xs">{t.target_type}</span>
                <span className={`badge ${t.is_active ? 'badge-success' : 'badge-neutral'} text-xs`}>
                  {t.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <button
                onClick={() => handleScrape(t.url)}
                disabled={scraping === t.url}
                className="btn-primary w-full text-sm py-2"
              >
                {scraping === t.url ? 'Scraping...' : 'Scrape Now'}
              </button>
            </div>
          ))}
          {targetList.length === 0 && (
            <p className="text-gray-500 col-span-full text-center py-12">No targets yet. Add your first target to start scraping.</p>
          )}
        </div>
      )}
    </div>
  )
}
