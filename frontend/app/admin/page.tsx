'use client';

import React from 'react';
import { Settings, BarChart2, BookOpen, Plus, BrainCircuit } from 'lucide-react';
import AnalyticsTab from '@/components/admin/AnalyticsTab';
import DocumentList from '@/components/docs/DocumentList';
import UploadModal from '@/components/docs/UploadModal';
import Link from 'next/link';
import SystemSettingsTab from '@/components/admin/SystemSettingsTab';
import ChunkViewer from '@/components/docs/ChunkViewer';

export default function AdminPage() {
  const [activeTab, setActiveTab] = React.useState<'analytics' | 'docs' | 'settings'>('analytics');
  const [isUploadOpen, setIsUploadOpen] = React.useState(false);
  const [selectedDocId, setSelectedDocId] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (window.location.hash === '#settings') setActiveTab('settings');
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col font-sans">
      <header className="h-16 flex items-center justify-between px-6 bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-800 shrink-0">
        <div className="flex items-center gap-4">
          <Link href="/" className="p-2 -ml-2 rounded-xl text-gray-500 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-arrow-left"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400">
              <Settings className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 dark:text-white leading-tight">Quản trị hệ thống</h1>
              <p className="text-xs text-gray-500 font-medium">Thống kê và quản lý dữ liệu</p>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto p-6 lg:p-8 space-y-8">
          
          <div className="flex p-1 bg-gray-100/80 dark:bg-slate-800/80 rounded-xl w-max border border-gray-200/50 dark:border-slate-700/50">
            <button
              onClick={() => setActiveTab('analytics')}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'analytics'
                  ? 'bg-white dark:bg-slate-900 text-rose-600 dark:text-rose-400 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-200/50 dark:hover:bg-slate-700/50'
              }`}
            >
              <BarChart2 className="w-4 h-4" />
              Thống kê & Lịch sử
            </button>
            <button
              onClick={() => setActiveTab('docs')}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'docs'
                  ? 'bg-white dark:bg-slate-900 text-rose-600 dark:text-rose-400 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-200/50 dark:hover:bg-slate-700/50'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              Quản lý tài liệu
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'settings'
                  ? 'bg-white dark:bg-slate-900 text-rose-600 dark:text-rose-400 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-200/50 dark:hover:bg-slate-700/50'
              }`}
            >
              <BrainCircuit className="w-4 h-4" />
              Cấu hình AI
            </button>
          </div>

          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-800 shadow-sm p-6">
            {activeTab === 'analytics' ? (
              <AnalyticsTab />
            ) : activeTab === 'settings' ? (
              <SystemSettingsTab />
            ) : (
              <div className="relative min-h-[520px] overflow-hidden">
                <div className={`space-y-4 transition-all duration-300 ${selectedDocId ? 'lg:pr-[420px]' : ''}`}>
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h2 className="text-lg font-bold text-gray-900 dark:text-white">Kho tài liệu</h2>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                      Danh sách văn bản luật đã được nạp vào hệ thống truy xuất.
                    </p>
                  </div>
                  <button 
                    onClick={() => setIsUploadOpen(true)}
                    className="flex shrink-0 items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-medium shadow-sm shadow-rose-600/15 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    Thêm tài liệu
                  </button>
                </div>
                <DocumentList
                  isAdmin={true}
                  selectedId={selectedDocId}
                  onSelect={setSelectedDocId}
                />
                </div>
                <div className={`absolute inset-y-0 right-0 z-20 w-full max-w-[400px] border-l border-gray-200 bg-white shadow-2xl transition-transform duration-300 dark:border-slate-800 dark:bg-slate-900 ${selectedDocId ? 'translate-x-0' : 'translate-x-full'}`}>
                  {selectedDocId && (
                    <ChunkViewer
                      lawId={selectedDocId}
                      onClose={() => setSelectedDocId(null)}
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {isUploadOpen && (
        <UploadModal 
          onClose={() => setIsUploadOpen(false)} 
          onSuccess={() => {
            setIsUploadOpen(false);
            window.location.reload();
          }} 
        />
      )}
    </div>
  );
}
