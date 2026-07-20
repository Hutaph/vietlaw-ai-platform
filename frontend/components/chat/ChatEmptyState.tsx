'use client';

import { Scale } from 'lucide-react';

interface ChatEmptyStateProps {
  onSelectSuggestion: (prompt: string) => void;
}

const SUGGESTIONS = [
  'Hợp đồng chuyển nhượng quyền sử dụng đất có cần công chứng không?',
  'Điều kiện để được cấp sổ đỏ (Giấy chứng nhận quyền sử dụng đất) là gì?',
  'Cần chuẩn bị giấy tờ gì khi đi công chứng hợp đồng mua bán nhà đất?',
];

export function ChatEmptyState({ onSelectSuggestion }: ChatEmptyStateProps) {
  return (
    <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-center px-4 py-10 text-center">
      <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-700 text-white shadow-lg shadow-blue-700/15">
        <Scale className="h-8 w-8" />
      </div>
      <h1 className="text-2xl font-bold tracking-tight text-slate-950 dark:text-white sm:text-3xl">
        Tra cứu pháp luật dễ dàng hơn
      </h1>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-500 dark:text-slate-400 sm:text-base">
        Đặt câu hỏi về quyền, nghĩa vụ, thủ tục hoặc quy định pháp luật để nhận câu trả lời kèm căn cứ tham khảo.
      </p>

      <div className="mt-8 grid gap-2.5 sm:grid-cols-3">
        {SUGGESTIONS.map(prompt => (
          <button
            key={prompt}
            type="button"
            onClick={() => onSelectSuggestion(prompt)}
            className="rounded-2xl border border-slate-200 bg-white p-4 text-left text-sm font-semibold leading-6 text-slate-700 shadow-sm transition hover:border-blue-200 hover:bg-blue-50/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-blue-500/10"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
