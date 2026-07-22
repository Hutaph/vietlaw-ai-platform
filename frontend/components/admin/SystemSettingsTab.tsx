'use client';

import React, { useEffect, useState } from 'react';
import {
  BrainCircuit,
  Check,
  Database,
  FileCheck2,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
} from 'lucide-react';
import { AI_MODELS, AI_PROVIDERS } from '@/lib/constants';
import { AISettings, DEFAULT_AI_SETTINGS, setRoleByModel } from '@/lib/ai-settings';
import { useAISettings } from '@/hooks/use-ai-settings';

const ROLE_LABELS = {
  answer: 'Trả lời chính',
  rewriter: 'Viết lại câu hỏi',
  summarizer: 'Tóm tắt bộ nhớ',
} as const;

const SERVER_AI_MODELS = AI_MODELS.filter(model => model.provider !== 'ollama');

const SYSTEM_FEATURES = [
  {
    icon: Search,
    title: 'Truy xuất tài liệu',
    status: 'Theo cấu hình máy chủ',
    description: 'FAISS hoặc Qdrant/hybrid được chọn khi máy chủ khởi động; bước tìm kiếm luôn cần để lấy căn cứ.',
  },
  {
    icon: FileCheck2,
    title: 'Trích dẫn pháp lý',
    status: 'Bắt buộc',
    description: 'Chỉ hiển thị các căn cứ được mô hình trích dẫn bằng ID điều khoản hợp lệ.',
  },
  {
    icon: Database,
    title: 'Kho dữ liệu',
    status: 'PostgreSQL + Qdrant',
    description: 'PostgreSQL lưu thông tin tài liệu; Qdrant lưu vector phục vụ truy xuất ngữ nghĩa.',
  },
  {
    icon: ShieldCheck,
    title: 'Thông tin nhạy cảm',
    status: 'Được bảo vệ',
    description: 'Khóa API, DSN và khóa Qdrant chỉ được cấu hình qua biến môi trường phía máy chủ.',
  },
];

