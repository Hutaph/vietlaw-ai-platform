import React, { useState } from 'react';
import { Plus, MessageSquare, Trash2, Scale, PanelLeftClose, Search, Moon, Sun, LibraryBig, Settings } from 'lucide-react';
import { useTheme } from 'next-themes';
import Link from 'next/link';
import { isToday, isYesterday, differenceInDays, isThisMonth } from 'date-fns';
import type { ChatSession } from '@/lib/types';

export type { ChatSession } from '@/lib/types';

interface SidebarProps {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onCloseSidebar: () => void;
  isSessionsListLoading?: boolean;
}

export function Sidebar({
  sessions,
  currentSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onCloseSidebar,
  isSessionsListLoading = false,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const { theme, setTheme, systemTheme } = useTheme();
  
  const currentTheme = theme === 'system' ? systemTheme : theme;

  const filteredSessions = sessions.filter(s => 
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const groupedSessions = filteredSessions.reduce((acc, session) => {
    const date = new Date(session.timestamp);
    let group = 'Cũ hơn';
    if (isToday(date)) group = 'Hôm nay';
    else if (isYesterday(date)) group = 'Hôm qua';
    else if (differenceInDays(new Date(), date) <= 7) group = '7 ngày trước';
    else if (isThisMonth(date)) group = 'Tháng này';

    if (!acc[group]) acc[group] = [];
    acc[group].push(session);
    return acc;
  }, {} as Record<string, ChatSession[]>);

  const groupOrder = ['Hôm nay', 'Hôm qua', '7 ngày trước', 'Tháng này', 'Cũ hơn'];

  return (
    <div className="h-screen w-full flex flex-col font-sans border-r border-gray-200 dark:border-gray-800 transition-colors bg-slate-50 dark:bg-[#171717]">

      {/* Header with glassmorphism */}
      <div className="h-14 flex items-center justify-between px-4 mt-1 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20"
            style={{ background: 'linear-gradient(135deg, #2563EB, #1D4ED8)' }}
          >
            <Scale className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="text-sm font-bold text-gray-800 dark:text-white tracking-tight">VietLaw AI</span>
            <span className="block text-[9px] font-medium text-blue-600 dark:text-blue-400 uppercase tracking-widest leading-none mt-0.5">Legal Assistant</span>
          </div>
        </div>
        <button
          onClick={onCloseSidebar}
          className="p-1.5 rounded-lg text-gray-500 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-white/8 transition-all"
          title="Đóng sidebar"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="px-3 py-2 flex-shrink-0 space-y-2">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 px-3 transition-all duration-200 border border-blue-500/25 bg-blue-50/60 dark:bg-[rgba(37,99,235,0.07)] text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-100 hover:border-blue-400 dark:hover:border-blue-400/50 hover:bg-blue-100 dark:hover:bg-blue-500/10 active:scale-98"
        >
          <Plus className="w-4 h-4" />
          <span className="text-[13px] font-semibold">Đoạn chat mới</span>
        </button>
        <Link
          href="/docs"
          className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 px-3 transition-all duration-200 border border-gray-200 dark:border-white/5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/5 active:scale-98"
        >
          <LibraryBig className="w-4 h-4" />
          <span className="text-[13px] font-semibold">Kho Tài Liệu</span>
        </Link>
        <Link
          href="/admin"
          className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 px-3 transition-all duration-200 border border-gray-200 dark:border-white/5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/5 active:scale-98 mt-2"
        >
          <Settings className="w-4 h-4" />
          <span className="text-[13px] font-semibold">Quản trị</span>
        </Link>
      </div>

      {/* Search Bar */}
      <div className="px-3 pb-3 flex-shrink-0">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            placeholder="Tìm kiếm đoạn chat..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl py-2 pl-9 pr-3 text-[12.5px] text-gray-700 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500/50 focus:bg-white dark:focus:bg-white/10 transition-all"
          />
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 mb-2 border-t border-gray-200 dark:border-white/5 flex-shrink-0" />

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-4 custom-scrollbar">
        {isSessionsListLoading ? (
          <div className="space-y-2 px-1 py-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="animate-pulse flex items-center px-3 py-2.5 rounded-xl bg-gray-100 dark:bg-white/5">
                <div className="w-4 h-4 bg-gray-200 dark:bg-gray-700 rounded mr-2.5 flex-shrink-0"></div>
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
              </div>
            ))}
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="px-3 py-6 text-[12px] text-gray-400 dark:text-gray-600 text-center italic leading-relaxed">
            {searchQuery ? 'Không tìm thấy đoạn chat nào.' : (
              <>Chưa có hội thoại nào.<br /><span className="not-italic text-gray-400 dark:text-gray-500">Bắt đầu một câu hỏi mới!</span></>
            )}
          </div>
        ) : (
          groupOrder.map(group => {
            const groupSessions = groupedSessions[group];
            if (!groupSessions || groupSessions.length === 0) return null;

            return (
              <div key={group} className="space-y-0.5">
                <div className="px-2 pt-1 pb-1.5 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-gray-600">
                  {group}
                </div>
                {groupSessions.map((session) => {
                  const isActive = currentSessionId === session.id;
                  return (
                    <div
                      key={session.id}
                      className={`group relative flex items-center px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 ${
                        isActive ? 'sidebar-item-active !border-l-0' : 'hover:bg-gray-100 dark:hover:bg-white/5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                      }`}
                      onClick={() => onSelectSession(session.id)}
                    >
                      <MessageSquare
                        className={`w-3.5 h-3.5 mr-2.5 flex-shrink-0 transition-colors ${
                          isActive ? 'text-blue-500 dark:text-blue-400' : 'text-gray-400 dark:text-gray-600 group-hover:text-gray-600 dark:group-hover:text-gray-400'
                        }`}
                      />
                      <div className="flex-1 truncate pr-6">
                        <span className={`text-[12.5px] font-medium block truncate ${isActive ? 'text-blue-700 dark:text-white' : ''}`}>
                          {session.title}
                        </span>
                      </div>
                      <button
                        onClick={(e) => { 
                          e.stopPropagation(); 
                          setSessionToDelete(session.id);
                        }}
                        className="absolute right-2 p-1.5 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-400/10 transition-all opacity-0 group-hover:opacity-100"
                        title="Xóa đoạn chat"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-200 dark:border-white/5 flex-shrink-0 flex items-center justify-between">
        <p className="text-[10px] text-gray-400 dark:text-gray-600 leading-relaxed">
          Phiên bản thử nghiệm · Dữ liệu luật VN
        </p>
        <button
          onClick={() => setTheme(currentTheme === 'dark' ? 'light' : 'dark')}
          className="p-1.5 rounded-lg text-gray-500 dark:text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-500/10 transition-all"
          title="Chuyển chế độ giao diện"
        >
          {currentTheme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      {sessionToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 dark:bg-black/60 backdrop-blur-sm animate-in fade-in duration-200" onClick={() => setSessionToDelete(null)}>
          <div 
            className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-2xl p-6 w-[90%] max-w-sm transform transition-all animate-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 mb-4 text-red-500">
              <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-500/10 flex items-center justify-center flex-shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">Xóa hội thoại?</h3>
            </div>
            
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 leading-relaxed">
              Bạn có chắc chắn muốn xóa đoạn hội thoại này không? Dữ liệu sẽ bị xóa hoàn toàn khỏi cơ sở dữ liệu và không thể khôi phục.
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setSessionToDelete(null)}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors"
              >
                Hủy bỏ
              </button>
              <button
                onClick={() => {
                  onDeleteSession(sessionToDelete);
                  setSessionToDelete(null);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 shadow-md shadow-red-500/20 rounded-xl transition-colors"
              >
                Xác nhận xóa
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
