import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  FileJson,
  Globe,
  Calendar,
  Bot,
  Settings,
  LogOut,
  Menu,
  X,
  Activity,
  Users,
} from 'lucide-react'
import { clearTokens } from '../../services/api'
import { useNavigate } from 'react-router-dom'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Jobs', href: '/jobs', icon: FileJson },
  { name: 'Targets', href: '/targets', icon: Globe },
  { name: 'Proxies', href: '/proxies', icon: Activity },
  { name: 'Schedules', href: '/schedules', icon: Calendar },
  { name: 'Extractions', href: '/extractions', icon: Bot },
  { name: 'Projects', href: '/projects', icon: Users },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    clearTokens()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 lg:relative lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col bg-gray-900 border-r border-gray-800">
          <div className="flex items-center justify-between px-6 py-5 border-b border-gray-800">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">DataForge</h1>
                <p className="text-xs text-gray-500">AI Platform</p>
              </div>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-gray-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1 scrollbar-thin">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-600/20 text-brand-400 border border-brand-600/30'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                  }`}
                >
                  <item.icon className="w-5 h-5 flex-shrink-0" />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          <div className="border-t border-gray-800 p-4">
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:text-red-400 hover:bg-gray-800 transition-colors"
            >
              <LogOut className="w-5 h-5" />
              Sign Out
            </button>
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <header className="lg:hidden bg-gray-900 border-b border-gray-800 px-4 py-3">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-gray-400 hover:text-white"
          >
            <Menu className="w-6 h-6" />
          </button>
        </header>

        <main className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-6">
          {children}
        </main>
      </div>
    </div>
  )
}
