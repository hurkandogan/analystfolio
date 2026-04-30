'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { Badge } from '@/components/ui/badge';
import { Trash2, Plus } from 'lucide-react';

interface CalendarEntry {
    id: number;
    exchange: string;
    date: string;
    is_open: boolean;
    note: string;
}

export default function CalendarPage() {
    const [entries, setEntries] = useState<CalendarEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [newDate, setNewDate] = useState('');
    const [newNote, setNewNote] = useState('');
    const [isOpen, setIsOpen] = useState(false); // Default to Closed (Holiday)

    useEffect(() => {
        fetchEntries();
    }, []);

    const fetchEntries = async () => {
        try {
            const res = await fetch('http://localhost:8000/calendar/');
            if (res.ok) {
                const data = await res.json();
                setEntries(data);
            }
        } catch (error) {
            console.error('Failed to fetch calendar:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async () => {
        if (!newDate) return;

        try {
            const res = await fetch('http://localhost:8000/calendar/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    exchange: 'NYSE', // Default for now
                    date: newDate,
                    is_open: isOpen,
                    note: newNote,
                }),
            });

            if (res.ok) {
                fetchEntries();
                setNewDate('');
                setNewNote('');
                setIsOpen(false);
            }
        } catch (error) {
            console.error('Failed to add entry:', error);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure?')) return;
        try {
            const res = await fetch(`http://localhost:8000/calendar/${id}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                fetchEntries();
            }
        } catch (error) {
            console.error('Failed to delete:', error);
        }
    };

    return (
        <div className='p-6 space-y-6'>
            <div className='flex justify-between items-center'>
                <h1 className='text-3xl font-bold tracking-tight'>Market Calendar</h1>
            </div>

            <div className='grid gap-6 md:grid-cols-2'>
                {/* Add New Entry Form */}
                <Card>
                    <CardHeader>
                        <CardTitle>Add Exception / Holiday</CardTitle>
                    </CardHeader>
                    <CardContent className='space-y-4'>
                        <div className='grid grid-cols-2 gap-4'>
                            <div className='space-y-2'>
                                <label className='text-sm font-medium'>Date</label>
                                <Input
                                    type='date'
                                    value={newDate}
                                    onChange={(e) => setNewDate(e.target.value)}
                                />
                            </div>
                            <div className='space-y-2'>
                                <label className='text-sm font-medium'>Status</label>
                                <div className='flex items-center space-x-2 h-10'>
                                    <Button
                                        variant={isOpen ? 'default' : 'outline'}
                                        size='sm'
                                        onClick={() => setIsOpen(true)}
                                        className={isOpen ? 'bg-green-600' : ''}
                                    >
                                        Open
                                    </Button>
                                    <Button
                                        variant={!isOpen ? 'destructive' : 'outline'}
                                        size='sm'
                                        onClick={() => setIsOpen(false)}
                                    >
                                        Closed
                                    </Button>
                                </div>
                            </div>
                        </div>
                        <div className='space-y-2'>
                            <label className='text-sm font-medium'>Note</label>
                            <Input
                                placeholder='e.g. Christmas Day'
                                value={newNote}
                                onChange={(e) => setNewNote(e.target.value)}
                            />
                        </div>
                        <Button onClick={handleAdd} className='w-full'>
                            <Plus className='mr-2 h-4 w-4' /> Add Entry
                        </Button>
                    </CardContent>
                </Card>

                {/* Existing Entries List */}
                <Card>
                    <CardHeader>
                        <CardTitle>Upcoming Exceptions</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className='rounded-md border'>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Date</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Note</TableHead>
                                        <TableHead className='text-right'>Action</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {entries.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={4} className='text-center h-24'>
                                                No exceptions found. Market assumes OPEN (Mon-Fri).
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        entries.map((entry) => (
                                            <TableRow key={entry.id}>
                                                <TableCell>{entry.date}</TableCell>
                                                <TableCell>
                                                    {entry.is_open ? (
                                                        <Badge className='bg-green-600'>Open</Badge>
                                                    ) : (
                                                        <Badge variant='destructive'>Closed</Badge>
                                                    )}
                                                </TableCell>
                                                <TableCell>{entry.note}</TableCell>
                                                <TableCell className='text-right'>
                                                    <Button
                                                        variant='ghost'
                                                        size='icon'
                                                        onClick={() => handleDelete(entry.id)}
                                                    >
                                                        <Trash2 className='h-4 w-4 text-muted-foreground hover:text-red-500' />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
