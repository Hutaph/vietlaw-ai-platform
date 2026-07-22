import React, { useState, useRef, useCallback } from 'react';
import { Cpu, ChevronDown, Check } from 'lucide-react';
import { useClickOutside } from '@/hooks/use-click-outside';
import { AI_MODELS, AI_PROVIDERS } from '@/lib/constants';

interface ModelSelectorProps {
  model: string;
  setModel: (model: string) => void;
}

export function ProviderSelector({ model, setModel }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedModel = AI_MODELS.find(m => m.id === model) || AI_MODELS[0];
  const selectedProvider = AI_PROVIDERS.find(provider => provider.id === selectedModel.provider);

  // Dùng hook tái sử dụng thay vì duplicate useEffect
  useClickOutside(dropdownRef, useCallback(() => setIsOpen(false), []));

  return (
    <div className="relative flex items-center" ref={dropdownRef}>
      <button 
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center rounded-xl border border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800 px-3 py-1.5 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 active:bg-gray-200 dark:active:bg-slate-600"
      >
        <Cpu className="w-3.5 h-3.5 text-rose-600 mr-2" />
        <div className="flex items-center gap-1">
          <span className="text-[12px] font-bold text-gray-700 dark:text-gray-300">
            {selectedProvider?.name ?? selectedModel.provider}: {selectedModel.name}
          </span>
          <ChevronDown className={`w-3 h-3 text-gray-400 dark:text-gray-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {/* Menu thả xuống */}
      {isOpen && (
        <div className="absolute bottom-full mb-2 left-0 md:left-auto md:right-0 w-48 bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 shadow-xl shadow-gray-200/50 dark:shadow-none rounded-xl py-1 z-50 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 border-b border-gray-50 dark:border-slate-800 mb-1">
            Chọn mô hình AI
          </div>
          {AI_MODELS.map((m) => (
            <button
              key={m.id}
              onClick={() => {
                setModel(m.id);
                setIsOpen(false);
              }}
              className={`w-full text-left px-3 py-2.5 text-[12px] font-medium flex items-center justify-between transition-colors ${
                model === m.id 
                  ? 'text-rose-700 dark:text-rose-300 bg-rose-50/50 dark:bg-rose-500/10'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800'
              }`}
            >
              <span>
                <span className="block">{m.fullName}</span>
                <span className="block text-[10px] text-gray-400">
                  {AI_PROVIDERS.find(provider => provider.id === m.provider)?.name ?? m.provider}
                </span>
              </span>
              {model === m.id && <Check className="w-3.5 h-3.5 text-rose-600" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
