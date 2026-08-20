import { createFileRoute } from '@tanstack/react-router'
import { Mail, Plus, ShieldCheck, UserRound } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export const Route = createFileRoute('/app/team')({ component: TeamPage })

function TeamPage() {
  return <div className="space-y-6"><div className="flex items-end justify-between"><div><h1 className="font-serif text-4xl font-medium tracking-tight">Team</h1><p className="mt-2 text-sm text-muted-foreground">Collaborate with the people operating your bots.</p></div><Button><Plus className="size-4" /> Invite member</Button></div><Card className="border-border/70"><CardHeader><CardTitle className="text-base">Workspace members <span className="ml-2 text-sm font-normal text-muted-foreground">3</span></CardTitle></CardHeader><CardContent className="divide-y divide-border/60 p-0">{[['AM', 'Alex Morgan', 'alex@northstar.team', 'Owner'], ['PS', 'Priya Shah', 'priya@northstar.team', 'Admin'], ['JK', 'Jon Kim', 'jon@northstar.team', 'Viewer']].map(([initials, name, email, role]) => <div className="flex items-center justify-between px-6 py-4" key={email}><div className="flex items-center gap-3"><div className="flex size-9 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">{initials}</div><div><p className="text-sm font-semibold">{name}</p><p className="flex items-center gap-1 text-xs text-muted-foreground"><Mail className="size-3" />{email}</p></div></div><div className="flex items-center gap-2 text-xs text-muted-foreground"><ShieldCheck className="size-4 text-primary" />{role}</div></div>)}</CardContent></Card></div>
}
