import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "LexAudit DE/EU — Föderales Rechts-Audit- & Demokratie-Portal",
  description:
    "Gemeinnützige Open-Source-Plattform für bitemporalen Rechtsgraph, Z3-Konfliktprüfung, verifizierte Zitationen und demokratische Durchsetzungshebel.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de">
      <body className="min-h-screen flex flex-col">
        <Navbar />
        <main id="main-content" className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
          {children}
        </main>
        <footer className="border-t border-editorial-border bg-white py-6 text-xs text-editorial-muted">
          <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 sm:px-6 md:flex-row md:items-center md:justify-between">
            <p>
              <strong>Hinweis nach Art. 50 KI-VO:</strong> KI-gestützte Normanalysen &amp; Textvorlagen
              durchlaufen zwingend den deterministischen CitationVerifier. Keine Einzelfall-Rechtsberatung (§ 2 RDG).
            </p>
            <p>
              Quellen: § 5 UrhG (NeuRIS, GII, RII, BGBl, Nds. GVBl) · ODbL v1.0 (OLDP) · CC0 (Abgeordnetenwatch) ·
              dl-de/by-2-0 (DIP) · MIT License
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
