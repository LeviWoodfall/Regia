import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Mail, FileText, Search, FolderOpen,
  MessageCircle, Settings, Sun, Moon, Activity, LogOut, User,
} from 'lucide-react';
import { useTheme } from '../lib/theme';
import { useAuth } from '../lib/auth';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/emails', icon: Mail, label: 'Emails' },
  { to: '/documents', icon: FileText, label: 'Documents' },
  { to: '/files', icon: FolderOpen, label: 'Files' },
  { to: '/search', icon: Search, label: 'Search' },
  { to: '/reggie', icon: MessageCircle, label: 'Reggie' },
  { to: '/logs', icon: Activity, label: 'Logs' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-64 bg-warm-900 text-warm-100 flex flex-col z-30">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-warm-800">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-sunset-400 to-sunset-600 flex items-center justify-center">
          <Sun className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white">Regia</h1>
          <p className="text-[11px] text-warm-400 -mt-0.5">Document Intelligence</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-sunset-600/30 text-sunset-300'
                  : 'text-warm-300 hover:bg-warm-800 hover:text-warm-100'
              }`
            }
          >
            <item.icon className="w-[18px] h-[18px] shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Theme Toggle + User */}
      <div className="px-3 py-3 border-t border-warm-800 space-y-2">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
                     text-warm-300 hover:bg-warm-800 hover:text-warm-100 transition-all duration-150"
        >
          {theme === 'dark' ? (
            <Sun className="w-[18px] h-[18px] shrink-0" />
          ) : (
            <Moon className="w-[18px] h-[18px] shrink-0" />
          )}
          {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
        </button>

        {/* User Info + Logout */}
        {user && (
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-6 h-6 rounded-full bg-warm-700 flex items-center justify-center shrink-0">
                <User className="w-3.5 h-3.5 text-warm-300" />
              </div>
              <span className="text-xs text-warm-400 truncate">{user.display_name || user.username}</span>
            </div>
            <button
              onClick={logout}
              className="p-1 rounded hover:bg-warm-800 text-warm-500 hover:text-warm-200 transition-colors"
              title="Log out"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <div className="text-[10px] text-warm-600 px-3">Regia v0.3.0</div>
      </div>
    </aside>
  );
}
