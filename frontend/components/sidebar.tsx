'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  BarChart3,
  Bot,
  Settings,
  LineChart,
  Database,
  Calendar,
  Bell,
  Eye,
} from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className='w-64 border-r bg-muted/10 hidden md:flex flex-col justify-between'>
      <div>
        <div className='h-14 flex items-center px-6 border-b font-mono font-bold tracking-wider text-primary'>
          ANALYST<span className='text-foreground'>FOLIO</span>_v1
        </div>
        <nav className='p-4 space-y-2'>
          <NavItem
            href='/'
            icon={<LayoutDashboard size={20} />}
            label='Command Center'
            active={pathname === '/'}
          />
          <NavItem
            href='/market'
            icon={<Database size={20} />}
            label='Market Data'
            active={pathname === '/market'}
          />
          <NavItem
            href='/analysis'
            icon={<BarChart3 size={20} />}
            label='Analysis'
            active={pathname === '/analysis'}
          />
          <NavItem
            href='/watchlist'
            icon={<Eye size={20} />}
            label='Premium Watchlist'
            active={pathname === '/watchlist'}
          />
          <div className='pt-4 pb-2'>
            <div className='text-xs font-semibold text-muted-foreground px-4 mb-2'>
              SYSTEM
            </div>
            <NavItem
              href='/bots'
              icon={<Bot size={20} />}
              label='Bot Manager'
              active={pathname === '/bots'}
            />
            <NavItem
              href='/settings'
              icon={<Settings size={20} />}
              label='Configuration'
              active={pathname === '/settings'}
            />
            <NavItem
              href='/calendar'
              icon={<Calendar size={20} />}
              label='Market Calendar'
              active={pathname === '/calendar'}
            />
            <NavItem
              href='/notifications'
              icon={<Bell size={20} />}
              label='Notifications'
              active={pathname === '/notifications'}
            />
          </div>
        </nav>
      </div>
      <div className='p-4 border-t text-xs text-muted-foreground font-mono'>
        <div>
          STATUS: <span className='text-green-500'>ONLINE</span>
        </div>
        <div>PING: 14ms</div>
      </div>
    </aside>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function NavItem({ href, icon, label, active = false }: any) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${active
        ? 'bg-primary/10 text-primary'
        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
        }`}
    >
      {icon}
      {label}
    </Link>
  );
}
