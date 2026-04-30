'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import {
  Search,
  RefreshCw,
  BarChart3,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function AnalysisPage() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/market/analyses`, {
        params: { page, search, limit: 15 },
      });
      setItems(res.data.items);
      setTotalPages(res.data.pages);
    } catch (error) {
      toast.error('Analiz verileri yüklenemedi.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      loadData();
    }, 300); // Debounce search
    return () => clearTimeout(timer);
  }, [page, search]);

  const handleSearch = (val: string) => {
    setSearch(val);
    setPage(1); // Reset page on search
  };

  return (
    <div className='p-6 space-y-6 max-w-7xl mx-auto'>
      <div className='flex flex-col md:flex-row gap-4 items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold tracking-tight flex items-center gap-2'>
            <BarChart3 className='text-primary' /> Fundamental Analysis
          </h1>
          <p className='text-muted-foreground'>
            Latest trade signals and analysis results.
          </p>
        </div>
        <div className='flex items-center gap-2 w-full md:w-auto'>
          <div className='relative w-full md:w-64'>
            <Search className='absolute left-2 top-2.5 h-4 w-4 text-muted-foreground' />
            <Input
              placeholder='Search symbol...'
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className='pl-8'
            />
          </div>
          <Button
            variant='outline'
            size='icon'
            onClick={loadData}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <Card className='bg-card/50'>
        <CardContent className='p-0'>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Bot</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Score</TableHead>
                <TableHead className='w-[40%]'>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 && !loading ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className='h-24 text-center text-muted-foreground'
                  >
                    No data found!
                  </TableCell>
                </TableRow>
              ) : (
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                items.map((item: any) => (
                  <TableRow key={item.id} className='font-mono text-sm'>
                    <TableCell className='text-muted-foreground text-xs'>
                      {new Date(item.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className='font-bold text-primary'>
                      {item.symbol}
                    </TableCell>
                    <TableCell>{item.bot_name}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          item.status === 'OPEN' ? 'default' : 'secondary'
                        }
                        className={
                          item.status === 'NEW'
                            ? 'bg-green-600 hover:bg-green-700'
                            : ''
                        }
                      >
                        {item.status}
                      </Badge>
                    </TableCell>
                    <TableCell
                      className={`font-bold ${
                        item.score === null || item.score === undefined
                          ? ''
                          : item.score >= 80
                            ? 'text-green-500'
                            : item.score < 50
                              ? 'text-red-500'
                              : 'text-yellow-500'
                      }`}
                    >
                      {item.score !== null && item.score !== undefined
                        ? item.score.toFixed(0)
                        : '-'}
                    </TableCell>
                    <TableCell className='text-xs text-muted-foreground whitespace-pre-wrap'>
                      {item.reason}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className='flex items-center justify-end space-x-2 p-4 border-t'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className='h-4 w-4 mr-1' /> Previous
            </Button>
            <div className='text-sm text-muted-foreground min-w-25 text-center'>
              Page {page} of {totalPages}
            </div>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              Next <ChevronRight className='h-4 w-4 ml-1' />
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
