import "./globals.css";
import type { ReactNode } from "react";
import BrandLogo from "@/components/BrandLogo";

export const metadata = {
  title: "FileForge 2.0",
  description: "Unified file conversion, batching, queueing, thumbnails, and compression.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </div>
      </body>
    </html>
  );
}

function Header() {
  return (
    <header className="border-b border-fileforgeBorder bg-fileforgeBg/80 backdrop-blur sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <a href="/">
          <BrandLogo />
        </a>
        <nav className="flex flex-wrap gap-4 text-sm">
          <NavLink href="/">Home</NavLink>
          <NavLink href="/features">Features</NavLink>
          <NavLink href="/downloads">Downloads</NavLink>
          <NavLink href="/docs">Docs</NavLink>
          <NavLink href="/cli">CLI &amp; API</NavLink>
          <NavLink href="/conversion">Convert</NavLink>
          <NavLink href="/conversion-dashboard">Dashboard</NavLink>
          <NavLink href="/community">Community</NavLink>
        </nav>
      </div>
    </header>
  );
}

function NavLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} className="text-fileforgeText hover:text-fileforgeAccent transition-colors">
      {children}
    </a>
  );
}

function Footer() {
  return (
    <footer className="border-t border-fileforgeBorder bg-fileforgeBg/80">
      <div className="max-w-6xl mx-auto px-6 py-4 text-xs text-fileforgeMuted flex flex-col sm:flex-row gap-1 sm:gap-0 sm:justify-between">
        <span>FileForge 2.0 · Unified File Conversion &amp; Discovery</span>
        <span>GitHub: github.com/K1LLLAGT/File-Forge</span>
      </div>
    </footer>
  );
}
