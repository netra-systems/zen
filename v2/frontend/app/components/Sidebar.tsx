import Link from 'next/link';
import { Icons } from '@/components/Icons';


export function Sidebar() {
  return (
    <div className="z-50 border-r bg-background md:block">
      <div className="flex h-full max-h-screen flex-col gap-2">
        <div className="flex h-14 items-center border-b px-4 lg:h-[60px] lg:px-6">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <Icons.logo className="h-6 w-6" />
            <span className="">Netra</span>
          </Link>
        </div>
        <div className="flex-1">
          <nav className="grid items-start px-2 text-sm font-medium lg:px-4">
            <Link
              href="/dashboard"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary"
            >
              <Icons.home className="h-4 w-4" />
              Dashboard
            </Link>
            <Link
              href="/generation"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary"
            >
              <Icons.syntheticData className="h-4 w-4" />
              Synthetic Data
            </Link>
            <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary cursor-not-allowed">
              <Icons.corpusAdmin className="h-4 w-4" />
              Corpus Admin
            </div>
            <Link
              href="/apex-optimizer-agent-v2"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary"
            >
              <Icons.apexOptimizer className="h-4 w-4" />
              Apex Optimizer
            </Link>
            <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary cursor-not-allowed">
              <Icons.ingestion className="h-4 w-4" />
              Ingestion
            </div>
            <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary cursor-not-allowed">
              <Icons.supplyCatalog className="h-4 w-4" />
              Supply Catalog
            </div>
            <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary cursor-not-allowed">
              <Icons.settings className="h-4 w-4" />
              Settings
            </div>
          </nav>
        </div>
      </div>
    </div>
  );
}