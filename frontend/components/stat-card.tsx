import { Card, CardContent } from '@/components/ui/card';
import { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number | ReactNode;
  icon: ReactNode;
  diff?: string | ReactNode;
  className?: string;
}

export default function StatCard({
  title,
  value,
  icon,
  diff,
  className,
}: StatCardProps) {
  return (
    <Card className={`bg-muted/10 border-muted/20 ${className}`}>
      <CardContent className='p-6 flex items-center justify-between'>
        <div className='flex-1 min-w-0'>
          <p className='text-sm font-medium text-muted-foreground'>{title}</p>
          <div className='text-2xl font-bold mt-1'>{value}</div>
          {diff && (
            <div className='text-xs text-muted-foreground mt-1'>{diff}</div>
          )}
        </div>
        <div className='p-3 bg-primary/10 rounded-full text-primary shrink-0 ml-4'>
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}
