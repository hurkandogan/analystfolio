import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Toaster } from 'sonner';
import Sidebar from '@/components/sidebar';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });
const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: 'AnalystFolio Terminal',
  description: 'Advanced Financial Analysis System',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang='en' className='dark'>
      <body
        className={`${inter.variable} ${jetbrains.variable} font-sans bg-background text-foreground antialiased overflow-hidden`}
      >
        <div className='flex h-screen border-collapse'>
          <Sidebar />

          <main className='flex-1 overflow-y-auto'>{children}</main>
        </div>
        <Toaster theme='dark' position='bottom-right' />
      </body>
    </html>
  );
}
