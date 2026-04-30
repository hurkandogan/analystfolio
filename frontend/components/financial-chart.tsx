'use client';

import React, { useMemo } from 'react';
import {
    ComposedChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Area,
    Bar,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

import { Button } from '@/components/ui/button';

interface FinancialChartProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    candles: any[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    fundamentals: any[];
    symbol: string;
    activeRange: string;
    onRangeChange: (range: string) => void;
}

export default function FinancialChart({
    candles,
    fundamentals,
    symbol,
    activeRange,
    onRangeChange,
}: FinancialChartProps) {
    // 1. Data Merging Logic
    const chartData = useMemo(() => {
        if (!candles || candles.length === 0) return [];

        // Sort fundamentals by date
        const sortedFundamentals = [...fundamentals].sort(
            (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
        );

        return candles.map((candle) => {
            const candleDate = new Date(candle.timestamp);

            // Find the latest fundamental record ON or BEFORE this candle date
            const fund = sortedFundamentals
                .filter((f) => new Date(f.date) <= candleDate)
                .pop(); // Last one is the most recent

            return {
                date: candle.timestamp,
                price: candle.close,
                volume: candle.volume,
                ma_14: candle.ma_14,
                ma_50: candle.ma_50,
                ma_200: candle.ma_200,
                pe: fund?.pe_ratio || null,
                peg: fund?.peg_ratio || null,
                roe: fund?.roe ? (fund.roe * 100).toFixed(2) : null,
                target: fund?.target_price || null,
                fair_value: fund?.fair_value || null,
            };
        });
    }, [candles, fundamentals]);

    if (chartData.length === 0) {
        return (
            <div className='flex items-center justify-center h-64 border rounded-md text-muted-foreground'>
                No data available for chart.
            </div>
        );
    }

    return (
        <Card className="h-full flex flex-col">
            <CardHeader className="py-2 px-4 border-b">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">
                        {symbol} Financial Health Timeline
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        {['1M', '3M', '6M', '1Y', '3Y', '5Y'].map((r) => (
                            <Button
                                key={r}
                                variant={activeRange === r ? 'secondary' : 'ghost'}
                                size="sm"
                                className="h-6 px-2 text-xs"
                                onClick={() => onRangeChange(r)}
                            >
                                {r}
                            </Button>
                        ))}
                    </div>
                </div>
                <div className="flex justify-end gap-3 text-xs font-normal text-muted-foreground mt-1">
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-blue-500"></span> Price
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-cyan-500"></span> MA14
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-violet-500"></span> MA50
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-yellow-500"></span> MA200
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-orange-500"></span> Target
                    </span>
                </div>
            </CardHeader>
            <CardContent className="flex-1 min-h-[400px] p-2">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData}>
                        <defs>
                            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                        <XAxis
                            dataKey="date"
                            tickFormatter={(val) => new Date(val).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                            stroke="#666"
                            fontSize={12}
                            minTickGap={30}
                        />
                        <YAxis
                            yAxisId="right"
                            orientation="right"
                            domain={['auto', 'auto']}
                            stroke="#666"
                            fontSize={12}
                            tickFormatter={(val) => `$${val}`}
                        />
                        <Tooltip content={<CustomTooltip />} />

                        {/* Price Area */}
                        <Area
                            yAxisId="right"
                            type="monotone"
                            dataKey="price"
                            stroke="#3b82f6"
                            fillOpacity={1}
                            fill="url(#colorPrice)"
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 6 }}
                        />

                        {/* Moving Averages */}
                        <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="ma_14"
                            stroke="#06b6d4" // Cyan
                            strokeWidth={1}
                            dot={false}
                            connectNulls
                        />
                        <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="ma_50"
                            stroke="#8b5cf6" // Violet/Purple
                            strokeWidth={1}
                            dot={false}
                            connectNulls
                        />
                        <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="ma_200"
                            stroke="#eab308" // Yellow/Gold
                            strokeWidth={1}
                            dot={false}
                            connectNulls
                        />

                        {/* Target Price Line (if available) */}
                        <Line
                            yAxisId="right"
                            type="stepAfter"
                            dataKey="target"
                            stroke="#f97316"
                            strokeWidth={2}
                            dot={false}
                            connectNulls
                            strokeDasharray="5 5"
                        />
                    </ComposedChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        const dateStr = new Date(label).toLocaleString(undefined, {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        return (
            <div className="bg-background/95 backdrop-blur-md border border-border p-4 rounded-lg shadow-xl w-64 text-sm animate-in zoom-in-95 duration-200">
                <div className="font-bold text-base mb-2 border-b pb-2 text-foreground">
                    {dateStr}
                </div>

                {/* Price Section */}
                <div className="grid grid-cols-2 gap-y-1 mb-3">
                    <span className="text-muted-foreground">Price:</span>
                    <span className="font-mono font-bold text-blue-500 text-right">${data.price}</span>

                    <span className="text-muted-foreground">Target:</span>
                    <span className="font-mono text-orange-500 text-right">
                        {data.target ? `$${data.target}` : '-'}
                    </span>
                </div>

                {/* Fundamentals Section (The Popup content user wanted) */}
                <div className="bg-muted/30 p-2 rounded-md space-y-1">
                    <div className="text-xs font-semibold text-muted-foreground mb-1 uppercase tracking-wider">
                        Fundamentals
                    </div>
                    <div className="flex justify-between items-center">
                        <span>P/E Ratio</span>
                        <Badge variant="outline" className={getPColor(data.pe)}>
                            {data.pe || 'N/A'}
                        </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                        <span>PEG Ratio</span>
                        <Badge variant="outline" className={getPEGColor(data.peg)}>
                            {data.peg || 'N/A'}
                        </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                        <span>ROE</span>
                        <span className="font-mono">{data.roe ? `${data.roe}%` : '-'}</span>
                    </div>
                </div>
            </div>
        );
    }
    return null;
};

// Helper for colors
function getPColor(pe: number | null) {
    if (!pe) return 'border-muted text-muted-foreground';
    if (pe < 15) return 'border-green-500 text-green-500 bg-green-500/10';
    if (pe < 25) return 'border-yellow-500 text-yellow-500 bg-yellow-500/10';
    return 'border-red-500 text-red-500 bg-red-500/10';
}

function getPEGColor(peg: number | null) {
    if (!peg) return 'border-muted text-muted-foreground';
    if (peg < 1) return 'border-green-500 text-green-500 bg-green-500/10';
    if (peg < 2) return 'border-yellow-500 text-yellow-500 bg-yellow-500/10';
    return 'border-red-500 text-red-500 bg-red-500/10';
}
