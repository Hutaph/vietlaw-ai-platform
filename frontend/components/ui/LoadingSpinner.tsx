/**
 * Loading spinner component — hiển thị khi đang chờ LLM trả lời.
 * Tách từ ChatInterface.tsx để tái sử dụng.
 */
import React from 'react';
import { Scale } from 'lucide-react';

export function LoadingSpinner() {
  return (
    <div className="py-6 px-4">
      <div className="max-w-4xl mx-auto flex space-x-4 items-center">
        <div className="w-8 h-8 bg-gradient-to-br from-rose-500 to-rose-700 rounded-lg flex items-center justify-center shadow-md border border-rose-800">
          <Scale className="w-4 h-4 text-white" />
        </div>
        <div className="flex space-x-1.5 items-center px-4 py-3">
          <div className="w-2 h-2 bg-rose-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-rose-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-rose-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}
