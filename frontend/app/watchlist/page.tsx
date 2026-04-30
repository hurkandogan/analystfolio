'use client';
import { useEffect, useState } from 'react';
import { WatchlistAPI, WatchlistEntry } from '@/lib/api';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Eye, Plus, Trash2, Search, Play, Activity, Clock, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

export default function WatchlistPage() {
    const [items, setItems] = useState<WatchlistEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [newTicker, setNewTicker] = useState('');
    const [adding, setAdding] = useState(false);

    useEffect(() => {
        fetchWatchlist();
        const interval = setInterval(fetchWatchlist, 10000); // 10s auto-refresh
        return () => clearInterval(interval);
    }, []);

    const fetchWatchlist = async () => {
        try {
            const data = await WatchlistAPI.getAll();
            setItems(data);
        } catch (error) {
            console.error('Watchlist fetch failed', error);
            toast.error('Failed to load Premium Watchlist');
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newTicker.trim()) return;

        setAdding(true);
        try {
            await WatchlistAPI.add(newTicker);
            toast.success(`${newTicker.toUpperCase()} added to Premium Watchlist`);
            setNewTicker('');
            fetchWatchlist();
        } catch (error: any) {
            toast.error(`Failed to add: ${error.response?.data?.detail || 'Unknown error'}`);
        } finally {
            setAdding(false);
        }
    };

    const handleDelete = async (id: number, ticker: string) => {
        try {
            await WatchlistAPI.delete(id);
            toast.success(`${ticker} removed from watchlist`);
            fetchWatchlist();
        } catch (error) {
            toast.error('Failed to remove item');
        }
    };

    const getStateColor = (state: string) => {
        switch (state) {
            case 'Action': return 'bg-red-500 hover:bg-red-600 text-white border-red-500';
            case 'Alert': return 'bg-amber-500 hover:bg-amber-600 text-white border-amber-500';
            default: return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
        }
    };

    return (
        <div className='flex flex-col h-full p-6 space-y-6'>
            <div className='flex items-center justify-between'>
                <div>
                    <h1 className='text-3xl font-bold tracking-tight'>Premium Watchlist</h1>
                    <p className='text-muted-foreground'>
                        High-quality targets monitored for sudden technical setups and premium options.
                    </p>
                </div>
            </div>

            <div className='grid grid-cols-1 md:grid-cols-4 gap-6'>
                {/* ADD FORM */}
                <Card className='md:col-span-1 border-muted/40 shadow-sm bg-card/50 h-fit'>
                    <CardHeader>
                        <CardTitle className='text-lg flex items-center gap-2'>
                            <Search size={18} className='text-primary' />
                            Track Asset
                        </CardTitle>
                        <CardDescription>Manually pin an instrument to the radar.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleAdd} className='space-y-4'>
                            <div className='space-y-2'>
                                <Input
                                    placeholder='e.g., TSLA, SOFI, NVDA'
                                    value={newTicker}
                                    onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                                    disabled={adding}
                                />
                            </div>
                            <Button type='submit' className='w-full' disabled={adding || !newTicker.trim()}>
                                {adding ? <RefreshCw className='animate-spin mr-2 h-4 w-4' /> : <Plus className='mr-2 h-4 w-4' />}
                                Add to Radar
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {/* WATCHLIST TABLE */}
                <Card className='md:col-span-3 border-muted/40 shadow-sm bg-card/50'>
                    <CardHeader>
                        <CardTitle className='flex items-center gap-2'>
                            <Eye className='text-blue-500' size={20} />
                            Active Surveillance Radar
                        </CardTitle>
                        <CardDescription>Assets currently being monitored by the State Machine every 60 minutes.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className='flex justify-center p-8'>
                                <Activity className='animate-pulse text-muted-foreground' />
                            </div>
                        ) : items.length === 0 ? (
                            <div className='text-center p-8 text-muted-foreground border border-dashed rounded-lg'>
                                No assets in the premium watchlist right now.
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Ticker</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Source</TableHead>
                                        <TableHead>Score</TableHead>
                                        <TableHead>Added</TableHead>
                                        <TableHead>Last Action</TableHead>
                                        <TableHead className='text-right'>Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {items.map((item) => (
                                        <TableRow key={item.id}>
                                            <TableCell className='font-bold font-mono text-primary'>
                                                {item.ticker}
                                            </TableCell>
                                            <TableCell>
                                                <Badge className={getStateColor(item.current_state)}>
                                                    {item.current_state.toUpperCase()}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant='outline' className={item.source === 'Manual' ? 'border-purple-500/50 text-purple-400' : 'border-emerald-500/50 text-emerald-400'}>
                                                    {item.source}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <span className='font-mono'>
                                                    {item.fundamental_score ? `${item.fundamental_score.toFixed(0)}/100` : '---'}
                                                </span>
                                            </TableCell>
                                            <TableCell className='text-xs text-muted-foreground'>
                                                {new Date(item.added_at).toLocaleDateString()}
                                            </TableCell>
                                            <TableCell className='text-xs text-muted-foreground'>
                                                {item.last_signal_at ? (
                                                    <span className='flex items-center gap-1'>
                                                        <Clock size={12} /> {new Date(item.last_signal_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                                    </span>
                                                ) : 'Pending...'}
                                            </TableCell>
                                            <TableCell className='text-right'>
                                                {item.source === 'Manual' && (
                                                    <Button
                                                        variant='ghost'
                                                        size='icon'
                                                        className='h-8 w-8 text-red-500 hover:text-red-400 hover:bg-red-500/10'
                                                        onClick={() => handleDelete(item.id, item.ticker)}
                                                    >
                                                        <Trash2 size={16} />
                                                    </Button>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
