'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Scale, BookOpen, Copy, Check, ThumbsUp, ThumbsDown, RotateCcw, Undo2 } from 'lucide-react';
import type { Message, DocumentChunk } from '@/lib/types';
import { ChatProcessingTrace } from './ChatProcessingTrace';
import { dedupeLegalSources, LegalSourcesTrigger } from './LegalSources';
import { CHAT_CONTENT_WIDTH_CLASS, CHAT_ROW_WIDTH_CLASS } from './layout';

export type { Message, DocumentChunk } from '@/lib/types';

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
  onRefine?: (prompt: string) => void;
  onOpenContext?: (context: DocumentChunk[]) => void;
  onFeedbackSubmit?: (messageId: string, type: 1 | -1, reason?: string, comment?: string) => void;
  onRetry?: () => void;
  isSourcesPanelOpen?: boolean;
}

export function ChatMessage({ message, isStreaming = false, onRefine, onOpenContext, onFeedbackSubmit, onRetry, isSourcesPanelOpen = false }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(
    message.feedback === 1 ? 'up' : message.feedback === -1 ? 'down' : null
  );
  const [showNegativeForm, setShowNegativeForm] = useState(false);
  const [reason, setReason] = useState('Sai luật');
  const [comment, setComment] = useState('');
  const [selectedCitation, setSelectedCitation] = useState<DocumentChunk | null>(null);
  const [isProcessCollapsed, setIsProcessCollapsed] = useState(true);

  React.useEffect(() => {
    setFeedback(message.feedback === 1 ? 'up' : message.feedback === -1 ? 'down' : null);
  }, [message.feedback]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedbackClick = (type: 'up' | 'down') => {
    if (type === 'up') {
      setFeedback(feedback === 'up' ? null : 'up');
      setShowNegativeForm(false);
      if (feedback !== 'up' && onFeedbackSubmit) {
        onFeedbackSubmit(message.id, 1);
      }
    } else {
      if (feedback === 'down') {
        setFeedback(null);
        setShowNegativeForm(false);
      } else {
        setFeedback('down');
        setShowNegativeForm(true);
      }
    }
  };

  const submitNegativeFeedback = () => {
    if (onFeedbackSubmit) {
      onFeedbackSubmit(message.id, -1, reason, comment);
    }
    setShowNegativeForm(false);
  };

  // Parse <cite id="...">...</cite> into markdown link format
  const processedContent = message.content?.replace(
    /<cite\s+id=["']([^"']+)["']>([^<]+)<\/cite>/gi,
    '[$2](#cite-$1)'
  ) || '';

  return (
    <div id={`message-${message.id}`} className={`group py-5 px-4 message-animate ${showNegativeForm ? 'relative z-[150]' : ''}`}>
      <div className={`${CHAT_ROW_WIDTH_CLASS} flex ${isUser ? 'flex-row-reverse gap-2.5' : 'flex-row gap-4'}`}>

        {/* Avatar */}
        <div className="flex-shrink-0 mt-1">
          {isUser ? (
            <div className="w-8 h-8 rounded-full flex items-center justify-center border border-gray-200 dark:border-white/10 bg-gray-100 dark:bg-[#171717] shadow-sm">
              <User className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            </div>
          ) : (
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center shadow-md shadow-blue-500/20"
              style={{ background: 'linear-gradient(135deg, #2563EB, #1D4ED8)' }}
            >
              <Scale className="w-4 h-4 text-white" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className={`flex-1 min-w-0 flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          {/* Bubble */}
          <div
            className={`${
              isUser
                ? 'inline-block max-w-[92%] sm:max-w-[88%] px-5 py-3.5 rounded-2xl rounded-tr-sm shadow-sm text-white'
                : `${CHAT_CONTENT_WIDTH_CLASS} text-gray-800 dark:text-gray-200`
            }`}
            style={isUser ? { background: 'linear-gradient(135deg, #2563EB, #1D4ED8)' } : {}}
          >
            {message.content && (
              <div className={`prose dark:prose-invert max-w-none text-[15px] leading-7 prose-p:my-3 prose-ul:my-3 prose-ol:my-3 prose-li:my-1.5 prose-headings:mb-2 prose-headings:mt-5 prose-h2:text-xl prose-h3:text-lg prose-code:rounded prose-code:bg-slate-100 prose-code:px-1 prose-code:py-0.5 dark:prose-code:bg-white/10 ${isStreaming ? 'typing-cursor' : ''} ${
                isUser
                  ? 'prose-p:text-white prose-strong:text-white prose-a:text-white prose-headings:text-white prose-code:text-white prose-li:text-white'
                  : 'prose-p:text-gray-800 dark:prose-p:text-gray-200 prose-headings:text-gray-900 dark:prose-headings:text-gray-100 prose-strong:text-gray-900 dark:prose-strong:text-gray-100'
              }`}>
                <ReactMarkdown
                  components={{
                    a: ({ node, ...props }) => {
                      const href = props.href || '';
                      if (href.startsWith('#cite-')) {
                        const citeId = href.replace('#cite-', '');
                        return (
                          <a
                            {...props}
                            href="#"
                            onClick={(e) => {
                              e.preventDefault();
                              const citedContext = message.contextUsed?.find(c => c.metadata?.id === citeId);
                              if (citedContext) setSelectedCitation(citedContext);
                            }}
                            className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium underline decoration-blue-400/60 dark:decoration-blue-500/50 decoration-dashed underline-offset-4 cursor-pointer transition-colors"
                          >
                            {props.children}
                          </a>
                        );
                      }
                      return <a {...props} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer" />;
                    }
                  }}
                >
                  {processedContent}
                </ReactMarkdown>
              </div>
            )}

            {!isUser && message.processingStage && (
              <ChatProcessingTrace
                stage={message.processingStage}
                collapsed={isProcessCollapsed}
                onToggleCollapsed={() => setIsProcessCollapsed(current => !current)}
              />
            )}
          </div>

          {/* --- USER ONLY UI --- */}
          {isUser && (
            <div className="flex items-center justify-end gap-1.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-full max-w-[88%] pr-1">
              <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium mr-1 tracking-wide">
                {!isNaN(Number(message.id)) ? new Date(Number(message.id)).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : ''}
              </span>
              <button
                onClick={handleCopy}
                title={copied ? 'Đã sao chép!' : 'Sao chép'}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
              {onRefine && (
                <button
                  onClick={() => onRefine(message.content)}
                  title="Gửi lại"
                  className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                >
                  <Undo2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}

          {/* --- ASSISTANT ONLY UI --- */}
          {!isUser && (
            <>
              {/* Quick action row */}
              <div className="mt-2 flex flex-wrap items-center gap-1">
                <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium mr-2 tracking-wide">
                  {!isNaN(Number(message.id)) ? new Date(Number(message.id)).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : ''}
                </span>
                <button
                  onClick={handleCopy}
                  title={copied ? 'Đã sao chép!' : 'Sao chép câu trả lời'}
                  className="quick-action-btn flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-gray-500 dark:text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                >
                  {copied
                    ? <Check className="w-3.5 h-3.5 text-emerald-500" />
                    : <Copy className="w-3.5 h-3.5" />
                  }
                  <span>{copied ? 'Đã chép' : 'Sao chép'}</span>
                </button>

                {onRefine && (
                  <button
                    onClick={() => onRefine('Giải thích đơn giản hơn với ví dụ thực tế')}
                    title="Yêu cầu giải thích đơn giản hơn"
                    className="quick-action-btn flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-gray-500 dark:text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Giải thích lại</span>
                  </button>
                )}

                {onRetry && (message.processingStage === 'error' || message.processingStage === 'cancelled') && (
                  <button
                    onClick={onRetry}
                    title="Thử lại câu hỏi trước"
                    className="quick-action-btn flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-gray-500 dark:text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                  >
                    <Undo2 className="w-3.5 h-3.5" />
                    <span>Thử lại</span>
                  </button>
                )}

                <div className="w-px h-3.5 bg-gray-200 mx-1" />

                <button
                  onClick={() => handleFeedbackClick('up')}
                  title="Câu trả lời hữu ích"
                  className={`quick-action-btn p-1.5 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${feedback === 'up' ? 'text-emerald-500' : 'text-gray-400'}`}
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                </button>
                <div className="relative">
                  <button
                    onClick={() => handleFeedbackClick('down')}
                    title="Câu trả lời chưa tốt"
                    className={`quick-action-btn p-1.5 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${feedback === 'down' ? 'text-red-400' : 'text-gray-400'}`}
                  >
                    <ThumbsDown className="w-3.5 h-3.5" />
                  </button>

                  {/* Negative Feedback Form */}
                  {showNegativeForm && (
                    <div className="absolute top-full mt-2 left-0 w-64 bg-white dark:bg-[#171717] border border-gray-200 dark:border-white/10 rounded-xl shadow-2xl z-[150] p-3">
                      <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Vấn đề bạn gặp phải?</h4>
                      <select
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        className="w-full bg-gray-50 dark:bg-[#171717] border border-gray-200 dark:border-white/10 rounded-lg text-xs p-2 mb-2 text-gray-700 dark:text-gray-300 outline-none focus:border-blue-500"
                      >
                        <option value="Sai luật">Sai luật</option>
                        <option value="Trích dẫn sai">Trích dẫn sai</option>
                        <option value="Không liên quan">Không liên quan</option>
                        <option value="Khác">Khác</option>
                      </select>
                      <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="Góp ý thêm (không bắt buộc)..."
                        className="w-full bg-gray-50 dark:bg-[#171717] border border-gray-200 dark:border-white/10 rounded-lg text-xs p-2 mb-2 min-h-[60px] text-gray-700 dark:text-gray-300 outline-none focus:border-blue-500 resize-none custom-scrollbar"
                      />
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => setShowNegativeForm(false)}
                          className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                        >
                          Hủy
                        </button>
                        <button
                          onClick={submitNegativeFeedback}
                          className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium"
                        >
                          Gửi
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className={CHAT_CONTENT_WIDTH_CLASS}>
                <LegalSourcesTrigger
                  sources={message.contextUsed}
                  onOpenAll={onOpenContext}
                  controlsId="legal-sources-panel"
                  expanded={isSourcesPanelOpen && dedupeLegalSources(message.contextUsed || []).length > 0}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Citation Modal */}
      {selectedCitation && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-900/40 backdrop-blur-sm transition-opacity"
          onClick={() => setSelectedCitation(null)}
        >
          <div
            className="bg-white dark:bg-[#171717] rounded-xl shadow-2xl w-[90%] max-w-2xl overflow-hidden transform transition-all scale-100 border dark:border-white/10"
            onClick={e => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-gray-100 dark:border-white/10 flex justify-between items-center bg-gray-50/80 dark:bg-[#171717]/60">
              <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                Trích dẫn pháp lý
              </h3>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-1 rounded-full hover:bg-gray-200 dark:hover:bg-[#3a3a3a]"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>

            <div className="p-6 max-h-[60vh] overflow-y-auto custom-scrollbar">
              <div className="mb-4">
                <div className="inline-block px-3 py-1 bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-100 dark:border-blue-500/20 rounded-full text-xs font-semibold mb-3">
                  {selectedCitation.metadata?.source || 'Tài liệu pháp lý'}
                </div>
                {(selectedCitation.metadata?.dieu || selectedCitation.metadata?.khoan) && (
                  <h4 className="text-md font-semibold text-gray-800 dark:text-gray-100 mb-2">
                    {selectedCitation.metadata?.dieu ? `Điều ${selectedCitation.metadata.dieu}` : ''}
                    {selectedCitation.metadata?.dieu && selectedCitation.metadata?.khoan ? ' - ' : ''}
                    {selectedCitation.metadata?.khoan ? `Khoản ${selectedCitation.metadata.khoan}` : ''}
                  </h4>
                )}
              </div>

              <div className="text-gray-600 dark:text-gray-300 leading-relaxed text-sm whitespace-pre-wrap bg-gray-50/50 dark:bg-[#171717]/60 p-4 rounded-lg border border-gray-100 dark:border-white/10">
                {selectedCitation.content}
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-100 dark:border-white/10 bg-gray-50 dark:bg-[#171717]/60 flex justify-end">
              <button
                onClick={() => setSelectedCitation(null)}
                className="px-5 py-2 bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
