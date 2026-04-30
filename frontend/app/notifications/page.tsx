'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { RotateCcw, Check, X, AlertCircle } from 'lucide-react';
import { formatDate } from '@/lib/utils'; // Assuming a utility exists, or I will use inline

interface NotificationDTO {
    id: number;
    channel: string;
    scope: string;
    content: string;
    status: string;
    created_at: string;
    meta: any;
}

export default function NotificationsPage() {
    const [notifications, setNotifications] = useState<NotificationDTO[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchNotifications();
    }, []);

    const fetchNotifications = async () => {
        try {
            const res = await fetch('http://localhost:8000/notifications/?limit=50');
            if (res.ok) {
                const data = await res.json();
                setNotifications(data);
            }
        } catch (error) {
            console.error('Failed to fetch notifications:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleResend = async (id: number) => {
        if (!confirm('Resend this notification?')) return;
        try {
            const res = await fetch(`http://localhost:8000/notifications/${id}/resend`, {
                method: 'POST',
            });
            if (res.ok) {
                alert('Notification resent successfully!');
                fetchNotifications(); // Refresh list to see new entry (optional, creating a new one?)
                // Actually, resend logic creates a NEW notification entry in the manager usually, 
                // OR just sends it. My helper `resend_notification` in router calls `manager.send` 
                // which WILL create a NEW DB entry. So refreshing is good.
            } else {
                alert('Failed to resend');
            }
        } catch (error) {
            console.error('Failed to resend:', error);
        }
    };

    const statusBadge = (status: string) => {
        switch (status) {
            case 'SENT':
                return <Badge className='bg-green-600'>Sent</Badge>;
            case 'FAILED':
                return <Badge variant='destructive'>Failed</Badge>;
            case 'SKIPPED':
                return <Badge variant='outline' className='text-yellow-600 border-yellow-600'>Skipped</Badge>;
            default:
                return <Badge variant='secondary'>{status}</Badge>;
        }
    };

    const channelIcon = (channel: string) => {
        // You can add icons here if you want
        return channel;
    };

    return (
        <div className='p-6 space-y-6'>
            <div className='flex justify-between items-center'>
                <h1 className='text-3xl font-bold tracking-tight'>Notification History</h1>
                <Button onClick={fetchNotifications} variant='outline' size='sm'>
                    <RotateCcw className='mr-2 h-4 w-4' /> Refresh
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Recent Messages</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className='rounded-md border'>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[50px]">ID</TableHead>
                                    <TableHead>Time</TableHead>
                                    <TableHead>Channel</TableHead>
                                    <TableHead>Scope</TableHead>
                                    <TableHead className="w-[40%]">Content</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead className='text-right'>Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {notifications.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={7} className='text-center h-24'>
                                            No notifications found.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    notifications.map((n) => (
                                        <TableRow key={n.id}>
                                            <TableCell>{n.id}</TableCell>
                                            <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                                                {new Date(n.created_at).toLocaleString()}
                                            </TableCell>
                                            <TableCell><Badge variant="outline">{n.channel}</Badge></TableCell>
                                            <TableCell><Badge variant="secondary" className="text-xs">{n.scope}</Badge></TableCell>
                                            <TableCell className="font-mono text-xs truncate max-w-[300px]" title={n.content}>
                                                {n.content}
                                            </TableCell>
                                            <TableCell>{statusBadge(n.status)}</TableCell>
                                            <TableCell className='text-right'>
                                                <Button
                                                    variant='ghost'
                                                    size='icon'
                                                    title="Resend"
                                                    onClick={() => handleResend(n.id)}
                                                >
                                                    <RotateCcw className='h-4 w-4 text-muted-foreground hover:text-primary' />
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
    );
}
