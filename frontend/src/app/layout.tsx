import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Examinator",
  description: "Clinical decision support platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children;
}
