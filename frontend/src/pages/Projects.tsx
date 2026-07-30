import { useState, useEffect } from 'react'
import { Plus, Folder, Trash2 } from 'lucide-react'
import { projects } from '../services/api'

export default function Projects() {
  const [projectList, setProjectList] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ name: '', description: '' })

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    setLoading(true)
    try {
      const result = await projects.list()
      setProjectList(result || [])
    } catch (err) {
      console.error('Failed to load projects', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await projects.create(form)
      setShowAdd(false)
      setForm({ name: '', description: '' })
      loadProjects()
    } catch (err) {
      console.error('Failed to create project', err)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this project and all associated data?')) return
    try {
      await projects.delete(id)
      loadProjects()
    } catch (err) {
      console.error('Failed to delete project', err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Projects</h1>
          <p className="text-gray-500 mt-1">Organize your scraping targets into projects</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Project
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="card space-y-4">
          <h3 className="text-lg font-semibold text-white">Create Project</h3>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Name</label>
            <input type="text" value={form.name} onChange={e => setForm({...form, name: e.target.value})}
              className="input" placeholder="My Project" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Description</label>
            <textarea value={form.description} onChange={e => setForm({...form, description: e.target.value})}
              className="input" rows={3} placeholder="Optional description" />
          </div>
          <div className="flex gap-3 justify-end">
            <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary">Cancel</button>
            <button type="submit" className="btn-primary">Create</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projectList.map((p: any) => (
            <div key={p.id} className="card hover:bg-gray-800/80 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-brand-600/20 rounded-lg">
                    <Folder className="w-5 h-5 text-brand-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{p.name}</h3>
                    <p className="text-xs text-gray-500">{p.description || 'No description'}</p>
                  </div>
                </div>
                <button onClick={() => handleDelete(p.id)} className="text-gray-500 hover:text-red-400">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <div className="mt-4 text-xs text-gray-500">
                Created {new Date(p.created_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
