import { useEffect, useState } from 'react';
import { Check, X, Archive, Eye, Loader2, Link2, Paperclip, ChevronLeft, ChevronRight } from 'lucide-react';
import { getReviewQueue, approveEmail, rejectEmail, archiveEmail, captureLink } from '../lib/api';
import { formatDateTime, truncate } from '../lib/utils';

export default function ReviewQueuePage() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selected, setSelected] = useState<any | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [previewLink, setPreviewLink] = useState('');
  const pageSize = 20;

  const load = async () => {
    setLoading(true);
    try {
      const resp = await getReviewQueue({ page, page_size: pageSize });
      setItems(resp.data.items);
      setTotal(resp.data.total);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, [page]);

  const loadDetail = async (id: number) => {
    setSelectedId(id);
    setLoadingDetail(true);
    try {
      const item = items.find(i => i.id === id);
      setSelected(item || null);
      setPreviewLink(item?.invoice_links?.[0] || '');
    } catch {
      setSelected(null);
    }
    setLoadingDetail(false);
  };

  const handleApprove = async () => {
    if (!selectedId) return;
    setActionLoading(true);
    setMessage('');
    try {
      await approveEmail(selectedId);
      setMessage('Approved and processed');
      await load();
      setSelected(null);
      setSelectedId(null);
    } catch {
      setMessage('Approve failed');
    }
    setActionLoading(false);
  };

  const handleReject = async () => {
    if (!selectedId) return;
    setActionLoading(true);
    setMessage('');
    try {
      await rejectEmail(selectedId);
      setMessage('Rejected');
      await load();
      setSelected(null);
      setSelectedId(null);
    } catch {
      setMessage('Reject failed');
    }
    setActionLoading(false);
  };

  const handleArchive = async () => {
    if (!selectedId) return;
    setActionLoading(true);
    setMessage('');
    try {
      await archiveEmail(selectedId);
      setMessage('Archived');
      await load();
      setSelected(null);
      setSelectedId(null);
    } catch {
      setMessage('Archive failed');
    }
    setActionLoading(false);
  };

  const handleCapture = async () => {
    if (!selectedId || !previewLink) return;
    setActionLoading(true);
    setMessage('');
    try {
      await captureLink(selectedId, previewLink, 'captured.pdf');
      setMessage('Link captured to PDF');
    } catch {
      setMessage('Capture failed');
    }
    setActionLoading(false);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold text-warm-900">Review Queue</h2>
        <p className="text-sm text-sand-600 mt-0.5">
          {total} email{total !== 1 ? 's' : ''} pending review
        </p>
      </div>

      <div className="grid grid-cols-12 gap-3">
        {/* Queue list */}
        <div className="col-span-7 bg-white rounded-2xl border border-sand-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="w-7 h-7 animate-spin text-sunset-400 border-t-transparent" />
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-sand-400">
              <Eye className="w-12 h-12 mb-3 text-sand-300" />
              <p className="text-sm font-medium">No emails pending review</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-sand-100 text-left">
                  <th className="px-5 py-3 font-medium text-sand-500 text-xs uppercase tracking-wider">Subject</th>
                  <th className="px-5 py-3 font-medium text-sand-500 text-xs uppercase tracking-wider">From</th>
                  <th className="px-5 py-3 font-medium text-sand-500 text-xs uppercase tracking-wider">Date</th>
                  <th className="px-5 py-3 font-medium text-sand-500 text-xs uppercase tracking-wider">Links</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-sand-50">
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className={`hover:bg-sand-50 cursor-pointer ${selectedId === item.id ? 'bg-sand-50' : ''}`}
                    onClick={() => loadDetail(item.id)}
                  >
                    <td className="px-5 py-3">
                      <span className="font-medium text-warm-900">
                        {truncate(item.subject || '(No subject)', 50)}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-sand-600">
                      {item.sender_name || item.sender_email}
                    </td>
                    <td className="px-5 py-3 text-sand-500 text-xs">
                      {formatDateTime(item.date_sent)}
                    </td>
                    <td className="px-5 py-3">
                      {item.invoice_links?.length ? (
                        <span className="inline-flex items-center gap-1 text-xs text-sunset-600">
                          <Link2 className="w-3.5 h-3.5" /> {item.invoice_links.length}
                        </span>
                      ) : (
                        <span className="text-xs text-sand-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-sand-100">
              <span className="text-xs text-sand-500">Page {page} of {totalPages}</span>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded-lg hover:bg-sand-100 disabled:opacity-30"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-1.5 rounded-lg hover:bg-sand-100 disabled:opacity-30"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Viewer & actions */}
        <div className="col-span-5 bg-white rounded-2xl border border-sand-200 shadow-sm min-h-[400px]">
          {!selected ? (
            <div className="flex flex-col items-center justify-center h-full py-12 text-sand-400">
              {loadingDetail ? (
                <div className="flex items-center gap-2 text-sm text-sand-500">
                  <Loader2 className="w-4 h-4 animate-spin" /> Loading...
                </div>
              ) : (
                <>
                  <Eye className="w-10 h-10 mb-2 text-sand-300" />
                  <p className="text-sm">Select an email to review</p>
                </>
              )}
            </div>
          ) : (
            <div className="p-4 space-y-3 overflow-y-auto max-h-[75vh]">
              <div className="flex items-center justify-between">
                <div className="text-xs text-sand-500">ID: {selected.id}</div>
                <div className="flex gap-2">
                  <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-green-50 text-green-600 hover:bg-green-100 disabled:opacity-50"
                  >
                    <Check className="w-3.5 h-3.5 inline mr-1" /> Approve
                  </button>
                  <button
                    onClick={handleReject}
                    disabled={actionLoading}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 text-red-600 hover:bg-red-100 disabled:opacity-50"
                  >
                    <X className="w-3.5 h-3.5 inline mr-1" /> Reject
                  </button>
                  <button
                    onClick={handleArchive}
                    disabled={actionLoading}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-sand-100 text-sand-700 hover:bg-sand-200 disabled:opacity-50"
                  >
                    <Archive className="w-3.5 h-3.5 inline mr-1" /> Archive
                  </button>
                </div>
              </div>

              {message && (
                <div className="text-xs text-sand-600 bg-sand-50 border border-sand-100 rounded-lg px-3 py-2">
                  {message}
                </div>
              )}

              <div className="border-b border-sand-100 pb-2">
                <p className="text-xs text-sand-500">From</p>
                <p className="text-sm text-warm-900">{selected.sender_name || selected.sender_email}</p>
                <p className="text-[11px] text-sand-500">{selected.sender_email}</p>
              </div>
              <div className="border-b border-sand-100 pb-2">
                <p className="text-xs text-sand-500">Subject</p>
                <p className="text-sm font-semibold text-warm-900">{selected.subject || '(No subject)'}</p>
              </div>
              <div className="text-xs text-sand-500">{formatDateTime(selected.date_sent)}</div>

              <div className="rounded-lg border border-sand-100 bg-sand-50 p-3">
                <p className="text-[11px] text-sand-500 mb-1">Body preview</p>
                {selected.body_html ? (
                  <div
                    className="prose prose-sm max-w-none text-sand-800"
                    dangerouslySetInnerHTML={{ __html: selected.body_html }}
                  />
                ) : (
                  <pre className="whitespace-pre-wrap text-[13px] text-sand-800">{selected.body_text || '(No body)'}</pre>
                )}
              </div>

              {/* Link preview & capture */}
              {selected.invoice_links && selected.invoice_links.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-sand-600 flex items-center gap-1">
                    <Link2 className="w-3.5 h-3.5" /> Links ({selected.invoice_links.length})
                  </p>
                  <select
                    className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                    value={previewLink}
                    onChange={e => setPreviewLink(e.target.value)}
                  >
                    <option value="">Select a link</option>
                    {selected.invoice_links.map((url: string, i: number) => (
                      <option key={i} value={url}>{truncate(url, 60)}</option>
                    ))}
                  </select>
                  {previewLink && (
                    <>
                      <div className="flex gap-2">
                        <button
                          onClick={handleCapture}
                          disabled={actionLoading}
                          className="px-3 py-2 rounded-lg text-xs font-medium bg-sand-100 text-sand-700 hover:bg-sand-200 disabled:opacity-50"
                        >
                          Capture screenshot
                        </button>
                        <a
                          href={previewLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3 py-2 rounded-lg text-xs font-medium bg-sand-100 text-sand-700 hover:bg-sand-200"
                        >
                          Open in new tab
                        </a>
                      </div>
                      <div className="h-64 border border-sand-200 rounded-lg overflow-hidden">
                        <iframe src={previewLink} title="Link preview" className="w-full h-full" />
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
