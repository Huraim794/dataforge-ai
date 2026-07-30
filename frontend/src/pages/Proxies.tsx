import { useState, useEffect } from 'react'
import { Plus, RefreshCw, Globe, CheckCircle2, XCircle } from 'lucide-react'
import { proxies } from '../services/api'

export default function Proxies() {
  const [proxyList, setProxyList] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [newProxy, setNewProxy] = useState({ host: '', port: 8080, protocol: 'http' })

  useEffect(() => {
    loadProxies()
  }, [])

  const loadProxies = async () => {
    setLoading(true)
    try {
      const result = await proxies.list()
      setProxyList(result.items || [])
    } catch (err) {
      console.error('Failed to load proxies', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await proxies.create(newProxy)
      setShowAdd(false)
      setNewProxy({ host: '', port: 8080, protocol: 'http' })
      loadProxies()
    } catch (err) {
      console.error('Failed to add proxy', err)
    }
  }

  const handleCheck = async (id: string) => {
    try {
      await proxies.check(id)
      loadProxies()
    } catch (err) {
      console.error('Failed to check proxy', err)
    }
  }

  const handleCheckAll = async () => {
    try {
      await proxies.checkAll()
      loadProxies()
    } catch (err) {
      console.error('Failed to check all proxies', err)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this proxy?')) return
    try {
      await proxies.delete(id)
      loadProxies()
    } catch (err) {
      console.error('Failed to delete proxy', err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Proxies</h1>
          <p className="text-gray-500 mt-1">Manage your proxy pool</p>
        </div>
        <div className="flex gap-3">
          <button onClick={handleCheckAll} className="btn-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            Check All
          </button>
          <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Add Proxy
          </button>
        </div>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="card space-y-4">
          <h3 className="text-lg font-semibold text-white">Add New Proxy</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Host</label>
              <input type="text" value={newProxy.host} onChange={(e) => setNewProxy({ ...newProxy, host: e.target.value })}
                className="input" placeholder="192.168.1.1" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Port</label>
              <input type="number" value={newProxy.port} onChange={(e) => setNewProxy({ ...newProxy, port: parseInt(e.target.value) })}
                className="input" placeholder="8080" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Protocol</label>
              <select value={newProxy.protocol} onChange={(e) => setNewProxy({ ...newProxy, protocol: e.target.value })}
                className="select">
                <option value="http">HTTP</option>
                <option value="https">HTTPS</option>
                <option value="socks4">SOCKS4</option>
                <option value="socks5">SOCKS5</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3 justify-end">
            <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary">Cancel</button>
            <button type="submit" className="btn-primary">Add Proxy</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Proxy</th>
                  <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Latency</th>
                  <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Success</th>
                  <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Failures</th>
                  <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Country</th>
                  <th className="text-right px-6 py-4 text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {proxyList.map((p: any) => (
                  <tr key={p.id} className="hover:bg-gray-800/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <Globe className="w-4 h-4 text-gray-500" />
                        <span className="text-sm text-gray-200">{p.host}:{p.port}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`badge ${
                        p.status === 'active' ? 'badge-success' :
                        p.status === 'checking' ? 'badge-warning' : 'badge-error'
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-400">
                        {p.latency_ms ? `${p.latency_ms.toFixed(0)}ms` : '-'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-emerald-400">{p.success_count}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`text-sm ${p.failure_count > 0 ? 'text-red-400' : 'text-gray-400'}`}>
                        {p.failure_count}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-400">{p.country || '-'}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button onClick={() => handleCheck(p.id)} className="btn-secondary text-xs py-1 px-2">Check</button>
                        <button onClick={() => handleDelete(p.id)} className="btn-danger text-xs py-1 px-2">Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
