'use client';
import { useEffect, useState } from 'react';
import { BotState, SystemAPI, DashboardAPI, DashboardSummary } from '@/lib/api';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Activity,
  Play,
  Square,
  Cpu,
  RefreshCw,
  Zap,
  Wallet,
  TrendingUp,
  DollarSign,
} from 'lucide-react';

import { toast } from 'sonner';
import TerminalLogs from '@/components/terminal-logs';
import StatCard from '@/components/stat-card';

export default function Home() {
  const [bots, setBots] = useState<BotState[]>([]);
  const [loadingBots, setLoadingBots] = useState(false);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // 5 saniyede bir guncelle
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    fetchBots();
    fetchSummary();
  };

  const fetchBots = async () => {
    setLoadingBots(true);
    try {
      const data = await SystemAPI.getBots();
      setBots(data);
    } catch (error) {
      console.error('Botlar çekilemedi', error);
    } finally {
      setLoadingBots(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const data = await DashboardAPI.getSummary();
      setSummary(data);
    } catch (error) {
      console.error('Ozet veri cekilemedi', error);
    }
  };

  const toggleBot = async (name: string, currentStatus: string) => {
    try {
      if (currentStatus === 'RUNNING') {
        await SystemAPI.stopBot(name);
        toast.info(`${name} durdurma emri gönderildi.`);
      } else {
        await SystemAPI.startBot(name);
        toast.success(`${name} başlatılıyor...`);
      }
      setTimeout(fetchBots, 1000);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      toast.error(
        `Process is failed: ${error.response?.data?.detail || 'Hata'}`
      );
    }
  };

  return (
    <div className='flex flex-col h-full p-6 space-y-6'>
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold tracking-tight'>Command Center</h1>
          <p className='text-muted-foreground'>
            Real-time system monitoring and bot orchestration.
          </p>
        </div>
        <div className='flex gap-2'>
          <Badge
            variant='outline'
            className='px-3 py-1 border-green-900 text-green-500 bg-green-900/10'
          >
            API: Connected
          </Badge>
          <Badge
            variant='outline'
            className='px-3 py-1 border-blue-900 text-blue-500 bg-blue-900/10'
          >
            DB: Synced
          </Badge>
        </div>
      </div>

      {/* TOP STATS */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
        <StatCard
          title='Active Bots'
          value={`${bots.filter((b) => b.status === 'RUNNING').length} / ${bots.length
            }`}
          icon={<BotCardIcon />}
          diff={
            <span className='flex items-center gap-1 text-green-500'>
              <Activity size={12} /> System Online
            </span>
          }
        />
        <StatCard
          title='Total Portfolio'
          value={summary ? `€${summary.total_value.toLocaleString()}` : '---'}
          icon={<Wallet size={20} />}
          diff={summary?.connected ? 'IBKR Connected' : 'Offline'}
        />
        <StatCard
          title='Open Positions'
          value={summary ? summary.total_positions_count : 0}
          icon={<TrendingUp size={20} />}
          diff={
            summary && summary.positions.length > 0 ? (
              <div className='flex flex-col gap-0.5 mt-1'>
                {summary.positions.map((pos, idx) => (
                  <div
                    key={idx}
                    className='flex justify-between text-[10px] w-full'
                  >
                    <span className='font-bold'>{pos.symbol}</span>
                    <span
                      className={
                        pos.pnl >= 0 ? 'text-green-500' : 'text-red-500'
                      }
                    >
                      {pos.pnl > 0 ? '+' : ''}
                      {pos.pnl.toFixed(1)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              'No active positions'
            )
          }
        />
        <StatCard
          title='Available Cash'
          value={
            summary ? (
              <div className='flex flex-col text-sm font-normal mt-1 space-y-1'>
                {summary.available_cash.map((cash) => (
                  <div
                    key={cash.currency}
                    className='flex justify-between w-full gap-6 border-b border-white/5 pb-0.5 last:border-0'
                  >
                    <span className='text-muted-foreground font-mono'>
                      {cash.currency}
                    </span>
                    <span className='font-mono'>
                      {cash.value.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              '---'
            )
          }
          icon={<DollarSign size={20} />}
          diff=''
        />
      </div>

      {/* MAIN GRID */}
      <div className='grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0'>
        {/* LEFT COLUMN: ACTIVE BOTS */}
        <Card className='lg:col-span-2 flex flex-col border-muted/40 shadow-sm bg-card/50'>
          <CardHeader>
            <div className='flex items-center justify-between'>
              <div>
                <CardTitle>Bot Orchestration</CardTitle>
                <CardDescription>Manage autonomous agents.</CardDescription>
              </div>
              <Button
                size='sm'
                variant='outline'
                onClick={fetchBots}
                disabled={loadingBots}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${loadingBots ? 'animate-spin' : ''
                    }`}
                />
              </Button>
            </div>
          </CardHeader>
          <CardContent className='space-y-4'>
            {bots.length === 0 ? (
              <div className='text-center p-4 text-muted-foreground'>
                No bots available.
              </div>
            ) : (
              bots.map((bot) => (
                <BotRow
                  key={bot.id}
                  bot={bot}
                  onToggle={() => toggleBot(bot.name, bot.status)}
                />
              ))
            )}
          </CardContent>
        </Card>

        {/* RIGHT COLUMN: TERMINAL LOGS */}
        <TerminalLogs />
      </div>
    </div>
  );
}


function BotRow({ bot, onToggle }: { bot: BotState; onToggle: () => void }) {
  const isRunning = bot.status === 'RUNNING';
  const lastRun = bot.last_run_at
    ? new Date(bot.last_run_at).toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
    })
    : 'Never';

  return (
    <div className='flex items-center justify-between p-4 border rounded-lg bg-card/40 hover:bg-muted/10 transition-colors'>
      <div className='flex items-center gap-4'>
        <div
          className={`p-2 rounded-full ${isRunning
              ? 'bg-green-500/10 text-green-500 animate-pulse'
              : 'bg-muted text-muted-foreground'
            }`}
        >
          <Cpu size={24} />
        </div>
        <div>
          <h3 className='font-bold text-base'>{bot.name}</h3>
          <p className='text-xs text-muted-foreground'>Last: {lastRun}</p>
          {bot.is_auto_run && (
            <div className='flex items-center gap-1 mt-1 text-[10px] text-blue-400 font-mono bg-blue-900/20 px-1.5 py-0.5 rounded w-fit'>
              <Zap size={10} />
              AUTO: {bot.run_interval_mins}m
            </div>
          )}
          <p className='text-xs text-muted-foreground'>
            {`${bot.info_message}`}
          </p>
        </div>
      </div>
      <div className='flex items-center gap-4'>
        <Badge
          variant={isRunning ? 'default' : 'secondary'}
          className={isRunning ? 'bg-green-600 hover:bg-green-700' : ''}
        >
          {bot.status}
        </Badge>

        <Button
          size='icon'
          variant='ghost'
          onClick={onToggle}
          className={`h-8 w-8 ${isRunning
              ? 'text-red-500 hover:text-red-400 hover:bg-red-900/20'
              : 'text-green-500 hover:text-green-400 hover:bg-green-900/20'
            }`}
        >
          {isRunning ? (
            <Square size={16} fill='currentColor' />
          ) : (
            <Play size={16} fill='currentColor' />
          )}
        </Button>
      </div>
    </div>
  );
}

// Icons
const BotCardIcon = () => <Activity size={20} />;
