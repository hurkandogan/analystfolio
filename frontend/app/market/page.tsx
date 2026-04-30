'use client';
import { useEffect, useState } from 'react';
import axios from 'axios';
import { MarketAPI, Instrument } from '@/lib/api';
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
import { toast } from 'sonner';
import {
  Search,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  Database,
  ChevronLeft,
  ChevronRight,
  X,
} from 'lucide-react';
import FinancialChart from '@/components/financial-chart';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function MarketPage() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSymbol, setNewSymbol] = useState('');
  const [newDataRole, setNewDataRole] = useState('TRADE');
  const [adding, setAdding] = useState(false);
  const [selectedInstrument, setSelectedInstrument] =
    useState<Instrument | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [details, setDetails] = useState<any>(null);
  const [selectedRange, setSelectedRange] = useState('1M');

  // Search & Pagination State
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 15;

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await MarketAPI.getAll();
      setInstruments(data);
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (error) {
      toast.error('Veriler yüklenemedi. Backend açık mı?');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedInstrument) {
      if (!details) {
        // İlk açılışta detayları sıfırla, ama range değişince sıfırlama (smooth transition)
        setDetails(null);
      }

      const fetchData = async () => {
        try {
          const symbol = selectedInstrument.symbol;

          // Range Logic
          let days = 30;
          let resolution = '1h';

          switch (selectedRange) {
            case '1M': days = 30; resolution = '1h'; break;
            case '3M': days = 90; resolution = '4h'; break; // 4h yoksa backend 1h döner, sorun yok
            case '6M': days = 180; resolution = '1d'; break;
            case '1Y': days = 365; resolution = '1d'; break;
            case '3Y': days = 365 * 3; resolution = '1w'; break;
            case '5Y': days = 365 * 5; resolution = '1w'; break;
            default: days = 30;
          }

          // Paralel olarak 3 endpoint'e istek atıyoruz
          const [analysesRes, candlesRes, fundamentalsRes] = await Promise.all([
            axios.get(`${API_BASE_URL}/market/instruments/${symbol}/analyses`),
            axios.get(`${API_BASE_URL}/market/instruments/${symbol}/candles`, {
              params: { days, resolution }
            }),
            axios.get(
              `${API_BASE_URL}/market/instruments/${symbol}/fundamentals`,
              { params: { days: 365 * 5 } } // Fundamental hep full gelsin
            ),
          ]);

          setDetails({
            signals: analysesRes.data,
            candles: candlesRes.data,
            fundamentals: fundamentalsRes.data,
          });
        } catch (error) {
          console.error('Detay verileri çekilemedi:', error);
          toast.error('Veriler yüklenirken hata oluştu.');
        }
      };
      fetchData();
    }
  }, [selectedInstrument, selectedRange]);

  // Filter & Pagination Logic
  const filteredInstruments = instruments.filter(
    (item) =>
      item.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.name &&
        item.name.toLowerCase().includes(searchQuery.toLowerCase())),
  );

  const totalPages = Math.ceil(filteredInstruments.length / ITEMS_PER_PAGE);
  const paginatedInstruments = filteredInstruments.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE,
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  // Ekleme Fonksiyonu
  const handleAdd = async () => {
    if (!newSymbol) return;
    setAdding(true);

    const toastId = toast.loading(
      `${newSymbol.toUpperCase()} aranıyor (IBKR)...`,
    );

    try {
      await MarketAPI.add(newSymbol, newDataRole);
      toast.success(`${newSymbol.toUpperCase()} başarıyla eklendi!`, {
        id: toastId,
      });
      setNewSymbol('');
      setNewDataRole('TRADE');
      loadData();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      const msg = error.response?.data?.detail || 'Bir hata oluştu';
      toast.error(`Hata: ${msg}`, { id: toastId });
    } finally {
      setAdding(false);
    }
  };

  // Silme Fonksiyonu
  const handleDelete = async (symbol: string) => {
    if (!confirm(`${symbol} silinecek. Emin misin?`)) return;

    try {
      await MarketAPI.delete(symbol);
      toast.success(`${symbol} silindi.`);
      setInstruments(instruments.filter((i) => i.symbol !== symbol));
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (error) {
      toast.error('Silinemedi.');
    }
  };

  return (
    <div className='p-6 space-y-6 max-w-6xl mx-auto'>
      {/* HEADER & ACTION BAR */}
      <div className='flex flex-col md:flex-row gap-4 items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold tracking-tight flex items-center gap-2'>
            <Database className='text-primary' /> Market Data
          </h1>
          <p className='text-muted-foreground'>
            İzlenen enstrümanlar ve kontrat detayları.
          </p>
        </div>

        {/* ADD NEW BOX */}
        <div className='flex gap-2 w-full md:w-auto'>
          <select
            className='h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
            value={newDataRole}
            onChange={(e) => setNewDataRole(e.target.value)}
          >
            <option value='TRADE'>TRADE</option>
            <option value='INDICATOR'>INDICATOR</option>
            <option value='WATCH'>WATCH</option>
          </select>
          <Input
            placeholder='Symbol (e.g. TSLA)'
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            className='w-full md:w-48 font-mono uppercase'
          />
          <Button onClick={handleAdd} disabled={adding || !newSymbol}>
            {adding ? (
              <Loader2 className='animate-spin mr-2' />
            ) : (
              <Plus className='mr-2 h-4 w-4' />
            )}
            {adding ? 'Checking...' : 'Add'}
          </Button>
        </div>
      </div>

      {/* DATA TABLE */}
      <Card className='bg-card/50'>
        <CardHeader className='py-4 border-b flex flex-row items-center justify-between gap-4'>
          <div className='flex items-center gap-4 flex-1'>
            <CardTitle className='text-sm font-medium text-muted-foreground whitespace-nowrap'>
              Total: {filteredInstruments.length}
            </CardTitle>
            <div className='relative max-w-sm w-full'>
              <Search className='absolute left-2 top-2.5 h-4 w-4 text-muted-foreground' />
              <Input
                placeholder='Search symbol...'
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className='pl-8 h-9'
              />
            </div>
          </div>
          <Button variant='ghost' size='sm' onClick={loadData}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </CardHeader>
        <CardContent className='p-0'>
          <Table>
            <TableHeader>
              <TableRow className='hover:bg-transparent'>
                <TableHead className='w-25'>Symbol</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Exchange</TableHead>
                <TableHead>Currency</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className='text-right'>Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedInstruments.length === 0 && !loading ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className='h-24 text-center text-muted-foreground'
                  >
                    {instruments.length === 0
                      ? 'Listeniz boş. Yukarıdan sembol ekleyin.'
                      : 'Sonuç bulunamadı.'}
                  </TableCell>
                </TableRow>
              ) : (
                paginatedInstruments.map((item) => (
                  <TableRow
                    key={item.id}
                    className='font-mono text-sm hover:bg-muted/50 cursor-pointer transition-colors'
                    onClick={() => setSelectedInstrument(item)}
                  >
                    <TableCell className='font-bold text-primary'>
                      {item.symbol}
                    </TableCell>
                    <TableCell className='text-muted-foreground font-sans'>
                      {item.name}
                    </TableCell>
                    <TableCell>{item.exchange}</TableCell>
                    <TableCell>{item.currency}</TableCell>
                    <TableCell>
                      <Badge
                        variant='outline'
                        className='border-blue-900 text-blue-400 bg-blue-900/10'
                      >
                        {item.data_role}
                      </Badge>
                    </TableCell>
                    <TableCell className='text-right'>
                      <div
                        className='flex items-center justify-end gap-2'
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Button
                          variant='ghost'
                          size='icon'
                          className='h-8 w-8 text-muted-foreground hover:text-foreground'
                          onClick={() => setSelectedInstrument(item)}
                        >
                          <Search className='h-4 w-4' />
                        </Button>
                        <Button
                          variant='ghost'
                          size='icon'
                          className='h-8 w-8 text-red-500 hover:text-red-400 hover:bg-red-900/20'
                          onClick={() => handleDelete(item.symbol)}
                        >
                          <Trash2 className='h-4 w-4' />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>

        {/* PAGINATION FOOTER */}
        {totalPages > 1 && (
          <div className='flex items-center justify-end space-x-2 p-4 border-t'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              <ChevronLeft className='h-4 w-4 mr-1' /> Previous
            </Button>
            <div className='text-sm text-muted-foreground min-w-25 text-center'>
              Page {currentPage} of {totalPages}
            </div>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
            >
              Next <ChevronRight className='h-4 w-4 ml-1' />
            </Button>
          </div>
        )}
      </Card>

      {/* FULL SCREEN POPUP (MODAL) */}
      {selectedInstrument && (
        <div className='fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200'>
          <div className='bg-background border rounded-lg shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200'>
            {/* Modal Header */}
            <div className='flex items-center justify-between p-6 border-b bg-muted/10'>
              <div>
                <h2 className='text-3xl font-bold flex items-center gap-3'>
                  {selectedInstrument.symbol}
                  <Badge variant='outline' className='text-base'>
                    {selectedInstrument.data_role}
                  </Badge>
                </h2>
                <p className='text-muted-foreground mt-1'>
                  {selectedInstrument.name}
                </p>
              </div>
              <Button
                variant='ghost'
                size='icon'
                onClick={() => setSelectedInstrument(null)}
              >
                <X className='h-6 w-6' />
              </Button>
            </div>

            {/* Modal Content */}
            <div className='flex-1 overflow-y-auto p-6'>
              <div className='space-y-6'>
                {/* 1. General Info (Full Width) */}
                <Card>
                  <CardHeader>
                    <CardTitle className='text-lg'>
                      General Information
                    </CardTitle>
                  </CardHeader>
                  <CardContent className='space-y-4'>
                    <div className='grid grid-cols-2 gap-2 text-sm'>
                      <span className='text-muted-foreground'>Exchange</span>
                      <span className='font-medium'>
                        {selectedInstrument.exchange}
                      </span>

                      <span className='text-muted-foreground'>Currency</span>
                      <span className='font-medium'>
                        {selectedInstrument.currency}
                      </span>

                      <span className='text-muted-foreground'>Sector</span>
                      <span className='font-medium'>
                        {(selectedInstrument as any).sector || '-'}
                      </span>

                      <span className='text-muted-foreground'>Industry</span>
                      <span className='font-medium'>
                        {(selectedInstrument as any).industry || '-'}
                      </span>

                      <span className='text-muted-foreground'>ID</span>
                      <span className='font-mono text-xs'>
                        {selectedInstrument.id}
                      </span>
                    </div>
                  </CardContent>
                </Card>

                {/* 2. Interactive Financial Chart (New) */}
                <div className="h-[500px]">
                  <FinancialChart
                    candles={details?.candles || []}
                    fundamentals={details?.fundamentals || []}
                    symbol={selectedInstrument.symbol}
                    activeRange={selectedRange}
                    onRangeChange={setSelectedRange}
                  />
                </div>

                {/* 3. Analysis History */}
                <Card>
                  <CardHeader>
                    <CardTitle className='text-lg'>Analysis History</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {details?.signals?.length > 0 ? (
                      <div className='space-y-2'>
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {details.signals.map((sig: any, i: number) => (
                          <div
                            key={i}
                            className='flex items-center justify-between p-3 border rounded-lg bg-muted/50'
                          >
                            <div className='flex items-center gap-3'>
                              <Badge
                                variant={
                                  sig.status === 'OPEN'
                                    ? 'default'
                                    : 'secondary'
                                }
                              >
                                {sig.status}
                              </Badge>
                              <span className='font-mono text-sm'>
                                {new Date(sig.created_at).toLocaleDateString()}
                              </span>
                            </div>
                            <div className='text-sm'>{sig.reason}</div>
                            <div className='font-bold'>{sig.score}/100</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className='text-muted-foreground text-sm italic p-4 text-center border border-dashed rounded-md'>
                        No analysis history found.
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Modal Footer */}
            <div className='p-4 border-t bg-muted/10 flex justify-end'>
              <Button
                variant='outline'
                onClick={() => setSelectedInstrument(null)}
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
