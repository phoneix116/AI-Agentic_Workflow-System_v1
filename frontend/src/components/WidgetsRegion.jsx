import TasksWidget from './TasksWidget'
import CalendarWidget from './CalendarWidget'
import ActivityWidget from './ActivityWidget'
import EmailsWidget from './EmailsWidget'

/**
 * Widgets Region Component
 * Responsive grid layout for dashboard widgets
 * Mobile: vertical stack | Tablet: 2 columns | Desktop: 3 columns
 * Accessibility: semantic section structure, aria-labels for each widget
 */
export default function WidgetsRegion() {
  return (
    <section className="flex h-full flex-col gap-3" aria-label="Dashboard widgets">
      <header className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
        <h2 className="text-base font-semibold">Focus widgets</h2>
        <p className="text-xs text-text-secondary">
          Quick status cards for tasks, schedule, and momentum.
        </p>
      </header>

      <div className="grid gap-3 lg:grid-cols-1 2xl:grid-cols-2">
        <TasksWidget />
        <CalendarWidget />
        <EmailsWidget />
        <ActivityWidget />
      </div>
    </section>
  )
}
