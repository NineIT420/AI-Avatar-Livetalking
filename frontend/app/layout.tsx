import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Nvidia A2F Demo',
  description: 'Real-time video streaming with WebRTC',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}

