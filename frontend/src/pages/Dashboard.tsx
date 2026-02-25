import { useEffect, useState } from 'react';
import { Mail, FileText, HardDrive, RefreshCw, Clock, AlertCircle } from 'lucide-react';
import { getDashboard, triggerFetchAll } from '../lib/api';
import { formatBytes, formatDateTime, truncate } from '../lib/utils';

interface DashboardData {
  total_emails: number;
  total_documents: number;
  total_storage_bytes: number;
  accounts_active: number;
  last_sync: string | null;
  pending_processing: number;
  recent_emails: any[];
  recent_documents: any[];
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);

  const load = async () => {
    try {
      const resp = await getDashboard();
      setData(resp.data);
    } catch {
      // API not available yet — show empty state
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleFetchAll = async () => {
    setFetching(true);
    try {
      await triggerFetchAll();
      await load();
    } catch { /* ignore */ }
    setFetching(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-sunset-400 border-t-transparent" />
      </div>
    );
  }

  const stats = data || {
    total_emails: 0, total_documents: 0, total_storage_bytes: 0,
    accounts_active: 0, last_sync: null, pending_processing: 0,
    recent_emails: [], recent_documents: [],
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-warm-900">Dashboard</h2>
          <p className="text-sm text-sand-600 mt-0.5">
            Overview of your document ingestion system
          </p>
        </div>
        <button
          onClick={handleFetchAll}
          disabled={fetching}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-sunset-500 to-sunset-600
                     text-white rounded-xl text-sm font-medium shadow-sm hover:shadow-md
                     hover:from-sunset-600 hover:to-sunset-700 transition-all duration-200
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 ${fetching ? 'animate-spin' : ''}`} />
          Fetch All Emails
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Mail className="w-5 h-5" />}
          label="Total Emails"
          value={stats.total_emails.toLocaleString()}
          color="sunset"
        />
        <StatCard
          icon={<FileText className="w-5 h-5" />}
          label="Documents"
          value={stats.total_documents.toLocaleString()}
          color="warm"
        />
        <StatCard
          icon={<HardDrive className="w-5 h-5" />}
          label="Storage Used"
          value={formatBytes(stats.total_storage_bytes)}
          color="sand"
        />
        <StatCard
          icon={<Clock className="w-5 h-5" />}
          label="Last Sync"
          value={stats.last_sync ? formatDateTime(stats.last_sync) : 'Never'}
          color="sunset"
          small
        />
      </div>

      {/* Pending Alert */}
      {stats.pending_processing > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 bg-sunset-100 border border-sunset-200 rounded-xl text-sm text-sunset-800">
          <AlertCircle className="w-5 h-5 text-sunset-500 shrink-0" />
          <span><strong>{stats.pending_processing}</strong> email(s) pending processing</span>
        </div>
      )}

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Emails */}
        <div className="bg-white rounded-2xl border border-sand-200 shadow-sm">
          <div className="px-5 py-4 border-b border-sand-100">
            <h3 className="font-semibold text-warm-900">Recent Emails</h3>
          </div>
          <div className="divide-y divide-sand-100">
            {stats.recent_emails.length === 0 ? (
              <p className="px-5 py-8 text-center text-sand-400 text-sm">No emails ingested yet</p>
            ) : (
              stats.recent_emails.map((email: any) => (
                <div key={email.id} className="px-5 py-3 hover:bg-sand-50 transition-colors">
                  <p className="text-sm font-medium text-warm-900">{truncate(email.subject || '(No subject)', 60)}</p>
                  <p className="text-xs text-sand-500 mt-0.5">
                    {email.sender_name || email.sender_email} · {formatDateTime(email.date_sent)}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Documents */}
        <div className="bg-white rounded-2xl border border-sand-200 shadow-sm">
          <div className="px-5 py-4 border-b border-sand-100">
            <h3 className="font-semibold text-warm-900">Recent Documents</h3>
          </div>
          <div className="divide-y divide-sand-100">
            {stats.recent_documents.length === 0 ? (
              <p className="px-5 py-8 text-center text-sand-400 text-sm">No documents processed yet</p>
            ) : (
              stats.recent_documents.map((doc: any) => (
                <div key={doc.id} className="px-5 py-3 hover:bg-sand-50 transition-colors">
                  <p className="text-sm font-medium text-warm-900">{truncate(doc.original_filename, 50)}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {doc.classification && (
                      <span className="inline-block px-2 py-0.5 bg-sunset-100 text-sunset-700 rounded-full text-[11px] font-medium">
                        {doc.classification}
                      </span>
                    )}
                    <span className="text-xs text-sand-500">
                      {formatBytes(doc.file_size)} · {formatDateTime(doc.date_ingested)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color, small }: {
  icon: React.ReactNode; label: string; value: string; color: string; small?: boolean;
}) {
  const bgMap: Record<string, string> = {
    sunset: 'bg-sunset-100 text-sunset-600',
    warm: 'bg-warm-100 text-warm-600',
    sand: 'bg-sand-200 text-sand-700',
  };

  return (
    <div className="bg-white rounded-2xl border border-sand-200 shadow-sm p-5">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${bgMap[color] || bgMap.sunset}`}>
          {icon}
        </div>
        <div>
          <p className="text-xs text-sand-500 font-medium">{label}</p>
          <p className={`font-bold text-warm-900 ${small ? 'text-sm' : 'text-xl'}`}>{value}</p>
        </div>
      </div>
    </div>
  );
}
