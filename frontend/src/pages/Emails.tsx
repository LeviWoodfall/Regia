import { useEffect, useState } from 'react';
import { Mail, Paperclip, Link2, ChevronLeft, ChevronRight } from 'lucide-react';
import { getEmails } from '../lib/api';
import { formatDateTime, truncate } from '../lib/utils';

export default function Emails() {
  const [emails, setEmails] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const pageSize = 20;

  const load = async () => {
    setLoading(true);
    try {
      const resp = await getEmails({ page, page_size: pageSize });
      setEmails(resp.data.emails);
      setTotal(resp.data.total);
    } catch { /* API not available */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, [page]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-warm-900">Emails</h2>
        <p className="text-sm text-sand-600 mt-0.5">
          {total} ingested email{total !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Email Table */}
      <div className="bg-white rounded-2xl border border-sand-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-7 w-7 border-2 border-sunset-400 border-t-transparent" />
          </div>
        ) : emails.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-sand-400">
            <Mail className="w-12 h-12 mb-3 text-sand-300" />
            <p className="text-sm font-medium">No emails ingested yet</p>
            <p className="text-xs mt-1">Configure an email account in Settings to get started</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-sand-100 text-left">
                <th className="px-5 py-3 font-medium text-sand-500 text-xs uppercase tracking-wider">Subject</th>
                <th className="px-5 py-3 font-medium text-sand-500 text-xs uppercase tracking-wider">From</th>
                <th className="px-5 py-3 font-medium text-sand-500 text-xs uppercase tracking-wider">Date</th>
                <th className="px-5 py-3 font-medium text-sand-500 text-xs uppercase tracking-wider">Status</th>
                <th className="px-5 py-3 font-medium text-sand-500 text-xs uppercase tracking-wider w-20">Docs</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sand-50">
              {emails.map((email: any) => (
                <tr key={email.id} className="hover:bg-sand-50 transition-colors cursor-pointer">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-warm-900">
                        {truncate(email.subject || '(No subject)', 50)}
                      </span>
                      {email.has_attachments && <Paperclip className="w-3.5 h-3.5 text-sand-400" />}
                      {email.has_invoice_links && <Link2 className="w-3.5 h-3.5 text-sunset-400" />}
                    </div>
                    {email.classification && (
                      <span className="inline-block mt-0.5 px-2 py-0.5 bg-sunset-50 text-sunset-600 rounded-full text-[10px] font-medium">
                        {email.classification}
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-sand-600">
                    {email.sender_name || email.sender_email}
                  </td>
                  <td className="px-5 py-3 text-sand-500 text-xs">
                    {formatDateTime(email.date_sent)}
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={email.status} />
                  </td>
                  <td className="px-5 py-3 text-center text-sand-600">
                    {email.document_count || 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-sand-100">
            <span className="text-xs text-sand-500">
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-lg hover:bg-sand-100 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1.5 rounded-lg hover:bg-sand-100 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'bg-green-100 text-green-700',
    pending: 'bg-yellow-100 text-yellow-700',
    processing: 'bg-blue-100 text-blue-700',
    error: 'bg-red-100 text-red-700',
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium ${styles[status] || styles.pending}`}>
      {status}
    </span>
  );
}
