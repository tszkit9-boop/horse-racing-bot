import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import {
  Activity,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  ChevronRight,
  CirclePause,
  Clock3,
  MoreHorizontal,
  Play,
  RotateCcw,
  Server,
  ShieldCheck,
  TerminalSquare,
  Upload,
  Users,
  Zap,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export const Route = createFileRoute('/app/')({
  head: () => ({
    meta: [
      { title: 'Overview · BotDeck' },
      { name: 'description', content: 'Operate your team’s Telegram bots from one calm control plane.' },
    ],
  }),
  component: DashboardHome,
})

type BotStatus = 'Running' | 'Paused' | 'Deploying'
type BotRecord = { name: string; handle: string; status: BotStatus; uptime: string; cpu: string; memory: string; color: string }

const seedBots: BotRecord[] = [
  { name: 'Support Concierge', handle: '@northstar_support', status: 'Running', uptime: '14d 06h', cpu: '2.4%', memory: '128 MB', color: 'bg-[#2B9F9A]' },
  { name: 'Daily Digest', handle: '@northstar_digest', status: 'Running', uptime: '8d 19h', cpu: '0.8%', memory: '86 MB', color: 'bg-[#6B7CC4]' },
  { name: 'Onboarding Guide', handle: '@northstar_start', status: 'Paused', uptime: '—', cpu: '0%', memory: '42 MB', color: 'bg-[#D17A45]' },
]

function StatusPill({ status }: { status: BotStatus }) {
  const styles = {
    Running: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    Paused: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
    Deploying: 'bg-sky-500/10 text-sky-700 dark:text-sky-300',
  }
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${styles[status]}`}><span className="size-1.5 rounded-full bg-current" />{status}</span>
}

function MetricCard({ icon: Icon, label, value, note, accent }: { icon: typeof Bot; label: string; value: string; note: string; accent: string }) {
  return (
    <Card className="border-border/70 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md">
      <CardContent className="flex items-start justify-between p-5">
        <div><p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p><p className="mt-1 text-xs text-muted-foreground">{note}</p></div>
        <div className={`rounded-xl p-2.5 ${accent}`}><Icon className="size-5" /></div>
      </CardContent>
    </Card>
  )
}

function DashboardHome() {
  const [bots, setBots] = useState(seedBots)
  const [notice, setNotice] = useState('')

  const notify = (message: string) => { setNotice(message); window.setTimeout(() => setNotice(''), 2600) }
  const toggleBot = (name: string) => {
    setBots(current => current.map(bot => bot.name === name ? { ...bot, status: bot.status === 'Running' ? 'Paused' : 'Running' } : bot))
    notify(`${name} status updated`)
  }

  return (
    <div className="min-h-dvh bg-background">
      {notice && <div className="fixed right-5 top-5 z-50 flex items-center gap-2 rounded-xl bg-foreground px-4 py-3 text-sm text-background shadow-lg animate-fade-in"><CheckCircle2 className="size-4 text-primary" />{notice}</div>}
      <header className="flex h-16 items-center justify-between border-b border-border/70 bg-background/90 px-5 backdrop-blur md:px-8">
        <div className="flex items-center gap-3"><div className="rounded-lg bg-primary/10 p-2 text-primary"><TerminalSquare className="size-4" /></div><div><p className="text-sm font-semibold">Operations center</p><p className="text-xs text-muted-foreground">Thursday, August 20, 2026</p></div></div>
        <div className="flex items-center gap-2"><Button variant="outline" size="sm" onClick={() => notify('Invite link copied')}><Users className="size-4" /> <span className="hidden sm:inline">Invite teammate</span></Button><Button size="sm" onClick={() => notify('Upload flow opened')}><Upload className="size-4" /> Deploy bot</Button></div>
      </header>

      <main className="mx-auto max-w-[1440px] space-y-8 px-5 py-8 md:px-8 lg:px-10">
        <section className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end"><div><p className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary"><span className="size-2 rounded-full bg-primary shadow-[0_0_0_5px_color-mix(in_oklch,var(--primary)_15%,transparent)]" />All systems operational</p><h1 className="font-serif text-4xl font-medium tracking-tight md:text-5xl">Good afternoon, Alex.</h1><p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">Your bots are healthy and your team is in sync. Here’s what’s happening across your workspace.</p></div><div className="flex items-center gap-2 rounded-full border border-border/70 bg-card px-3 py-2 text-xs text-muted-foreground"><ShieldCheck className="size-4 text-primary" /> Isolated runtime environment <ChevronRight className="size-3" /></div></section>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><MetricCard icon={Bot} label="Active bots" value="2 / 3" note="1 paused by your team" accent="bg-primary/10 text-primary" /><MetricCard icon={Activity} label="Messages today" value="18,492" note="+12.8% from yesterday" accent="bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" /><MetricCard icon={Zap} label="Avg. response" value="420ms" note="Across active bots" accent="bg-amber-500/10 text-amber-700 dark:text-amber-300" /><MetricCard icon={Server} label="Workspace health" value="99.98%" note="Last 30 days" accent="bg-sky-500/10 text-sky-700 dark:text-sky-300" /></section>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <Card className="overflow-hidden border-border/70 shadow-sm"><CardHeader className="flex flex-row items-center justify-between border-b border-border/60 px-5 py-4"><div><CardTitle className="text-base">Your bots</CardTitle><p className="mt-1 text-xs text-muted-foreground">Live process health and deployment status</p></div><Button variant="ghost" size="sm" onClick={() => notify('Bot directory opened')}>View all <ArrowUpRight className="size-3.5" /></Button></CardHeader><CardContent className="p-0"><div className="divide-y divide-border/60">{bots.map(bot => <div key={bot.name} className="group flex flex-col gap-4 px-5 py-4 transition-colors hover:bg-muted/40 sm:flex-row sm:items-center sm:justify-between"><div className="flex min-w-0 items-center gap-3"><div className={`flex size-10 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-background ${bot.color}`}>{bot.name.slice(0, 1)}</div><div className="min-w-0"><p className="truncate text-sm font-semibold">{bot.name}</p><p className="truncate text-xs text-muted-foreground">{bot.handle}</p></div></div><div className="flex items-center gap-5 sm:gap-8"><div className="hidden text-right sm:block"><p className="text-xs font-medium">{bot.uptime}</p><p className="text-[11px] text-muted-foreground">uptime</p></div><div className="hidden text-right sm:block"><p className="text-xs font-medium">{bot.cpu}</p><p className="text-[11px] text-muted-foreground">CPU</p></div><StatusPill status={bot.status} /><button onClick={() => toggleBot(bot.name)} className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground" aria-label={`Toggle ${bot.name}`}>{bot.status === 'Running' ? <CirclePause className="size-4" /> : <Play className="size-4" />}</button><button onClick={() => notify(`${bot.name} menu opened`)} className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground" aria-label={`More options for ${bot.name}`}><MoreHorizontal className="size-4" /></button></div></div>)}</div></CardContent></Card>

          <div className="space-y-6"><Card className="border-border/70 bg-foreground text-background shadow-md"><CardContent className="p-5"><div className="mb-8 flex items-center justify-between"><div className="rounded-xl bg-background/10 p-2.5 text-primary"><RotateCcw className="size-5" /></div><span className="rounded-full bg-primary/20 px-2.5 py-1 text-[11px] font-semibold text-primary">AUTOMATION ON</span></div><p className="font-serif text-2xl">Restarts, handled.</p><p className="mt-2 text-sm leading-6 text-background/60">BotDeck watches every process and restarts unhealthy bots before your team notices.</p><div className="mt-6 flex items-center gap-2 text-xs text-background/70"><CheckCircle2 className="size-4 text-primary" /> 7 recoveries this month</div></CardContent></Card>
            <Card className="border-border/70 shadow-sm"><CardHeader className="flex flex-row items-center justify-between px-5 py-4"><CardTitle className="text-base">Recent activity</CardTitle><Clock3 className="size-4 text-muted-foreground" /></CardHeader><CardContent className="space-y-4 px-5 pb-5">{[['Support Concierge', 'Restarted automatically', '8 min ago'], ['Daily Digest', 'New deployment completed', '42 min ago'], ['Alex Morgan', 'Added Onboarding Guide', '2h ago']].map(([title, detail, time]) => <div key={title + detail} className="flex gap-3"><div className="mt-1 size-2 shrink-0 rounded-full bg-primary" /><div className="min-w-0"><p className="text-xs font-semibold">{title}</p><p className="truncate text-xs text-muted-foreground">{detail}</p><p className="mt-1 text-[11px] text-muted-foreground/70">{time}</p></div></div>)}</CardContent></Card></div>
        </section>
      </main>
    </div>
  )
}
