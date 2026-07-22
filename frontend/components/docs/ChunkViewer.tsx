import React, { useState, useEffect } from 'react';
import { X, Layers, Database, Hash } from 'lucide-react';

interface ChunkViewerProps {
  lawId: string;
  onClose: () => void;
}

interface Chunk {
  id: string;
  content: string;
  position?: {
    article?: string | null;
    chapter?: string | null;
    clause?: string | null;
    point?: string | null;
    section?: string | null;
  };
}

export default function ChunkViewer({ lawId, onClose }: ChunkViewerProps) {
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchChunks = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/documents/${lawId}/chunks`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.details || data.error || `HTTP ${res.status}`);
        }
        if (!Array.isArray(data.chunks)) {
          throw new Error('Phản hồi từ máy chủ không đúng định dạng.');
        }
        setChunks(data.chunks || []);
      } catch (e) {
        console.error('Không thể tải các đoạn dữ liệu', e);
        setError(e instanceof Error ? e.message : 'Không thể tải các đoạn dữ liệu.');
      } finally {
        setIsLoading(false);
      }
    };
    
    if (lawId) {
      fetchChunks();
    }
  }, [lawId]);

  const getReadableChunkId = (id: string) => {
    const paragraphMatch = id.match(/:p(\d+)$/i);
    if (paragraphMatch) return `Đoạn ${paragraphMatch[1]}`;

    const articleMatch = id.match(/article-(\d+)/i);
    if (articleMatch) return `Điều ${articleMatch[1]}`;

    return 'Đoạn dữ liệu';
  };

  const getReadablePosition = (chunk: Chunk) => {
    const position = chunk.position;
    if (!position) return '';

    const parts = [
      position.chapter ? `Chương ${position.chapter}` : '',
      position.section ? `Mục ${position.section}` : '',
      position.article ? `Điều ${position.article}` : '',
      position.clause ? `Khoản ${position.clause}` : '',
      position.point ? `Điểm ${position.point}` : '',
    ].filter(Boolean);

    return parts.join(', ');
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-900 shadow-2xl">
      <div className="h-16 border-b border-gray-200 dark:border-slate-800 flex items-center justify-between px-6 shrink-0 bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-300 flex items-center justify-center">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-[14px] font-bold text-gray-900 dark:text-white">Các đoạn dữ liệu</h3>
            <p className="text-[11px] text-gray-500 dark:text-gray-400 font-mono">{lawId}</p>
          </div>
        </div>
        <button 
          onClick={onClose}
          className="p-2 -mr-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 bg-slate-50/30 dark:bg-slate-950/30 custom-scrollbar">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-gray-100 dark:border-slate-800 animate-pulse">
                <div className="h-4 bg-gray-200 dark:bg-slate-800 rounded w-1/3 mb-3"></div>
                <div className="space-y-2">
                  <div className="h-3 bg-gray-200 dark:bg-slate-800 rounded w-full"></div>
                  <div className="h-3 bg-gray-200 dark:bg-slate-800 rounded w-5/6"></div>
                  <div className="h-3 bg-gray-200 dark:bg-slate-800 rounded w-4/6"></div>
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-40 text-center text-gray-500 text-sm">
            <Database className="w-8 h-8 mb-2 opacity-20" />
            <p className="font-medium text-gray-700 dark:text-gray-300">Không thể tải các đoạn dữ liệu.</p>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{error}</p>
          </div>
        ) : chunks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-gray-500 text-sm">
            <Database className="w-8 h-8 mb-2 opacity-20" />
            Không tìm thấy đoạn dữ liệu nào cho văn bản này.
          </div>
        ) : (
          <div className="space-y-4 relative before:absolute before:inset-y-0 before:left-[19px] before:w-px before:bg-rose-100 dark:before:bg-rose-900/50">
            <div className="text-[11px] font-medium text-gray-500 mb-6 pl-12">
              Tìm thấy <span className="text-rose-600 dark:text-rose-300 font-bold">{chunks.length}</span> đoạn dữ liệu
            </div>
            {chunks.map(chunk => {
              const positionLabel = getReadablePosition(chunk);

              return (
                <div key={chunk.id} className="relative pl-12">
                  <div className="absolute left-[13px] top-4 w-3 h-3 rounded-full border-2 border-rose-600 dark:border-rose-300 bg-white dark:bg-slate-900 z-10 shadow-sm ring-4 ring-slate-50 dark:ring-slate-950"></div>
                  
                  <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-gray-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow hover:border-rose-200 dark:hover:border-rose-900/70 group">
                    <div className="mb-3 flex flex-wrap items-center gap-2">
                      <div
                        className="inline-flex min-w-0 items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                        title={chunk.id}
                      >
                        <Hash className="w-3 h-3" />
                        <span className="truncate">{getReadableChunkId(chunk.id)}</span>
                      </div>
                      {positionLabel && (
                        <span className="inline-flex max-w-full rounded-full border border-rose-100 bg-rose-50 px-2.5 py-1 text-[11px] font-semibold leading-4 text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300">
                          {positionLabel}
                        </span>
                      )}
                    </div>
                    <div className="text-[13px] text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                      {chunk.content}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
