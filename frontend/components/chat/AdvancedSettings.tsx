import React, { useState, useRef, useCallback } from 'react';
import Link from 'next/link';
import { useClickOutside } from '@/hooks/use-click-outside';

export interface AdvancedConfig {
  temperature: number;
  maxTokens: number;
  topK: number;
}

interface AdvancedSettingsProps {
  config: AdvancedConfig;
  setConfig: (config: AdvancedConfig) => void;
}

export function AdvancedSettings({ config, setConfig }: AdvancedSettingsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useClickOutside(dropdownRef, useCallback(() => setIsOpen(false), []));

  return (
    <div className="relative flex items-center" ref={dropdownRef}>
      <button 
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        title="Cài đặt nâng cao"
        className="flex items-center justify-center rounded-xl border border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800 px-3 py-1.5 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 active:bg-gray-200 dark:active:bg-slate-600"
      >
        <span className="text-[12px] font-bold text-gray-700 dark:text-gray-300 flex items-center gap-1">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-rose-600">
            <line x1="4" y1="21" x2="4" y2="14"></line>
            <line x1="4" y1="10" x2="4" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12" y2="3"></line>
            <line x1="20" y1="21" x2="20" y2="16"></line>
            <line x1="20" y1="12" x2="20" y2="3"></line>
            <line x1="1" y1="14" x2="7" y2="14"></line>
            <line x1="9" y1="8" x2="15" y2="8"></line>
            <line x1="17" y1="16" x2="23" y2="16"></line>
          </svg>
          Tham số
        </span>
      </button>

      {isOpen && (
        <div className="absolute bottom-full mb-2 left-0 w-64 bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 shadow-xl shadow-gray-200/50 dark:shadow-none rounded-xl py-3 px-4 z-50 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="text-[11px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 border-b border-gray-50 dark:border-slate-800 pb-2 mb-3">
            Cấu hình mô hình và tìm kiếm
          </div>
          
          <div className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[12px] font-medium text-gray-700 dark:text-gray-300">Độ linh hoạt</label>
                <span className="text-[10px] text-gray-500 font-mono">{config.temperature.toFixed(2)}</span>
              </div>
              <input 
                type="range" 
                min="0" max="1" step="0.05"
                value={config.temperature}
                onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
                className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-rose-600"
              />
              <p className="text-[10px] text-gray-400">Điều chỉnh độ sáng tạo của câu trả lời.</p>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[12px] font-medium text-gray-700 dark:text-gray-300">Độ dài tối đa</label>
                <span className="text-[10px] text-gray-500 font-mono">{config.maxTokens}</span>
              </div>
              <input 
                type="range" 
                min="100" max="4000" step="100"
                value={config.maxTokens}
                onChange={(e) => setConfig({ ...config, maxTokens: parseInt(e.target.value) })}
                className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-rose-600"
              />
              <p className="text-[10px] text-gray-400">Giới hạn độ dài tối đa của câu trả lời.</p>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[12px] font-medium text-gray-700 dark:text-gray-300">Số căn cứ sử dụng</label>
                <span className="text-[10px] text-gray-500 font-mono">{config.topK}</span>
              </div>
              <input 
                type="range" 
                min="1" max="20" step="1"
                value={config.topK}
                onChange={(e) => setConfig({ ...config, topK: parseInt(e.target.value) })}
                className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-rose-600"
              />
              <p className="text-[10px] text-gray-400">Số điều khoản tối đa đưa vào câu trả lời.</p>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 dark:border-slate-800">
            <Link
              href="/admin#settings"
              onClick={() => setIsOpen(false)}
              className="text-[11px] font-semibold text-rose-600 dark:text-rose-300 hover:text-rose-700 dark:hover:text-rose-200"
            >
              Mở cấu hình đầy đủ →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
