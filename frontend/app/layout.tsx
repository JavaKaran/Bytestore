import type { Metadata } from "next"
import { JetBrains_Mono } from "next/font/google"
import type { ReactNode } from "react"
import { Toaster } from "sonner"
import "./globals.css"

const jetbrainsMono = JetBrains_Mono({
    subsets: ["latin"],
    variable: "--font-jetbrains-mono",
})

export const metadata: Metadata = {
    title: "G-Drive",
    description: "Modern file storage and management",
}

export default function RootLayout({
    children,
}: {
    children: ReactNode;
}) {
    return (
        <html lang="en" className="dark">
            <body className={jetbrainsMono.variable}>
                {children}
                <Toaster theme="dark" />
            </body>
        </html>
    )
}

