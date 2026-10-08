import { ClerkProvider } from '@clerk/nextjs';
import type { Metadata } from 'next';
import { Heart } from 'lucide-react';
import './globals.css';

export const metadata: Metadata = {
  title: 'Smart Learning Planner',
  description: 'AI-powered personalized academic scheduling and study assistance.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="flex flex-col min-h-screen bg-slate-50">
          {/* Main content area expands to push footer to the bottom */}
          <div className="flex-grow">
            {children}
          </div>
          
          {/* Global Footer */}
          <footer className="w-full py-6 mt-auto border-t border-slate-200 bg-white">
            <p className="flex items-center justify-center gap-1.5 text-sm font-medium text-slate-600">
              Made with <Heart className="w-4 h-4 text-red-500 fill-red-500" /> by Devanshu, Khushi, Himanshu & Heman
            </p>
          </footer>
        </body>
      </html>
    </ClerkProvider>
  );
}