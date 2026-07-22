'use client';

import React, { useEffect, useState } from 'react';
import { Loader2, User, Bot, Clock } from 'lucide-react';

interface ChatLog {
  id: string;
  session_id: string;
  user_message: string;
  ai_response: string;
  timestamp: string;
}

interface Stats {
  total_interactions: number;
  by_date: Record<string, number>;
}

export default function AnalyticsTab() {
  const [logs, setLogs] = useState<ChatLog[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const [logsRes, statsRes] = await Promise.all([
          fetch('/api/admin/analytics/logs?limit=100'),
          fetch('/api/admin/analytics/stats')
        ]);
        
        if (logsRes.ok) {
          const logsData = await logsRes.json();
          setLogs(logsData.data);
        }
        
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setStats(statsData);
        }
      } catch (error) {
        console.error("Failed to fetch analytics", error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchAnalytics();
  }, []);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 bg-rose-50 dark:bg-rose-500/10 rounded-xl border border-rose-100 dark:border-rose-500/20">
          <p className="text-sm font-medium text-rose-600 dark:text-rose-400 mb-1">Tổng lượt hội thoại</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white">{stats?.total_interactions || 0}</p>
        </div>
        <div className="p-5 bg-rose-50/70 dark:bg-rose-500/10 rounded-xl border border-rose-100 dark:border-rose-500/20">
          <p className="text-sm font-medium text-rose-600 dark:text-rose-300 mb-1">Hôm nay</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white">
            {stats?.by_date?.[new Date().toISOString().split('T')[0]] || 0}
          </p>
        </div>
      </div>

      {/* Logs Table */}
      <div>
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Lịch sử trò chuyện gần đây</h3>
        
        {logs.length === 0 ? (
          <div className="text-center py-10 text-gray-500 bg-gray-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-gray-200 dark:border-slate-700">
            Chưa có lịch sử hội thoại nào
          </div>
        ) : (
          <div className="space-y-4">
            {logs.map((log) => (
              <div key={log.id} className="p-4 bg-gray-50 dark:bg-slate-800/50 rounded-xl border border-gray-100 dark:border-slate-700/50 hover:border-rose-200 dark:hover:border-rose-700/50 transition-colors">
                <div className="flex items-center gap-2 mb-3 text-xs text-gray-400">
                  <Clock className="w-3.5 h-3.5" />
                  {new Date(log.timestamp).toLocaleString('vi-VN')}
                </div>
                
                <div className="space-y-3">
                  <div className="flex gap-3">
                    <div className="w-6 h-6 rounded bg-gray-200 dark:bg-slate-700 flex items-center justify-center shrink-0">
                      <User className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />
                    </div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white leading-relaxed">
                      {log.user_message}
                    </p>
                  </div>
                  
                  <div className="flex gap-3">
                    <div className="w-6 h-6 rounded bg-rose-100 dark:bg-rose-900/30 flex items-center justify-center shrink-0">
                      <Bot className="w-3.5 h-3.5 text-rose-600 dark:text-rose-300" />
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed line-clamp-3">
                      {log.ai_response}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
