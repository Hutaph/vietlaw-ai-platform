'use client';

import React, { useState, useEffect } from 'react';
import { AlertCircle, ArrowLeft, BookOpen, Upload } from 'lucide-react';
import Link from 'next/link';
import DocumentList from '@/components/docs/DocumentList';
import UploadModal from '@/components/docs/UploadModal';
import ChunkViewer from '@/components/docs/ChunkViewer';

export default function DocumentDashboard() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const fetchDocuments = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const res = await fetch('/api/documents', { cache: 'no-store' });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.details || data.error || `HTTP ${res.status}`);
      }

      if (!Array.isArray(data.documents)) {
        throw new Error('Phản hồi từ máy chủ không đúng định dạng.');
      }

      setDocuments(data.documents);
    } catch (e: unknown) {
      console.error('Không thể tải kho tài liệu', e);
      setLoadError(e instanceof Error ? e.message : 'Không thể tải kho tài liệu.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col font-sans transition-colors">
      <header className="h-16 flex items-center justify-between px-6 bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-800 shrink-0">
        <div className="flex items-center gap-4">
          <Link 
            href="/"
            className="p-2 -ml-2 rounded-xl text-gray-500 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-300">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-[15px] font-bold text-gray-800 dark:text-gray-100 leading-tight">Kho tài liệu</h1>
              <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400">Quản lý & trực quan hóa dữ liệu pháp luật</p>
            </div>
          </div>
        </div>
        <button
          onClick={() => setIsUploadOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-[13px] font-semibold rounded-xl transition-all shadow-sm shadow-rose-600/15 active:scale-95"
        >
          <Upload className="w-4 h-4" />
          Tải tài liệu lên
        </button>
      </header>

      <main className="flex-1 overflow-hidden flex relative">
        <div className={`flex-1 overflow-y-auto p-6 transition-all duration-300 ${selectedDocId ? 'pr-[400px]' : ''}`}>
          <div className="max-w-6xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100">Tất cả tài liệu ({documents.length})</h2>
            </div>
            
            {isLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3, 4, 5, 6].map(i => (
                  <div key={i} className="h-32 bg-white dark:bg-slate-900 rounded-2xl border border-gray-100 dark:border-slate-800 animate-pulse p-5">
                    <div className="w-10 h-10 bg-gray-200 dark:bg-slate-800 rounded-xl mb-4"></div>
                    <div className="h-4 bg-gray-200 dark:bg-slate-800 rounded w-3/4 mb-2"></div>
                    <div className="h-3 bg-gray-200 dark:bg-slate-800 rounded w-1/2"></div>
                  </div>
                ))}
              </div>
            ) : loadError ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="w-16 h-16 bg-red-50 dark:bg-red-500/10 rounded-full flex items-center justify-center mb-4">
                  <AlertCircle className="w-8 h-8 text-red-500" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">Không thể tải kho tài liệu</h3>
                <p className="text-gray-500 dark:text-gray-400 max-w-lg mb-5">{loadError}</p>
                <button
                  type="button"
                  onClick={fetchDocuments}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-sm font-semibold rounded-xl transition-colors"
                >
                  Thử lại
                </button>
              </div>
            ) : (
              <DocumentList 
                documents={documents} 
                selectedId={selectedDocId} 
                onSelect={setSelectedDocId} 
              />
            )}
          </div>
        </div>
        
        {/* Bảng chi tiết các đoạn dữ liệu */}
        <div className={`absolute top-0 right-0 h-full bg-white dark:bg-slate-900 border-l border-gray-200 dark:border-slate-800 shadow-2xl transition-transform duration-300 w-[400px] flex flex-col ${selectedDocId ? 'translate-x-0' : 'translate-x-full'}`}>
          {selectedDocId && (
            <ChunkViewer 
              lawId={selectedDocId} 
              onClose={() => setSelectedDocId(null)} 
            />
          )}
        </div>
      </main>

      {isUploadOpen && (
        <UploadModal 
          onClose={() => setIsUploadOpen(false)} 
          onSuccess={() => {
            setIsUploadOpen(false);
            fetchDocuments();
          }} 
        />
      )}
    </div>
  );
}
