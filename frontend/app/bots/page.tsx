'use client';

import React, { useEffect, useState } from 'react';
import { Activity, Cpu, Server, AlertCircle, Play, Pause, Zap } from 'lucide-react';
import { toast } from 'sonner';
import { SystemAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { BotState } from '@/lib/api';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function BotsPage() {
  const [bots, setBots] = useState<BotState[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchBots = async () => {
    try {
      const data = await SystemAPI.getBots();
      setBots(data);
    } catch (error) {
      console.error('Failed to fetch bots:', error);
      toast.error('Failed to fetch bots.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBots();
    const interval = setInterval(fetchBots, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const handleToggleBot = async (bot: BotState) => {
    try {
      if (bot.status === 'RUNNING') {
        await SystemAPI.stopBot(bot.name);
        toast.success(`${bot.name} stopped.`);
      } else {
        await SystemAPI.startBot(bot.name);
        toast.success(`${bot.name} is started.`);
      }
      fetchBots();
    } catch (err) {
      toast.error('Process is failed.' + err);
    }
  };

  const handleRunBot = async (bot: BotState) => {
    try {
      await SystemAPI.runBot(bot.name);
      toast.success(`${bot.name} tetiklendi (Run Signal Sent).`);
    } catch (err) {
      toast.error('Tetikleme başarısız: ' + err);
    }
  };

  // Calculate stats
  const activeCount = bots.filter((b) => b.status === 'RUNNING').length;
  const totalCount = bots.length;
  const errorCount = bots.filter((b) => b.status === 'ERROR').length;

  return (
    <div className='min-h-screen bg-zinc-950 text-zinc-100 p-6 font-sans selection:bg-cyan-500/30'>
      <header className='mb-8 border-b border-zinc-800 pb-6'>
        <div className='flex flex-col md:flex-row justify-between items-start md:items-center gap-4'>
          <div>
            <h1 className='text-3xl font-bold tracking-tight text-transparent bg-clip-text bg-linear-to-r from-cyan-400 to-emerald-400 flex items-center gap-3'>
              <Activity className='w-8 h-8 text-cyan-500' />
              BOTS
            </h1>
            <p className='text-zinc-500 font-mono text-sm mt-1'>
              SYSTEM_STATUS: <span className='text-emerald-500'>ONLINE </span>/
              LATENCY: 24ms
            </p>
          </div>

          <div className='flex gap-4'>
            <HudCard
              label='ACTIVE BOTS'
              value={activeCount}
              color='text-emerald-400'
              icon={<Cpu className='w-4 h-4' />}
            />
            <HudCard
              label='TOTAL NODES'
              value={totalCount}
              color='text-blue-400'
              icon={<Server className='w-4 h-4' />}
            />
            <HudCard
              label='ERRORS'
              value={errorCount}
              color='text-red-400'
              icon={<AlertCircle className='w-4 h-4' />}
            />
          </div>
        </div>
      </header>

      <div className='grid grid-cols-1 xl:grid-cols-3'>
        <div className='xl:col-span-3 space-y-6'>
          <div className='flex items-center justify-between'>
            <h2 className='text-xl font-semibold flex items-center gap-2'>
              <Server className='w-5 h-5 text-zinc-400' />
              Active Nodes
            </h2>
            <Badge
              variant='outline'
              className='font-mono text-xs border-zinc-700 text-zinc-400'
            >
              AUTO-REFRESH: 10s
            </Badge>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
            {bots.map((bot) => (
              <BotCard
                key={bot.name}
                bot={bot}
                onToggle={() => handleToggleBot(bot)}
                onRun={() => handleRunBot(bot)}
              />
            ))}
            {bots.length === 0 && !loading && (
              <div className='col-span-full p-12 border border-dashed border-zinc-800 rounded-lg text-center text-zinc-500'>
                No bots detected in the system.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function HudCard({
  label,
  value,
  color,
  icon,
}: {
  label: string;
  value: number;
  color: string;
  icon: React.ReactNode;
}) {
  return (
    <div className='bg-zinc-900/50 border border-zinc-800 rounded-lg px-4 py-3 min-w-30 flex flex-col items-center justify-center backdrop-blur-sm'>
      <div className='text-[10px] font-mono text-zinc-500 uppercase tracking-wider flex items-center gap-1 mb-1'>
        {icon} {label}
      </div>
      <div className={`text-2xl font-bold font-mono ${color}`}>{value}</div>
    </div>
  );
}

function BotCard({ bot, onToggle, onRun }: { bot: BotState; onToggle: () => void; onRun: () => void }) {
  const isRunning = bot.status === 'RUNNING';

  return (
    <Card
      className={`bg-zinc-900/40 border-zinc-800 overflow-hidden transition-all hover:border-zinc-700 group relative ${isRunning ? 'shadow-[0_0_30px_-10px_rgba(16,185,129,0.1)]' : ''}`}
    >
      {isRunning && (
        <div className='absolute top-0 left-0 w-1 h-full bg-emerald-500/50' />
      )}

      <CardHeader className='pb-2'>
        <div className='flex justify-between items-start'>
          <div>
            <CardTitle className='text-lg font-bold text-zinc-100 flex items-center gap-2'>
              {bot.name}
            </CardTitle>
            <CardDescription className='font-mono text-[10px] text-zinc-500 mt-1'>
              CRON: {bot.run_interval_mins}
            </CardDescription>
          </div>
          <Badge
            variant='outline'
            className={`font-mono text-[10px] px-2 py-0.5 ${
              isRunning
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : 'bg-zinc-500/10 text-zinc-500 border-zinc-700'
            }`}
          >
            {isRunning ? 'ACTIVE' : 'INACTIVE'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className='pb-3 space-y-4'>
        <div className='grid grid-cols-2 gap-2 text-xs'>
          <div className='bg-black/20 p-2 rounded border border-zinc-800/50'>
            <div className='text-zinc-500 text-[10px] uppercase mb-0.5'>
              Last Run
            </div>
            <div className='font-mono text-zinc-300'>
              {bot.last_run_at
                ? new Date(bot.last_run_at).toLocaleString()
                : 'NEVER'}
            </div>
          </div>
          <div className='bg-black/20 p-2 rounded border border-zinc-800/50'>
            <div className='text-zinc-500 text-[10px] uppercase mb-0.5'>
              Next Run
            </div>
            <div className='font-mono text-zinc-300'>
              {bot.next_run_at
                ? new Date(bot.next_run_at).toLocaleString()
                : 'MANUAL'}
            </div>
          </div>
        </div>

        {bot.status === 'ERROR' && (
          <div className='bg-red-950/20 border border-red-900/30 p-2 rounded text-[10px] font-mono text-red-400 break-all'>
            ERR: {bot.info_message}
          </div>
        )}
      </CardContent>

      <CardFooter className='pt-0 gap-2'>
        <Button
          variant={isRunning ? 'destructive' : 'default'}
          size='sm'
          className={`flex-1 font-mono text-xs font-bold tracking-wider ${
            isRunning
              ? 'bg-red-900/20 hover:bg-red-900/40 text-red-400 border border-red-900/50'
              : 'bg-emerald-600 hover:bg-emerald-500 text-white'
          }`}
          onClick={onToggle}
        >
          {isRunning ? (
            <>
              <Pause className='w-3 h-3 mr-2' /> STOP PROCESS
            </>
          ) : (
            <>
              <Play className='w-3 h-3 mr-2' /> START PROCESS
            </>
          )}
        </Button>
        <Button
          variant='secondary'
          size='icon'
          onClick={onRun}
          title="Run Now"
          className='bg-zinc-800 border border-zinc-700 hover:bg-blue-500/20 hover:text-blue-400 hover:border-blue-500/50 transition-all'
        >
          <Zap className='h-4 w-4' />
        </Button>
      </CardFooter>
    </Card>
  );
}
