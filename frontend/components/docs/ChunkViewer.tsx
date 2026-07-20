import React, { useState, useEffect } from 'react';
import { X, Layers, Database, Hash } from 'lucide-react';

interface ChunkViewerProps {
  lawId: string;
  onClose: () => void;
}

interface Chunk {
  id: string;
  content: string;
  position: any;
}

export default function ChunkViewer({ lawId, onClose }: ChunkViewerProps) {
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchChunks = async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`/api/documents/${lawId}/chunks`);
        if (res.ok) {
          const data = await res.json();
          setChunks(data.chunks || []);
        }
      } catch (e) {
        console.error('Failed to fetch chunks', e);
      } finally {
        setIsLoading(false);
      }
    };
    
    if (lawId) {
      fetchChunks();
    }
  }, [lawId]);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-900 shadow-2xl">
      <div className="h-16 border-b border-gray-200 dark:border-slate-800 flex items-center justify-between px-6 shrink-0 bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-[14px] font-bold text-gray-900 dark:text-white">Cấu trúc Chunking</h3>
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
        ) : chunks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-gray-500 text-sm">
            <Database className="w-8 h-8 mb-2 opacity-20" />
            Không tìm thấy chunk nào cho tài liệu này.
          </div>
        ) : (
          <div className="space-y-4 relative before:absolute before:inset-y-0 before:left-[19px] before:w-px before:bg-indigo-100 dark:before:bg-indigo-900/50">
            <div className="text-[11px] font-medium text-gray-500 mb-6 pl-12">
              Tìm thấy <span className="text-indigo-600 dark:text-indigo-400 font-bold">{chunks.length}</span> chunks
            </div>
            {chunks.map((chunk, index) => (
              <div key={chunk.id} className="relative pl-12">
                <div className="absolute left-[13px] top-4 w-3 h-3 rounded-full border-2 border-indigo-600 dark:border-indigo-400 bg-white dark:bg-slate-900 z-10 shadow-sm ring-4 ring-slate-50 dark:ring-slate-950"></div>
                
                <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-gray-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow hover:border-indigo-300 dark:hover:border-indigo-700 group">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-1.5 text-[11px] font-mono text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-slate-800 px-2 py-0.5 rounded-md">
                      <Hash className="w-3 h-3" />
                      {chunk.id.split('_').pop() || chunk.id}
                    </div>
                    {chunk.position && Object.keys(chunk.position).length > 0 && (
                      <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-100 dark:border-emerald-500/20">
                        {chunk.position.chapter ? `Chương ${chunk.position.chapter}` : ''}
                        {chunk.position.section ? ` - Mục ${chunk.position.section}` : ''}
                        {chunk.position.clause ? ` - Điều/Khoản ${chunk.position.clause}` : ''}
                      </span>
                    )}
                  </div>
                  <div className="text-[13px] text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {chunk.content}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
