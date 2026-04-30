'use client';

import React, { useEffect, useState } from 'react';
import { Terminal, Trash2 } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SystemAPI } from '@/lib/api';
import { LogType, LogEntry } from '@/lib/api';


export default function TerminalLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<LogType | 'ALL'>('ALL');

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const history = await SystemAPI.getLogs(100);
        setLogs(history);
      } catch (err) {
        console.error('Failed to fetch log history:', err);
      }
    };
    fetchHistory();

    let ws: WebSocket | null = null;
    let reconnectTimer: NodeJS.Timeout;
    let isMounted = true;

    const connect = () => {
      if (!isMounted) return;

      try {
        ws = SystemAPI.getLogSocket();

        ws.onopen = () => {
          console.log('System Logs: WS Connected');
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const newLog = JSON.parse(event.data);
            setLogs((prev) => {
              // Avoid duplicates if history was just fetched
              const exists = prev.some(l =>
                l.msg === newLog.msg &&
                l.time === newLog.time &&
                l.module === newLog.module
              );
              if (exists) return prev;
              return [newLog, ...prev].slice(0, 100);
            });
          } catch (err) {
            console.error('Failed to parse log:', err);
          }
        };

        ws.onclose = () => {
          if (isMounted) {
            console.log('System Logs: WS Closed. Reconnecting in 3s...');
            reconnectTimer = setTimeout(connect, 3000);
          }
        };

        ws.onerror = (err) => {
          console.error('System Logs: WS Error', err);
        };
      } catch (e) {
        console.error('System Logs: Connection creation failed', e);
        if (isMounted) reconnectTimer = setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      isMounted = false;
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  const filteredLogs =
    filter === 'ALL' ? logs : logs.filter((log) => log.type === filter);

  const handleClear = () => {
    setLogs([]);
  };

  return (
    <Card className='lg:col-span-1 flex flex-col bg-black border-zinc-800 shadow-2xl h-full overflow-hidden'>
      <CardHeader className='py-3 px-4 border-b border-zinc-800 bg-zinc-900/50 flex flex-row items-center justify-between space-y-0'>
        <div className='flex items-center gap-2 text-zinc-400'>
          <Terminal size={16} />
          <span className='font-mono text-sm font-bold'>SYSTEM_LOGS</span>
        </div>
        <div className='flex items-center gap-3'>
          <div className='flex gap-1.5 border-r border-zinc-800 pr-3'>
            {(['ALL', 'INFO', 'SUCCESS', 'ERROR'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all ${filter === f
                    ? 'bg-zinc-700 text-white shadow-sm'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
                  }`}
              >
                {f}
              </button>
            ))}
          </div>
          <button
            onClick={handleClear}
            className='text-zinc-500 hover:text-red-400 transition-colors'
            title='Clear Logs'
          >
            <Trash2 size={14} />
          </button>
        </div>
      </CardHeader>
      <CardContent className='p-0 flex-1 relative min-h-75'>
        <ScrollArea className='h-full w-full absolute inset-0 p-4 font-mono text-[11px]'>
          <div className='space-y-1.5'>
            {filteredLogs.length === 0 ? (
              <div className='text-zinc-600 italic'>
                {logs.length === 0
                  ? 'Waiting for logs...'
                  : `No ${filter} logs found.`}
              </div>
            ) : (
              <>
                {filteredLogs.map((log, idx) => (
                  <LogLine key={idx} log={log} />
                ))}
              </>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function LogLine({ log }: { log: LogEntry }) {
  let color = 'text-zinc-400';
  if (log.type === 'INFO') color = 'text-blue-400';
  if (log.type === 'SUCCESS') color = 'text-green-400';
  if (log.type === 'WARNING') color = 'text-yellow-400';
  if (log.type === 'ERROR') color = 'text-red-400';

  return (
    <div className='flex gap-3 hover:bg-zinc-900/50 p-0.5 rounded transition-colors'>
      <span className='text-zinc-600 shrink-0 tabular-nums'>
        {log.time || new Date().toLocaleTimeString()}
      </span>
      <span
        className={`font-bold shrink-0 w-24 truncate ${color}`}
        title={log.module}
      >
        {log.module}
      </span>
      <span className='text-zinc-300 wrap-break-word whitespace-pre-wrap flex-1'>
        {log.msg}
      </span>
    </div>
  );
}
