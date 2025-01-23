import { Inter } from 'next/font/google';
import { SidebarProvider } from '@/components/ui/sidebar'; // Ensure this path is correct
import { DataManagerSidebar } from '@/components/sidebar'; // Ensure this path is correct
import { Providers } from './providers';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'Edit and Visualize App',
  description: 'An application for editing and visualizing data',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} bg-background text-foreground`}>
        <Providers>
          <SidebarProvider>
            <div className="flex min-h-screen">
              {/* Sidebar */}
              <DataManagerSidebar className="w-64" />

              {/* Main Content */}
              <main className="flex-1">{children}</main>
            </div>
          </SidebarProvider>
        </Providers>
      </body>
    </html>
  );
}
