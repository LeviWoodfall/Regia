import { Search, Bell } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Header() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  return (
    <header className="sticky top-0 z-20 bg-warm-50/80 backdrop-blur-md border-b border-sand-200">
      <div className="flex items-center justify-between h-14 px-6">
        {/* Search Bar */}
        <form onSubmit={handleSearch} className="flex-1 max-w-xl">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sand-400" />
            <input
              type="text"
              placeholder="Search documents, emails, invoices…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-sand-100 border border-sand-200 rounded-xl text-sm
                         text-warm-900 placeholder-sand-400
                         focus:outline-none focus:ring-2 focus:ring-sunset-400/40 focus:border-sunset-400
                         transition-all duration-200"
            />
          </div>
        </form>

        {/* Right Side */}
        <div className="flex items-center gap-3 ml-4">
          <button className="relative p-2 rounded-lg hover:bg-sand-100 text-sand-500 hover:text-warm-700 transition-colors">
            <Bell className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
