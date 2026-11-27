"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Scale, Network, FileWarning, Calculator, Megaphone, Compass } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Übersicht", icon: Scale },
  { href: "/graph", label: "Rechts-Graph", icon: Network },
  { href: "/findings", label: "Konfliktbefunde", icon: FileWarning },
  { href: "/simulator", label: "Z3-Rechenlabor", icon: Calculator },
  { href: "/aktionen", label: "Demokratie-Hebel", icon: Megaphone },
  { href: "/assistent", label: "Jura-Kompass", icon: Compass },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-editorial-border bg-white/95 backdrop-blur">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-50 focus:rounded focus:bg-editorial-accent focus:px-3 focus:py-2 focus:text-white"
      >
        Zum Hauptinhalt springen
      </a>
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5 text-editorial-accent">
          <Scale className="h-6 w-6 shrink-0" aria-hidden="true" />
          <div>
            <span className="block text-base font-bold tracking-tight">LexAudit DE/EU</span>
            <span className="block text-xs text-editorial-muted">
              Föderales Rechts-Audit · Pilot Niedersachsen
            </span>
          </div>
        </Link>

        <nav aria-label="Hauptnavigation" className="flex flex-wrap items-center gap-1.5">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-editorial-accent text-white"
                    : "text-editorial-ink hover:bg-slate-100"
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
