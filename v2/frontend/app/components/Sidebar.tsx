
import Link from 'next/link';
import { Icons } from '@/components/Icons';
import { NavLinks } from './NavLinks';

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
          <NavLinks />
        </div>
      </div>
    </div>
  );
}
