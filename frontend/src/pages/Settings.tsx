import { useState, useEffect } from 'react'
import { Key, Copy, Plus, Trash2 } from 'lucide-react'
import { auth } from '../services/api'

export default function Settings() {
  const [apiKeys, setApiKeys] = useState<any[]>([])
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [userData, keys] = await Promise.all([
        auth.me(),
        auth.listApiKeys(),
      ])
      setUser(userData)
      setApiKeys(keys || [])
    } catch (err) {
      console.error('Failed to load settings', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKeyName) return
    try {
      const result = await auth.createApiKey(newKeyName)
      setNewKeyValue(result.key)
      setNewKeyName('')
      loadData()
    } catch (err) {
      console.error('Failed to create API key', err)
    }
  }

  const handleDeleteKey = async (id: string) => {
    if (!confirm('Delete this API key? This action cannot be undone.')) return
    try {
      await auth.deleteApiKey(id)
      loadData()
    } catch (err) {
      console.error('Failed to delete API key', err)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-500 mt-1">Manage your account and API keys</p>
      </div>

      {user && (
        <div className="card">
          <h2 className="card-header">Profile</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Name</p>
              <p className="text-sm text-gray-200">{user.full_name || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Email</p>
              <p className="text-sm text-gray-200">{user.email}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Role</p>
              <p className="text-sm text-gray-200 capitalize">{user.role}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Company</p>
              <p className="text-sm text-gray-200">{user.company || '-'}</p>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="card-header mb-0">API Keys</h2>
        </div>

        {newKeyValue && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 mb-4">
            <p className="text-sm font-medium text-amber-400 mb-2">New API Key Created</p>
            <p className="text-xs text-amber-300 mb-2">Copy this key now. You won't be able to see it again.</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-gray-950 rounded px-3 py-2 text-sm font-mono text-amber-200">
                {newKeyValue}
              </code>
              <button onClick={() => copyToClipboard(newKeyValue)} className="btn-secondary text-xs py-2">
                <Copy className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        <form onSubmit={handleCreateKey} className="flex gap-3 mb-6">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            className="input flex-1"
            placeholder="Key name (e.g., Production)"
          />
          <button type="submit" className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" /> Create Key
          </button>
        </form>

        <div className="space-y-3">
          {apiKeys.map((key: any) => (
            <div key={key.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50">
              <div className="flex items-center gap-3">
                <Key className="w-4 h-4 text-gray-500" />
                <div>
                  <p className="text-sm text-gray-200">{key.name}</p>
                  <p className="text-xs text-gray-500 font-mono">{key.key_prefix}...</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`badge ${key.is_active ? 'badge-success' : 'badge-neutral'} text-xs`}>
                  {key.is_active ? 'Active' : 'Inactive'}
                </span>
                <button onClick={() => handleDeleteKey(key.id)} className="text-gray-500 hover:text-red-400">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
