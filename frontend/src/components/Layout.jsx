import { useState } from 'react'
import Sidebar from './Sidebar'
import ChatPanel from './ChatPanel'
import WidgetsRegion from './WidgetsRegion'

/**
 * Main layout component
 * Semantic structure: aside (sidebar) + main (content)
 * Responsive: stacks on mobile, side-by-side on desktop
 */
export default function Layout({ onLogout }) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-background-DEFAULT text-text-primary">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(0,212,255,0.16),_transparent_42%),radial-gradient(circle_at_bottom_right,_rgba(108,99,255,0.24),_transparent_42%)]"
      />

      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[80] focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-text-primary"
      >
        Skip to main content
      </a>

      {/* Sidebar - Navigation */}
      <Sidebar
        mobileOpen={mobileSidebarOpen}
        onToggleMobile={() => setMobileSidebarOpen(prev => !prev)}
        onCloseMobile={() => setMobileSidebarOpen(false)}
        onLogout={onLogout}
      />

      {mobileSidebarOpen && (
        <button
          type="button"
          onClick={() => setMobileSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-slate-950/45 backdrop-blur-[2px] md:hidden"
          aria-label="Close navigation overlay"
        />
      )}

      {/* Main Content Region */}
      <main 
        id="main-content"
        className="relative z-10 flex min-h-screen flex-1 flex-col overflow-hidden md:ml-64"
        role="main"
        aria-label="Dashboard"
      >
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-white/10 bg-background-DEFAULT/80 px-4 py-3 backdrop-blur-md md:hidden">
          <button
            type="button"
            onClick={() => setMobileSidebarOpen(true)}
            className="touch-target rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm font-semibold"
            aria-label="Open navigation"
          >
            Menu
          </button>
          <p className="text-sm font-semibold tracking-wide text-text-secondary">Daily Briefing</p>
        </header>

        <div className="grid h-full flex-1 grid-cols-1 gap-4 overflow-y-auto p-4 md:gap-5 md:p-6 xl:grid-cols-12">
          <section className="xl:col-span-7">
            <ChatPanel />
          </section>
          <section className="xl:col-span-5">
            <WidgetsRegion />
          </section>
        </div>
      </main>
    </div>
  )
}
