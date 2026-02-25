import { useEffect, useState } from 'react';
import { Folder, FileText, ChevronRight, Home, ArrowLeft } from 'lucide-react';
import { browseFiles } from '../lib/api';
import { formatBytes, formatDateTime } from '../lib/utils';

export default function FileBrowser() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [currentPath, setCurrentPath] = useState('');
  const [pathHistory, setPathHistory] = useState<string[]>(['']);
  const [loading, setLoading] = useState(true);
  const [totalFiles, setTotalFiles] = useState(0);
  const [totalSize, setTotalSize] = useState(0);

  const load = async (path: string) => {
    setLoading(true);
    try {
      const resp = await browseFiles(path || undefined);
      setNodes(resp.data.nodes || []);
      setTotalFiles(resp.data.total_files || 0);
      setTotalSize(resp.data.total_size || 0);
    } catch {
      setNodes([]);
    }
    setLoading(false);
  };

  useEffect(() => { load(currentPath); }, [currentPath]);

  const navigateTo = (path: string) => {
    setPathHistory(prev => [...prev, currentPath]);
    setCurrentPath(path);
  };

  const goBack = () => {
    const prev = pathHistory[pathHistory.length - 1];
    setPathHistory(h => h.slice(0, -1));
    setCurrentPath(prev ?? '');
  };

  const goHome = () => {
    setPathHistory(['']);
    setCurrentPath('');
  };

  const breadcrumbs = currentPath ? currentPath.split(/[/\\]/).filter(Boolean) : [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-warm-900">Files</h2>
        <p className="text-sm text-sand-600 mt-0.5">
          Browse your document storage
        </p>
      </div>

      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-1 bg-white rounded-xl border border-sand-200 px-4 py-2.5 shadow-sm">
        <button onClick={goHome} className="p-1 rounded hover:bg-sand-100 text-sand-500 hover:text-warm-700 transition-colors">
          <Home className="w-4 h-4" />
        </button>
        {pathHistory.length > 1 && (
          <button onClick={goBack} className="p-1 rounded hover:bg-sand-100 text-sand-500 hover:text-warm-700 transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </button>
        )}
        <ChevronRight className="w-3.5 h-3.5 text-sand-300 mx-1" />
        <span className="text-xs text-sand-500 font-medium">Documents</span>
        {breadcrumbs.map((part, i) => (
          <span key={i} className="flex items-center">
            <ChevronRight className="w-3.5 h-3.5 text-sand-300 mx-1" />
            <span className="text-xs text-warm-700 font-medium">{part}</span>
          </span>
        ))}

        <span className="ml-auto text-[11px] text-sand-400">
          {totalFiles} file{totalFiles !== 1 ? 's' : ''} · {formatBytes(totalSize)}
        </span>
      </div>

      {/* File Grid */}
      <div className="bg-white rounded-2xl border border-sand-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-7 w-7 border-2 border-sunset-400 border-t-transparent" />
          </div>
        ) : nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-sand-400">
            <Folder className="w-12 h-12 mb-3 text-sand-300" />
            <p className="text-sm font-medium">Empty directory</p>
          </div>
        ) : (
          <div className="divide-y divide-sand-50">
            {nodes.map((node: any, idx: number) => (
              <div
                key={idx}
                className="flex items-center gap-3 px-5 py-3 hover:bg-sand-50 transition-colors cursor-pointer"
                onClick={() => node.type === 'directory' ? navigateTo(node.path) : null}
              >
                {node.type === 'directory' ? (
                  <div className="w-9 h-9 rounded-lg bg-sunset-100 flex items-center justify-center shrink-0">
                    <Folder className="w-5 h-5 text-sunset-500" />
                  </div>
                ) : (
                  <div className="w-9 h-9 rounded-lg bg-sand-100 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-sand-500" />
                  </div>
                )}

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-warm-900 truncate">{node.name}</p>
                  {node.modified && (
                    <p className="text-[11px] text-sand-400">{formatDateTime(node.modified)}</p>
                  )}
                </div>

                <div className="text-xs text-sand-400 shrink-0">
                  {node.type === 'directory'
                    ? `${node.size} item${node.size !== 1 ? 's' : ''}`
                    : formatBytes(node.size)
                  }
                </div>

                {node.type === 'directory' && (
                  <ChevronRight className="w-4 h-4 text-sand-300" />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
