import { useEffect, useState } from 'react';
import { FileText, Download, Eye, ShieldCheck, ChevronLeft, ChevronRight } from 'lucide-react';
import { getDocuments, getDocumentPreviewUrl, getDocumentDownloadUrl } from '../lib/api';
import { formatBytes, formatDateTime, truncate } from '../lib/utils';

export default function Documents() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<any | null>(null);
  const pageSize = 20;

  const load = async () => {
    setLoading(true);
    try {
      const resp = await getDocuments({ page, page_size: pageSize });
      setDocuments(resp.data.documents);
      setTotal(resp.data.total);
    } catch { /* API not available */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, [page]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-warm-900">Documents</h2>
        <p className="text-sm text-sand-600 mt-0.5">
          {total} document{total !== 1 ? 's' : ''} stored
        </p>
      </div>

      <div className="flex gap-6">
        {/* Document Grid */}
        <div className="flex-1">
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <div className="animate-spin rounded-full h-7 w-7 border-2 border-sunset-400 border-t-transparent" />
            </div>
          ) : documents.length === 0 ? (
            <div className="bg-white rounded-2xl border border-sand-200 shadow-sm flex flex-col items-center justify-center py-16 text-sand-400">
              <FileText className="w-12 h-12 mb-3 text-sand-300" />
              <p className="text-sm font-medium">No documents yet</p>
              <p className="text-xs mt-1">Documents will appear here after email ingestion</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {documents.map((doc: any) => (
                <div
                  key={doc.id}
                  className="bg-white rounded-2xl border border-sand-200 shadow-sm hover:shadow-md hover:border-sunset-200 transition-all duration-200 overflow-hidden cursor-pointer"
                  onClick={() => setPreview(doc)}
                >
                  {/* Preview Thumbnail */}
                  <div className="h-36 bg-gradient-to-br from-sand-100 to-sand-200 flex items-center justify-center">
                    <FileText className="w-12 h-12 text-sand-400" />
                  </div>

                  <div className="p-4">
                    <p className="text-sm font-semibold text-warm-900 leading-snug">
                      {truncate(doc.original_filename, 40)}
                    </p>

                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {doc.classification && (
                        <span className="px-2 py-0.5 bg-sunset-100 text-sunset-700 rounded-full text-[10px] font-medium">
                          {doc.classification}
                        </span>
                      )}
                      {doc.category && (
                        <span className="px-2 py-0.5 bg-warm-100 text-warm-700 rounded-full text-[10px] font-medium">
                          {doc.category}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center justify-between mt-3 text-xs text-sand-500">
                      <span>{formatBytes(doc.file_size)}</span>
                      <span>{formatDateTime(doc.date_ingested)}</span>
                    </div>

                    {doc.sender_name && (
                      <p className="text-xs text-sand-400 mt-1">From: {doc.sender_name}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
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

        {/* Preview Panel */}
        {preview && (
          <div className="w-80 shrink-0 bg-white rounded-2xl border border-sand-200 shadow-sm p-5 sticky top-20 self-start">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-warm-900 text-sm">Document Preview</h3>
              <button onClick={() => setPreview(null)} className="text-sand-400 hover:text-warm-600 text-xs">
                Close
              </button>
            </div>

            {/* Preview Image */}
            <div className="h-64 bg-sand-100 rounded-xl mb-4 flex items-center justify-center overflow-hidden relative">
              <img
                src={getDocumentPreviewUrl(preview.id)}
                alt="Preview"
                className="max-h-full max-w-full object-contain"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                  const fallback = e.currentTarget.parentElement?.querySelector('.preview-fallback');
                  if (fallback) (fallback as HTMLElement).style.display = 'flex';
                }}
              />
              <div className="preview-fallback hidden absolute inset-0 items-center justify-center">
                <div className="text-center text-sand-500 text-xs">
                  <FileText className="w-10 h-10 mx-auto mb-2 text-sand-300" />
                  <p>Preview not available</p>
                </div>
              </div>
            </div>

            <p className="text-sm font-medium text-warm-900 break-words">{preview.original_filename}</p>

            <div className="space-y-2 mt-3 text-xs text-sand-600">
              <div className="flex justify-between"><span>Size</span><span>{formatBytes(preview.file_size)}</span></div>
              <div className="flex justify-between"><span>Pages</span><span>{preview.page_count}</span></div>
              <div className="flex justify-between"><span>Type</span><span>{preview.classification || '—'}</span></div>
              <div className="flex justify-between"><span>Hash verified</span>
                <span className="flex items-center gap-1">
                  {preview.hash_verified ? <ShieldCheck className="w-3 h-3 text-green-500" /> : null}
                  {preview.hash_verified ? 'Yes' : 'No'}
                </span>
              </div>
            </div>

            {preview.llm_summary && (
              <div className="mt-3 p-3 bg-sand-50 rounded-lg">
                <p className="text-[11px] font-medium text-sand-500 mb-1">AI Summary</p>
                <p className="text-xs text-warm-800 leading-relaxed">{preview.llm_summary}</p>
              </div>
            )}

            <div className="flex gap-2 mt-4">
              <a
                href={getDocumentDownloadUrl(preview.id)}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-sunset-500 text-white rounded-xl text-xs font-medium hover:bg-sunset-600 transition-colors"
              >
                <Download className="w-3.5 h-3.5" /> Download
              </a>
              <button className="flex items-center justify-center gap-1.5 px-3 py-2 bg-sand-100 text-warm-700 rounded-xl text-xs font-medium hover:bg-sand-200 transition-colors">
                <Eye className="w-3.5 h-3.5" /> View
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
