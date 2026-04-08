import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Providers } from "./providers";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "OmegaBot — Personal Trading Platform",
  description: "Your personal algorithmic trading workstation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>
          <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
            <Sidebar />
            <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <Topbar />
              <main
                style={{
                  flex: 1,
                  overflowY: "auto",
                  padding: "20px",
                  background: "var(--bg)",
                }}
              >
                {children}
              </main>
            </div>
          </div>
          <Toaster
            theme="dark"
            position="bottom-right"
            toastOptions={{
              style: {
                background: "var(--bg2)",
                border: "1px solid var(--border2)",
                color: "var(--text)",
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: "12px",
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
