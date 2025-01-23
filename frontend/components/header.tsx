'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { NavigationMenuDemo } from '@/components/navigation';
import { Settings } from 'lucide-react';
import SettingsModal from './settings-modal';
import { ThemeToggle } from './theme-toggle';

export default function Header() {
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    return (
        <header className="bg-background border-b text-foreground p-4">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <div className="flex h-16 items-center justify-between">
                    {/* Logo and Navigation */}
                    <div className="flex items-center">
                        <Link href="/" className="flex-shrink-0">
                            {/* Updated sr-only text (or remove entirely if you don't need it) */}
                            <span className="sr-only">Your Company</span>
                            <svg
                                className="h-8 w-auto"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1"
                            >
                            </svg>
                        </Link>
                        <nav className="ml-6 flex items-center space-x-4">
                            <NavigationMenuDemo />
                        </nav>
                    </div>

                    {/* Right-side Actions */}
                    <div className="flex items-center space-x-4">
                        <ThemeToggle />
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setIsSettingsOpen(true)}
                        >
                            <Settings className="h-5 w-5" />
                        </Button>
                    </div>
                </div>
            </div>
            <SettingsModal isOpen={isSettingsOpen} setIsOpen={setIsSettingsOpen} />
        </header>
    );
}
