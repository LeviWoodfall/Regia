import { useEffect, useState } from 'react';
import {
  Mail, Paperclip, Link2, ChevronLeft, ChevronRight, Loader2, Eye, RotateCw, Trash2,
} from 'lucide-react';
import { getEmails, getEmail, redownloadEmail, deleteEmail, refreshEmailFiles, downloadAllEmailDocs, downloadAllAttachments, captureLink, getDocumentPreviewUrl } from '../lib/api';
import { formatDateTime, truncate } from '../lib/utils';

export default function Emails() {
  const [emails, setEmails] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedEmail, setSelectedEmail] = useState<any | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [actionMessage, setActionMessage] = useState<string>('');
  const [actionLoading, setActionLoading] = useState(false);
  const [previewLink, setPreviewLink] = useState<string>('');
  const [attachmentPreview, setAttachmentPreview] = useState<any | null>(null);
  const pageSize = 20;

  const load = async () => {
    setLoading(true);
    try {
      const resp = await getEmails({ page, page_size: pageSize });
      setEmails(resp.data.emails);
      setTotal(resp.data.total);
    } catch {
      /* ignore */
    }
    setLoading(false);
  };

  const handleCaptureLink = async () => {
    if (!selectedId || !previewLink) return;
    setActionLoading(true);
    setActionMessage('');
    try {
      await captureLink(selectedId, previewLink, 'captured_link.pdf');
      setActionMessage('Link captured to PDF and saved');
      await loadEmailDetail(selectedId);
    } catch {
      setActionMessage('Capture failed');
    }
    setActionLoading(false);
  };

  const handleRefreshFiles = async () => {
    if (!selectedId) return;
    setActionLoading(true);
    setActionMessage('');
    try {
      await refreshEmailFiles(selectedId);
      setActionMessage('Files refreshed');
      await loadEmailDetail(selectedId);
    } catch {
      setActionMessage('Refresh failed');
    }
    setActionLoading(false);
  };

  const handleDownloadAll = async () => {
    if (!selectedId) return;
    setActionLoading(true);
    setActionMessage('');
    try {
      const resp = await downloadAllEmailDocs(selectedId);
      const blob = new Blob([resp.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `email_${selectedId}_attachments.zip`;
      a.click();
      window.URL.revokeObjectURL(url);
      setActionMessage('Download started');
    } catch {
      setActionMessage('Download failed');
    }
    setActionLoading(false);
  };

  useEffect(() => { load(); }, [page]);

  const loadEmailDetail = async (id: number) => {
    setLoadingDetail(true);
    try {
      const resp = await getEmail(id);
      setSelectedEmail(resp.data);
      setSelectedId(id);
      setActionMessage('');
    } catch {
      setSelectedEmail(null);
    }
    setLoadingDetail(false);
  };

  const handleRedownload = async () => {
    if (!selectedId) return;
    setActionLoading(true);
    setActionMessage('');
    try {
      await redownloadEmail(selectedId);
      setActionMessage('Re-download complete (deduped)');
      await loadEmailDetail(selectedId);
    } catch {
      setActionMessage('Re-download failed');
    }
    setActionLoading(false);
  };

  const handleDelete = async (deleteRemote: boolean) => {
    if (!selectedId) return;
    setActionLoading(true);
    setActionMessage('');
    try {
      await deleteEmail(selectedId, deleteRemote);
      setActionMessage('Email deleted');
      setSelectedEmail(null);
      setSelectedId(null);
      load();
    } catch {
      setActionMessage('Delete failed');
    }
    setActionLoading(false);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-warm-900">Emails</h2>
          <p className="text-sm text-sand-600 mt-0.5">
            {total} ingested email{total !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={async () => {
            setActionLoading(true);
            setActionMessage('');
            try {
              const resp = await downloadAllAttachments();
              const blob = new Blob([resp.data], { type: 'application/zip' });
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = 'regia_all_attachments.zip';
              a.click();
              window.URL.revokeObjectURL(url);
              setActionMessage('Download started');
            } catch {
              setActionMessage('Download failed');
            }
            setActionLoading(false);
          }}
          disabled={actionLoading}
          className="px-3 py-2 rounded-lg text-xs font-medium bg-sand-100 text-sand-700 hover:bg-sand-200 disabled:opacity-50"
        >
          <Paperclip className="w-3.5 h-3.5 inline mr-1" /> Download all attachments
        </button>
      </div>

      <div className="grid grid-cols-12 gap-3">
        {/* Email Table */}
        <div className="col-span-7 bg-white rounded-2xl border border-sand-200 shadow-sm overflow-hidden">
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
                  <tr
                    key={email.id}
                    className={`hover:bg-sand-50 transition-colors cursor-pointer ${selectedId === email.id ? 'bg-sand-50' : ''}`}
                    onClick={() => loadEmailDetail(email.id)}
                  >
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

        {/* Preview Pane */}
        <div className="col-span-5 bg-white rounded-2xl border border-sand-200 shadow-sm min-h-[400px]">
          {!selectedEmail ? (
            <div className="flex flex-col items-center justify-center h-full py-12 text-sand-400">
              {loadingDetail ? (
                <div className="flex items-center gap-2 text-sand-500 text-sm">
                  <Loader2 className="w-4 h-4 animate-spin" /> Loading email...
                </div>
              ) : (
                <>
                  <Eye className="w-10 h-10 mb-2 text-sand-300" />
                  <p className="text-sm">Select an email to preview</p>
                </>
              )}
            </div>
          ) : (
            <div className="p-4 space-y-3 overflow-y-auto max-h-[75vh]">
              <div className="flex items-center justify-between">
                <div className="text-xs text-sand-500">ID: {selectedEmail.email.id}</div>
                <div className="flex gap-2">
                  <button
                    onClick={handleRefreshFiles}
                    disabled={actionLoading}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-sand-100 text-sand-700 hover:bg-sand-200 disabled:opacity-50"
                  >
                    <RotateCw className="w-3.5 h-3.5 inline mr-1" /> Refresh files
                  </button>
                  <button
                    onClick={handleRedownload}
                    disabled={actionLoading}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-sand-100 text-sand-700 hover:bg-sand-200 disabled:opacity-50"
                  >
                    <RotateCw className="w-3.5 h-3.5 inline mr-1" /> Redownload
                  </button>
                  <button
                    onClick={handleDownloadAll}
                    disabled={actionLoading}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-sand-100 text-sand-700 hover:bg-sand-200 disabled:opacity-50"
                  >
                    <Paperclip className="w-3.5 h-3.5 inline mr-1" /> Download all
                  </button>
                  <button
                    onClick={() => setPreviewLink(selectedEmail.email.invoice_links?.[0] || '')}
                    disabled={!selectedEmail.email.invoice_links || selectedEmail.email.invoice_links.length === 0}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-sand-100 text-sand-700 hover:bg-sand-200 disabled:opacity-50"
                  >
                    Preview link
                  </button>
                  <button
                    onClick={() => handleDelete(true)}
                    disabled={actionLoading}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 text-red-600 hover:bg-red-100 disabled:opacity-50"
                  >
                    <Trash2 className="w-3.5 h-3.5 inline mr-1" /> Delete (remote)
                  </button>
                </div>
              </div>

              {actionMessage && (
                <div className="text-xs text-sand-600 bg-sand-50 border border-sand-100 rounded-lg px-3 py-2">
                  {actionMessage}
                </div>
              )}

              <div className="border-b border-sand-100 pb-2">
                <p className="text-xs text-sand-500">From</p>
                <p className="text-sm text-warm-900">{selectedEmail.email.sender_name || selectedEmail.email.sender_email}</p>
                <p className="text-[11px] text-sand-500">{selectedEmail.email.sender_email}</p>
              </div>
              <div className="border-b border-sand-100 pb-2">
                <p className="text-xs text-sand-500">Subject</p>
                <p className="text-sm font-semibold text-warm-900">{selectedEmail.email.subject || '(No subject)'}</p>
              </div>
              <div className="text-xs text-sand-500">
                {formatDateTime(selectedEmail.email.date_sent)}
              </div>

              <div className="rounded-lg border border-sand-100 bg-sand-50 p-3">
                <p className="text-[11px] text-sand-500 mb-1">Body preview</p>
                {selectedEmail.email.body_html ? (
                  <div
                    className="prose prose-sm max-w-none text-sand-800"
                    dangerouslySetInnerHTML={{ __html: selectedEmail.email.body_html }}
                  />
                ) : (
                  <pre className="whitespace-pre-wrap text-[13px] text-sand-800">{selectedEmail.email.body_text || '(No body)'}</pre>
                )}
              </div>

              {selectedEmail.documents?.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-sand-600 flex items-center gap-1">
                    <Paperclip className="w-3.5 h-3.5" /> Attachments ({selectedEmail.documents.length})
                  </p>
                  <div className="space-y-1">
                    {selectedEmail.documents.map((doc: any) => (
                      <div key={doc.id} className="px-2 py-1.5 rounded-lg border border-sand-100 flex items-center justify-between text-sm text-sand-700">
                        <div className="truncate">
                          <span className="font-medium text-warm-900">{doc.original_filename}</span>
                          <span className="text-[11px] text-sand-500 ml-2">{Math.round(doc.file_size / 1024)} KB</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setAttachmentPreview(doc)}
                            className="text-[11px] px-2 py-1 bg-sand-100 text-sand-700 rounded hover:bg-sand-200"
                          >
                            Preview
                          </button>
                          <span className="text-[11px] text-sand-500">{doc.mime_type}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Link preview & capture */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={previewLink}
                    onChange={e => setPreviewLink(e.target.value)}
                    placeholder="Paste link to preview/capture"
                    className="flex-1 px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                  />
                  <button
                    onClick={handleCaptureLink}
                    disabled={actionLoading || !previewLink}
                    className="px-3 py-2 rounded-lg text-xs font-medium bg-sand-100 text-sand-700 hover:bg-sand-200 disabled:opacity-50"
                  >
                    Print to PDF
                  </button>
                </div>
                {previewLink && (
                  <div className="h-64 border border-sand-200 rounded-lg overflow-hidden">
                    <iframe src={previewLink} title="Link preview" className="w-full h-full" />
                  </div>
                )}
              </div>

              {attachmentPreview && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-sand-600">Attachment preview: {attachmentPreview.original_filename}</p>
                    <button
                      onClick={() => setAttachmentPreview(null)}
                      className="text-[11px] text-sand-500 hover:text-warm-700"
                    >
                      Close
                    </button>
                  </div>
                  <div className="h-64 border border-sand-200 rounded-lg overflow-hidden bg-sand-50 flex items-center justify-center">
                    <img
                      src={getDocumentPreviewUrl(attachmentPreview.id)}
                      alt="Preview"
                      className="max-h-full max-w-full object-contain"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
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
