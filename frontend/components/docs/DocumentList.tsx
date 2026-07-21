'use client';

import React, { useState, useEffect } from 'react';
import { FileText, ChevronRight, Trash2, Scale } from 'lucide-react';

interface Document {
  id: string;
  name: string;
  summary?: string;
  category: string;
  metadata?: {
    category?: string;
  };
}

interface DocumentListProps {
  documents?: Document[];
  selectedId?: string | null;
  onSelectDoc?: (doc: Document) => void;
  onSelect?: (id: string) => void;
  isAdmin?: boolean;
}

export default function DocumentList({ documents: propDocuments, selectedId, onSelect, onSelectDoc, isAdmin = false }: DocumentListProps) {
  const [fetchedDocuments, setFetchedDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const res = await fetch('/api/documents');
        if (!res.ok) {
          throw new Error(`Không thể tải danh sách tài liệu: ${res.statusText}`);
        }
        const data = await res.json();
        setFetchedDocuments(data.documents || []);
      } catch (error) {
        console.error('Không thể tải danh sách tài liệu:', error);
      } finally {
        setLoading(false);
      }
    };
    
    if (!propDocuments) {
      fetchDocs();
    } else {
      setLoading(false);
    }
  }, [propDocuments]);

  const displayDocuments = propDocuments || fetchedDocuments;

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm('Bạn có chắc chắn muốn xóa tài liệu này? Hành động này không thể hoàn tác.')) {
      return;
    }
    
    try {
      const res = await fetch(`/api/documents/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        if (!propDocuments) {
          setFetchedDocuments(fetchedDocuments.filter(doc => doc.id !== id));
        } else {
          window.location.reload();
        }
      } else {
        alert('Có lỗi xảy ra khi xóa tài liệu');
      }
    } catch (error) {
      alert('Lỗi kết nối');
    }
  };

  if (loading) {
    return <div className="text-center py-20 text-gray-500">Đang tải...</div>;
  }

  if (displayDocuments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 bg-gray-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-4">
          <FileText className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">Chưa có tài liệu nào</h3>
        <p className="text-gray-500 dark:text-gray-400 max-w-sm">
          Tải lên tài liệu của bạn để bắt đầu phân tích và tìm kiếm.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {displayDocuments.map((doc) => (
        <div 
          key={doc.id}
          onClick={() => {
            if (onSelectDoc) onSelectDoc(doc);
            if (onSelect) onSelect(doc.id);
          }}
          className={`p-5 rounded-2xl border transition-all cursor-pointer flex flex-col group ${
            selectedId === doc.id 
              ? 'border-indigo-500 ring-1 ring-indigo-500 shadow-sm bg-white dark:bg-slate-900' 
              : 'bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-md hover:-translate-y-1'
          }`}
        >
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              {doc.metadata?.category ? <Scale className="w-5 h-5" /> : <FileText className="w-5 h-5" />}
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                {(() => {
                  const cat = doc.metadata?.category || doc.category || '';
                  const map: Record<string, string> = {
                    'real-estate': 'Bất động sản',
                    'construction-environment': 'Xây dựng - Môi trường',
                    'land': 'Đất đai',
                    'civil': 'Dân sự',
                    'criminal': 'Hình sự',
                    'enterprise': 'Doanh nghiệp',
                    'all': 'Chung',
                  };
                  return map[cat.toLowerCase()] || cat || 'Chưa phân loại';
                })()}
              </span>
              {isAdmin && (
                <button
                  onClick={(e) => handleDelete(e, doc.id)}
                  className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                  title="Xóa tài liệu"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
          
          <h3 className="text-[14px] font-bold text-gray-900 dark:text-white mb-2 line-clamp-2" title={doc.name}>
            {doc.name || doc.id}
          </h3>
          
          <p className="text-[12px] text-gray-500 dark:text-gray-400 flex-1 line-clamp-3 mb-4">
            {doc.id}
          </p>
          
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              if (onSelectDoc) onSelectDoc(doc);
              if (onSelect) onSelect(doc.id);
            }}
            className="mt-auto pt-4 border-t border-gray-100 dark:border-slate-800 flex items-center justify-between text-indigo-600 dark:text-indigo-400 text-left"
          >
            <span className="text-[12px] font-medium">Xem các đoạn dữ liệu</span>
            <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </button>
        </div>
      ))}
    </div>
  );
}
