import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Drawer } from 'vaul';
import { Menu, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import type { NavItem } from './AppLayout';

interface MobileNavProps {
  navItems: NavItem[];
}

export function MobileNav({ navItems }: MobileNavProps) {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <Drawer.Root direction="left" open={open} onOpenChange={setOpen}>
      <Drawer.Trigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </Button>
      </Drawer.Trigger>
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <Drawer.Content className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col gap-2 border-r bg-background p-4 outline-none">
          <Drawer.Title className="px-2 py-3 text-lg font-bold">Stock Analysis</Drawer.Title>
          <Drawer.Description className="truncate px-2 pb-2 text-sm text-muted-foreground">
            {user?.email}
          </Drawer.Description>
          <nav className="flex flex-col gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link key={item.path} to={item.path} onClick={() => setOpen(false)}>
                  <Button
                    variant={location.pathname.startsWith(item.path) ? 'secondary' : 'ghost'}
                    className="w-full justify-start gap-3"
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Button>
                </Link>
              );
            })}
          </nav>
          <Button variant="outline" onClick={logout} className="mt-auto gap-2">
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
