import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Mail, FileText, Search, FolderOpen,
  MessageCircle, Settings, Sun, Activity,
} from 'lucide-react';

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

      {/* Footer */}
      <div className="px-4 py-3 border-t border-warm-800 text-xs text-warm-500">
        Regia v0.1.0
      </div>
    </aside>
  );
}
