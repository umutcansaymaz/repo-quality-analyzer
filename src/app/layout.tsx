import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono, Fraunces, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";
import { Toaster as SonnerToaster } from "@/components/ui/sonner";
import { ThemeProvider } from "@/components/analyzer/theme-provider";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

const fraunces = Fraunces({
  variable: "--font-display",
  subsets: ["latin"],
  display: "swap",
});

const ibmPlexSans = IBM_Plex_Sans({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Software Architect — Repository Analyzer",
  description:
    "Analyze repositories. Understand architecture. Discover root causes. Generate engineering roadmaps.",
  keywords: [
    "code analysis",
    "architecture review",
    "root cause detection",
    "engineering roadmap",
    "static analysis",
  ],
  openGraph: {
    title: "repo-quality-analyzer",
    description: "Privacy-first repository quality analysis — 417 repos audited, 0 false positives, 0 false negatives.",
    type: "website",
    images: [{ url: "/og-card.svg", width: 1200, height: 630, alt: "repo-quality-analyzer" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "repo-quality-analyzer",
    description: "Privacy-first repository quality analysis — 417 repos audited, 0 FP · 0 FN.",
    images: ["/og-card.svg"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${fraunces.variable} ${ibmPlexSans.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} font-sans antialiased`}
        suppressHydrationWarning
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          {children}
          <SonnerToaster richColors position="top-right" />
        </ThemeProvider>
      </body>
    </html>
  );
}
