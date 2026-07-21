import React, { useState, useRef } from 'react';
import { X, UploadCloud, FileText, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';

interface UploadModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export default function UploadModal({ onClose, onSuccess }: UploadModalProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [chunksCount, setChunksCount] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files);
    }
  };

  const handleFileSelection = (files: FileList | File[]) => {
    const validFiles = Array.from(files).filter(f => f.type === 'text/plain' || f.name.endsWith('.txt'));
    if (validFiles.length === 0) {
      setErrorMessage('Hiện tại chỉ hỗ trợ file văn bản (.txt)');
      setUploadStatus('error');
      return;
    }
    
    const newFiles = Array.from(validFiles);
    setSelectedFiles(prev => {
      const existingNames = new Set(prev.map(f => f.name));
      const filtered = newFiles.filter(f => !existingNames.has(f.name));
      return [...prev, ...filtered];
    });
    setUploadStatus('idle');
    setErrorMessage('');
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setUploadStatus('uploading');
    const formData = new FormData();
    selectedFiles.forEach(file => {
      formData.append('files', file);
    });

    try {
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setChunksCount(data.chunks_count || 0);
        setUploadStatus('success');
      } else {
        let err;
        try {
          err = await res.json();
        } catch {
          err = { detail: `Lỗi máy chủ (${res.status})` };
        }
        setErrorMessage(err.detail || 'Có lỗi xảy ra khi tải lên');
        setUploadStatus('error');
      }
    } catch (error) {
      setErrorMessage('Lỗi kết nối đến máy chủ');
      setUploadStatus('error');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="bg-white dark:bg-slate-900 w-full max-w-md rounded-3xl shadow-2xl overflow-hidden border border-gray-100 dark:border-slate-800 animate-in zoom-in-95 duration-200 flex flex-col"
      >
        <div className="flex items-center justify-between p-6 border-b border-gray-100 dark:border-slate-800">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Tải tài liệu lên</h2>
          <button 
            onClick={onClose}
            className="p-2 -mr-2 text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 flex-1">
          {uploadStatus === 'success' ? (
            <div className="flex flex-col items-center justify-center py-8 text-center space-y-4">
              <div className="w-16 h-16 bg-emerald-100 dark:bg-emerald-500/20 rounded-full flex items-center justify-center">
                <CheckCircle2 className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Tải lên thành công!</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Tài liệu đã được phân tách thành <span className="font-bold text-emerald-600 dark:text-emerald-400">{chunksCount}</span> đoạn dữ liệu và đưa vào kho truy xuất.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div 
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${
                  isDragging 
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-500/10' 
                    : selectedFiles.length > 0 
                      ? 'border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/10'
                      : 'border-gray-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-gray-50 dark:hover:bg-slate-800/50'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  className="hidden" 
                  accept=".txt,text/plain"
                  multiple
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFileSelection(e.target.files);
                    }
                  }}
                />
                
                {selectedFiles.length > 0 && uploadStatus !== 'error' ? (
                  <div className="flex flex-col items-center w-full">
                    <div className="flex items-center gap-2 mb-3">
                      <FileText className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                      <span className="font-medium text-gray-900 dark:text-white">Đã chọn {selectedFiles.length} tệp</span>
                    </div>
                    
                    <div className="max-h-32 overflow-y-auto w-full custom-scrollbar space-y-2 mb-4">
                      {selectedFiles.map((file, idx) => (
                        <div key={idx} className="flex justify-between items-center bg-white dark:bg-slate-800 px-3 py-2 rounded-lg border border-gray-100 dark:border-slate-700">
                          <span className="text-sm text-gray-700 dark:text-gray-300 truncate pr-4">{file.name}</span>
                          <button 
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedFiles(prev => prev.filter((_, i) => i !== idx));
                            }}
                            className="text-gray-400 hover:text-red-500"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                    
                    <div className="flex gap-4">
                      <button 
                        onClick={() => fileInputRef.current?.click()}
                        className="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
                      >
                        Thêm tệp
                      </button>
                      <button 
                        onClick={() => setSelectedFiles([])}
                        className="text-xs text-red-600 dark:text-red-400 hover:underline font-medium"
                      >
                        Xóa tất cả
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                    <div className="w-12 h-12 bg-gray-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-3">
                      <UploadCloud className="w-6 h-6 text-gray-500 dark:text-gray-400" />
                    </div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                      Kéo thả tệp vào đây hoặc <span className="text-blue-600 dark:text-blue-400">chọn tệp</span>
                    </span>
                    <span className="text-xs text-gray-500">
                      Chỉ hỗ trợ tệp văn bản (.txt)
                    </span>
                  </div>
                )}
              </div>

              {uploadStatus === 'error' && (
                <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-500/10 rounded-xl text-red-600 dark:text-red-400 text-sm">
                  <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                  <p>{errorMessage}</p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-900 flex justify-end gap-3">
          {uploadStatus === 'success' ? (
            <button
              onClick={onSuccess}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl transition-all shadow-sm"
            >
              Hoàn tất
            </button>
          ) : (
            <>
              <button
                onClick={onClose}
                disabled={uploadStatus === 'uploading'}
                className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-800 text-sm font-medium rounded-xl transition-all disabled:opacity-50"
              >
                Hủy
              </button>
              <button
                onClick={handleUpload}
                disabled={selectedFiles.length === 0 || uploadStatus === 'uploading'}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 dark:disabled:bg-blue-800 text-white text-sm font-medium rounded-xl transition-all shadow-sm flex items-center gap-2"
              >
                {uploadStatus === 'uploading' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Đang xử lý...
                  </>
                ) : (
                  'Tải lên và xử lý'
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
