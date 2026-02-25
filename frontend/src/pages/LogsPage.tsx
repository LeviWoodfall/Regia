import { useEffect, useState } from 'react';
import { Activity, AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';
import { getLogs } from '../lib/api';
import { formatDateTime } from '../lib/utils';

export default function LogsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const pageSize = 50;

  const load = async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: pageSize };
      if (statusFilter) params.status = statusFilter;
      const resp = await getLogs(params);
      setLogs(resp.data.logs || []);
      setTotal(resp.data.total || 0);
    } catch { /* API not available */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, [page, statusFilter]);

  const statusIcons: Record<string, React.ReactNode> = {
    success: <CheckCircle className="w-4 h-4 text-green-500" />,
    error: <AlertCircle className="w-4 h-4 text-red-500" />,
    warning: <AlertTriangle className="w-4 h-4 text-yellow-500" />,
    info: <Info className="w-4 h-4 text-blue-500" />,
  };

  const statusColors: Record<string, string> = {
    success: 'bg-green-50 border-green-100',
    error: 'bg-red-50 border-red-100',
    warning: 'bg-yellow-50 border-yellow-100',
    info: 'bg-blue-50 border-blue-100',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-warm-900">Ingestion Logs</h2>
          <p className="text-sm text-sand-600 mt-0.5">{total} log entries</p>
        </div>

        <div className="flex gap-1">
          {['', 'success', 'error', 'warning', 'info'].map(s => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === s
                  ? 'bg-sunset-500 text-white'
                  : 'bg-sand-100 text-sand-600 hover:bg-sand-200'
              }`}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-sand-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-7 w-7 border-2 border-sunset-400 border-t-transparent" />
          </div>
        ) : logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-sand-400">
            <Activity className="w-12 h-12 mb-3 text-sand-300" />
            <p className="text-sm font-medium">No log entries yet</p>
          </div>
        ) : (
          <div className="divide-y divide-sand-50">
            {logs.map((log: any) => (
              <div
                key={log.id}
                className={`flex items-start gap-3 px-5 py-3 border-l-3 ${statusColors[log.status] || ''}`}
              >
                <div className="mt-0.5 shrink-0">
                  {statusIcons[log.status] || statusIcons.info}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-warm-800 uppercase tracking-wider">
                      {log.action}
                    </span>
                    <span className="text-[10px] text-sand-400">{formatDateTime(log.created_at)}</span>
                  </div>
                  <p className="text-sm text-warm-700 mt-0.5">{log.message}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