export default function SystemSettingsTab() {
  const { settings, setSettings, resetSettings, isLoaded } = useAISettings();
  const [draft, setDraft] = useState<AISettings>(DEFAULT_AI_SETTINGS);
  const [section, setSection] = useState<'basic' | 'advanced'>('basic');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isLoaded) setDraft(settings);
  }, [isLoaded, settings]);

  const updateDraft = <K extends keyof AISettings,>(key: K, value: AISettings[K]) => {
    setDraft(current => ({ ...current, [key]: value }));
    setSaved(false);
  };

  const updateRoleModel = (role: 'answer' | 'rewriter' | 'summarizer', modelId: string) => {
    setDraft(current => setRoleByModel(current, role, modelId));
    setSaved(false);
  };

  const handleSave = () => {
    setSettings(draft);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    const confirmed = window.confirm(
      'Khôi phục cấu hình AI mặc định? Các lựa chọn mô hình và tham số sinh câu trả lời trên trình duyệt này sẽ được đặt lại.',
    );
    if (!confirmed) return;

    resetSettings();
    setDraft(DEFAULT_AI_SETTINGS);
    setSaved(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-rose-600 dark:text-rose-300 mb-2">
            <BrainCircuit className="w-5 h-5" />
            <span className="text-xs font-bold uppercase tracking-widest">Cấu hình AI</span>
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Cấu hình AI và tìm kiếm</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-2xl">
            Điều chỉnh cấu hình mặc định dùng cho các câu hỏi mới trên trình duyệt này.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-slate-700 rounded-xl hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Mặc định
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-xl transition-colors shadow-sm shadow-rose-600/15"
          >
            {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
            {saved ? 'Đã lưu' : 'Lưu cấu hình'}
          </button>
        </div>
      </div>

      <div className="inline-flex p-1 bg-gray-100 dark:bg-slate-800 rounded-xl">
        <button
          type="button"
          onClick={() => setSection('basic')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${section === 'basic' ? 'bg-white dark:bg-slate-900 text-rose-600 dark:text-rose-300 shadow-sm' : 'text-gray-500 dark:text-gray-400'}`}
        >
          Cơ bản
        </button>
        <button
          type="button"
          onClick={() => setSection('advanced')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${section === 'advanced' ? 'bg-white dark:bg-slate-900 text-rose-600 dark:text-rose-300 shadow-sm' : 'text-gray-500 dark:text-gray-400'}`}
        >
          Hệ thống nâng cao
        </button>
      </div>

      {section === 'basic' ? (
        <div className="space-y-6">
          <section className="rounded-2xl border border-gray-200 dark:border-slate-800 p-5">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white">Vai trò mô hình</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Chọn mô hình cho từng bước sinh câu trả lời. Khóa API và truy xuất pháp lý được xử lý ở máy chủ.
              </p>
            </div>
            <div className="space-y-3">
              {(['answer', 'rewriter', 'summarizer'] as const).map(role => (
                <div key={role} className="grid gap-2 md:grid-cols-[170px_1fr] md:items-center">
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">{ROLE_LABELS[role]}</span>
                  <select
                    value={draft.roles[role].model}
                    onChange={event => updateRoleModel(role, event.target.value)}
                    disabled={draft.useSameModelForHelperRoles && role !== 'answer'}
                    className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-gray-900 dark:text-white outline-none focus:border-rose-400 disabled:opacity-60"
                  >
                    {SERVER_AI_MODELS.map(model => (
                      <option key={`${role}-${model.id}`} value={model.id}>
                        {model.fullName} - {AI_PROVIDERS.find(provider => provider.id === model.provider)?.name}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
              <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={draft.useSameModelForHelperRoles}
                  onChange={event => {
                    const enabled = event.target.checked;
                    setDraft(current => {
                      if (!enabled) return { ...current, useSameModelForHelperRoles: false };
                      const answer = current.roles.answer;
                      return {
                        ...current,
                        useSameModelForHelperRoles: true,
                        roles: {
                          ...current.roles,
                          rewriter: { ...answer },
                          summarizer: { ...answer },
                        },
                      };
                    });
                    setSaved(false);
                  }}
                />
                Dùng cùng mô hình trả lời cho bước viết lại câu hỏi và tóm tắt bộ nhớ
              </label>
            </div>
          </section>

          <section className="rounded-2xl border border-gray-200 dark:border-slate-800 p-5">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white">Chọn nhanh mô hình trả lời</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Các lựa chọn này chỉ đổi mô hình cho vai trò trả lời chính; thông tin xác thực vẫn nằm trên máy chủ.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {SERVER_AI_MODELS.map(model => (
                <button
                  key={model.id}
                  type="button"
                  onClick={() => updateRoleModel('answer', model.id)}
                  className={`flex items-center justify-between gap-3 p-4 rounded-xl border text-left transition-all ${draft.roles.answer.model === model.id ? 'border-rose-400 bg-rose-50/60 dark:bg-rose-500/10 ring-1 ring-rose-400/80' : 'border-gray-200 dark:border-slate-700 hover:border-rose-200 dark:hover:border-rose-900/70'}`}
                >
                  <div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">{model.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{model.fullName}</p>
                  </div>
                  {draft.roles.answer.model === model.id && <Check className="w-4 h-4 text-rose-600" />}
                </button>
              ))}
            </div>
          </section>

          <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <RangeSetting
              label="Độ linh hoạt"
              value={draft.temperature}
              displayValue={draft.temperature.toFixed(2)}
              min={0}
              max={1}
              step={0.05}
              description="Độ sáng tạo của câu trả lời. Pháp luật nên dùng 0.1–0.3."
              onChange={value => updateDraft('temperature', value)}
            />
            <RangeSetting
              label="Độ dài tối đa"
              value={draft.maxTokens}
              displayValue={String(draft.maxTokens)}
              min={100}
              max={4000}
              step={100}
              description="Giới hạn số token tối đa, không hoàn toàn tương đương số từ."
              onChange={value => updateDraft('maxTokens', value)}
            />
            <RangeSetting
              label="Số đoạn ứng viên"
              value={draft.candidateK}
              displayValue={String(draft.candidateK)}
              min={10}
              max={100}
              step={5}
              description="Số đoạn dữ liệu được lấy trước khi xếp hạng lại."
              onChange={value => updateDraft('candidateK', value)}
            />
            <RangeSetting
              label="Số căn cứ gửi cho mô hình"
              value={draft.topK}
              displayValue={String(draft.topK)}
              min={1}
              max={20}
              step={1}
              description="Số điều khoản sau truy xuất và xếp hạng lại được gửi cho mô hình."
              onChange={value => updateDraft('topK', value)}
            />
            <RangeSetting
              label="Ngưỡng dùng lại câu trả lời"
              value={draft.cacheThreshold}
              displayValue={draft.cacheThreshold.toFixed(2)}
              min={0.8}
              max={0.99}
              step={0.01}
              description="Độ tương đồng tối thiểu để dùng lại câu trả lời trong bộ nhớ đệm."
              onChange={value => updateDraft('cacheThreshold', value)}
            />
            <RangeSetting
              label="Số truy vấn con tối đa"
              value={draft.maxSubqueries}
              displayValue={String(draft.maxSubqueries)}
              min={1}
              max={5}
              step={1}
              description="Giới hạn số truy vấn sau bước viết lại để kiểm soát số lần tìm kiếm và nhúng."
              onChange={value => updateDraft('maxSubqueries', value)}
            />
            <RangeSetting
              label="Số tin nhắn lịch sử"
              value={draft.historyMessages}
              displayValue={String(draft.historyMessages)}
              min={0}
              max={10}
              step={1}
              description="Số tin nhắn gần nhất được đưa vào ngữ cảnh và bước viết lại câu hỏi."
              onChange={value => updateDraft('historyMessages', value)}
            />
            <RangeSetting
              label="Ngân sách ngữ cảnh"
              value={draft.contextTokenBudget}
              displayValue={String(draft.contextTokenBudget)}
              min={1000}
              max={16000}
              step={500}
              description="Ngân sách token ước lượng cho toàn bộ căn cứ đưa vào LLM."
              onChange={value => updateDraft('contextTokenBudget', value)}
            />
            <RangeSetting
              label="Thời gian chờ mô hình (giây)"
              value={draft.llmTimeout}
              displayValue={String(draft.llmTimeout)}
              min={30}
              max={300}
              step={30}
              description="Thời gian tối đa chờ API hoặc Ollama sinh câu trả lời."
              onChange={value => updateDraft('llmTimeout', value)}
            />
          </section>

          <div className="flex items-start gap-3 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-100 dark:border-rose-500/20 p-4">
            <RefreshCw className="w-4 h-4 text-rose-600 dark:text-rose-300 mt-0.5 shrink-0" />
            <p className="text-xs leading-5 text-rose-700 dark:text-rose-200">
              Sau khi lưu, popup “Tham số” và bộ chọn mô hình ở màn hình chat sẽ tự đồng bộ. Cấu hình chỉ áp dụng cho trình duyệt hiện tại.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <section className="rounded-2xl border border-gray-200 dark:border-slate-800 p-5">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white">Bật/tắt từng bước xử lý</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Mỗi lựa chọn được gửi theo từng câu hỏi. Bước bị tắt sẽ không gọi mô hình hoặc dịch vụ tương ứng.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <ToggleSetting
                label="Viết lại câu hỏi"
                description="Viết lại và tách câu hỏi trước khi tìm kiếm; có thể thêm một lần gọi mô hình ngôn ngữ."
                enabled={draft.enableQueryRewriter}
                onChange={enabled => updateDraft('enableQueryRewriter', enabled)}
              />
              <ToggleSetting
                label="Xếp hạng lại căn cứ"
                description="Chấm điểm lại tài liệu bằng mô hình xếp hạng; tắt sẽ giữ thứ tự tìm kiếm ban đầu."
                enabled={draft.enableReranker}
                onChange={enabled => updateDraft('enableReranker', enabled)}
              />
              <ToggleSetting
                label="Bộ nhớ câu hỏi tương tự"
                description="Tìm câu hỏi tương tự trước khi truy xuất; tắt sẽ bỏ lượt nhúng để kiểm tra câu trả lời đã có."
                enabled={draft.enableSemanticCache}
                onChange={enabled => updateDraft('enableSemanticCache', enabled)}
              />
              <ToggleSetting
                label="Bộ nhớ hội thoại"
                description="Đọc và cập nhật ghi nhớ của phiên trò chuyện; cập nhật có thể gọi thêm một mô hình chạy nền."
                enabled={draft.enableMemory}
                onChange={enabled => updateDraft('enableMemory', enabled)}
              />
              <ToggleSetting
                label="Hiển thị từng phần"
                description="Hiển thị từng phần ngay khi mô hình sinh câu trả lời; tắt sẽ chờ phản hồi hoàn chỉnh."
                enabled={draft.streaming}
                onChange={enabled => updateDraft('streaming', enabled)}
              />
              <ToggleSetting
                label="Dùng lịch sử khi viết lại câu hỏi"
                description="Cho phép bước viết lại câu hỏi đọc lịch sử gần đây; độc lập với lịch sử gửi cho mô hình trả lời."
                enabled={draft.useHistoryForRewriter}
                onChange={enabled => updateDraft('useHistoryForRewriter', enabled)}
              />
            </div>
          </section>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SYSTEM_FEATURES.map(feature => {
              const Icon = feature.icon;
              return (
                <div key={feature.title} className="rounded-2xl border border-gray-200 dark:border-slate-800 p-5 bg-white dark:bg-slate-900">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-300 flex items-center justify-center">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-[10px] font-bold uppercase tracking-wide">
                      {feature.status}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white">{feature.title}</h3>
                  <p className="text-xs leading-5 text-gray-500 dark:text-gray-400 mt-1.5">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

interface ToggleSettingProps {
  label: string;
  description: string;
  enabled: boolean;
  onChange: (enabled: boolean) => void;
}

function ToggleSetting({ label, description, enabled, onChange }: ToggleSettingProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={() => onChange(!enabled)}
      className={`flex items-start justify-between gap-4 rounded-xl border p-4 text-left transition-all ${enabled ? 'border-rose-300 bg-rose-50/50 dark:border-rose-700 dark:bg-rose-500/10' : 'border-gray-200 dark:border-slate-700'}`}
    >
      <div>
        <p className="text-sm font-semibold text-gray-900 dark:text-white">{label}</p>
        <p className="text-xs leading-5 text-gray-500 dark:text-gray-400 mt-1">{description}</p>
      </div>
      <span className={`relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition-colors ${enabled ? 'bg-rose-600' : 'bg-gray-300 dark:bg-slate-600'}`}>
        <span className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${enabled ? 'translate-x-6' : 'translate-x-1'}`} />
      </span>
    </button>
  );
}
interface RangeSettingProps {
  label: string;
  value: number;
  displayValue: string;
  min: number;
  max: number;
  step: number;
  description: string;
  onChange: (value: number) => void;
}

function RangeSetting({ label, value, displayValue, min, max, step, description, onChange }: RangeSettingProps) {
  return (
    <div className="rounded-2xl border border-gray-200 dark:border-slate-800 p-5 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <label className="text-sm font-bold text-gray-900 dark:text-white">{label}</label>
        <span className="font-mono text-xs font-semibold text-rose-600 dark:text-rose-300 bg-rose-50 dark:bg-rose-500/10 px-2 py-1 rounded-lg">{displayValue}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={event => onChange(Number(event.target.value))}
        className="w-full h-2 bg-gray-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-rose-600"
      />
      <p className="text-xs leading-5 text-gray-500 dark:text-gray-400">{description}</p>
    </div>
  );
}
