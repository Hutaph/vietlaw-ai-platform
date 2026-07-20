import Link from 'next/link';
import { ArrowRight, KeyRound, ShieldCheck } from 'lucide-react';

export function InferenceSetupModal() {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-800 dark:bg-slate-950">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <KeyRound className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-950 dark:text-white">Inference setup required</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
              Configure a supported provider and model before asking legal questions. Your API keys are stored in this browser and sent only for inference requests.
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50 p-3 text-xs leading-5 text-emerald-800 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300">
          <ShieldCheck className="mr-2 inline h-4 w-4" />
          Tra cứu căn cứ pháp lý được quản lý an toàn bởi máy chủ.
        </div>

        <div className="mt-5 flex justify-end">
          <Link
            href="/admin#settings"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
          >
            Open configuration
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
