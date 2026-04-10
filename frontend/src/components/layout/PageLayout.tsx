import { useState } from 'react';
import type { ReactNode } from 'react';
import type { Market } from '../../types/stock';
import { Navbar } from './Navbar';

interface PageLayoutProps {
  children: ReactNode;
}

export function PageLayout({ children }: PageLayoutProps) {
  const [market, setMarket] = useState<Market>('US');

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar market={market} onMarketChange={setMarket} />
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}
