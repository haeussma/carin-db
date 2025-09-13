import { Inter } from 'next/font/google';
import { Header } from "@/components/new-header"
import { MainContent } from "@/components/MainContent"
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
      <body className={`${inter.className} bg-background text-foreground`} suppressHydrationWarning>
        <Providers>
          <div className="flex flex-col h-screen w-full">
            <Header />
            {/* Main Content controlled by header state */}
            <main className="flex-1 overflow-hidden">
              <MainContent />
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
