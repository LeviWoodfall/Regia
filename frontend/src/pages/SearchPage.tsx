import { useState, useEffect } from 'react';
import { Search, FileText, Mail, Filter, X } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { search as apiSearch, getClassifications } from '../lib/api';
import { formatDateTime, truncate } from '../lib/utils';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [results, setResults] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [tookMs, setTookMs] = useState(0);
  const [loading, setLoading] = useState(false);
  const [scope, setScope] = useState('all');
  const [classifications, setClassifications] = useState<any[]>([]);
  const [filterClassification, setFilterClassification] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    getClassifications().then(r => setClassifications(r.data.classifications || [])).catch(() => {});
  }, []);

  useEffect(() => {
    const q = searchParams.get('q');
    if (q) {
      setQuery(q);
      doSearch(q);
    }
  }, [searchParams]);

  const doSearch = async (q?: string) => {
    const searchQuery = q || query;
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const filters: any = {};
      if (filterClassification) filters.classification = filterClassification;

      const resp = await apiSearch({
        query: searchQuery.trim(),
        scope,
        filters,
        page: 1,
        page_size: 50,
      });
      setResults(resp.data.results || []);
      setTotal(resp.data.total || 0);
      setTookMs(resp.data.took_ms || 0);
    } catch {
      setResults([]);
    }
    setLoading(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams({ q: query });
    doSearch();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-warm-900">Search</h2>
        <p className="text-sm text-sand-600 mt-0.5">
          Find documents, emails, and content across your entire archive
        </p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-sand-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for invoices, contracts, receipts, names, amounts…"
              className="w-full pl-12 pr-4 py-3.5 bg-white border border-sand-200 rounded-2xl text-sm
                         text-warm-900 placeholder-sand-400 shadow-sm
                         focus:outline-none focus:ring-2 focus:ring-sunset-400/40 focus:border-sunset-400
                         transition-all duration-200"
            />
          </div>
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-3 rounded-2xl border transition-colors ${
              showFilters ? 'bg-sunset-100 border-sunset-300 text-sunset-700' : 'bg-white border-sand-200 text-sand-500 hover:bg-sand-50'
            }`}
          >
            <Filter className="w-5 h-5" />
          </button>
          <button
            type="submit"
            className="px-6 py-3 bg-gradient-to-r from-sunset-500 to-sunset-600 text-white rounded-2xl
                       text-sm font-medium shadow-sm hover:shadow-md transition-all duration-200"
          >
            Search
          </button>
        </div>
      </form>

      {/* Filters */}
      {showFilters && (
        <div className="bg-white rounded-2xl border border-sand-200 shadow-sm p-4 flex flex-wrap gap-3 items-center">
          <span className="text-xs font-medium text-sand-500">Scope:</span>
          {['all', 'documents', 'emails'].map(s => (
            <button
              key={s}
              onClick={() => setScope(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                scope === s ? 'bg-sunset-500 text-white' : 'bg-sand-100 text-sand-600 hover:bg-sand-200'
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}

          <div className="w-px h-6 bg-sand-200 mx-1" />

          <span className="text-xs font-medium text-sand-500">Classification:</span>
          <select
            value={filterClassification}
            onChange={(e) => setFilterClassification(e.target.value)}
            className="px-3 py-1.5 bg-sand-100 border-none rounded-lg text-xs text-warm-700 focus:ring-2 focus:ring-sunset-400"
          >
            <option value="">All</option>
            {classifications.map((c: any) => (
              <option key={c.classification} value={c.classification}>
                {c.classification} ({c.count})
              </option>
            ))}
          </select>

          {filterClassification && (
            <button onClick={() => setFilterClassification('')} className="text-sand-400 hover:text-warm-600">
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      )}

      {/* Results */}
      {total > 0 && (
        <p className="text-xs text-sand-500">
          {total} result{total !== 1 ? 's' : ''} in {tookMs}ms
        </p>
      )}

      <div className="space-y-3">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-7 w-7 border-2 border-sunset-400 border-t-transparent" />
          </div>
        ) : results.length === 0 && query ? (
          <div className="bg-white rounded-2xl border border-sand-200 shadow-sm flex flex-col items-center justify-center py-12 text-sand-400">
            <Search className="w-10 h-10 mb-3 text-sand-300" />
            <p className="text-sm font-medium">No results found</p>
            <p className="text-xs mt-1">Try different keywords or broaden your filters</p>
          </div>
        ) : (
          results.map((result: any, idx: number) => (
            <div
              key={idx}
              className="bg-white rounded-2xl border border-sand-200 shadow-sm p-4 hover:border-sunset-200 hover:shadow-md transition-all duration-200 cursor-pointer"
            >
              <div className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                  result.type === 'document' ? 'bg-sunset-100 text-sunset-500' : 'bg-warm-100 text-warm-500'
                }`}>
                  {result.type === 'document' ? <FileText className="w-4 h-4" /> : <Mail className="w-4 h-4" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-warm-900">{truncate(result.title, 80)}</p>
                    <span className="text-[10px] px-1.5 py-0.5 bg-sand-100 text-sand-500 rounded font-medium uppercase">
                      {result.type}
                    </span>
                  </div>
                  <p className="text-xs text-sand-600 mt-1 leading-relaxed">{result.snippet}</p>
                  <div className="flex items-center gap-3 mt-2 text-[11px] text-sand-400">
                    <span>{formatDateTime(result.date)}</span>
                    {result.metadata?.sender_name && <span>From: {result.metadata.sender_name}</span>}
                    {result.metadata?.classification && (
                      <span className="px-1.5 py-0.5 bg-sunset-50 text-sunset-600 rounded-full font-medium">
                        {result.metadata.classification}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
