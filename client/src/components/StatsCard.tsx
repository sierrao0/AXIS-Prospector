'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Lead } from '@/lib/supabase';
import { TrendingUp, Flame, Thermometer, Snowflake, CheckCircle } from 'lucide-react';

interface StatsCardProps {
  leads: Lead[];
}

export function StatsCard({ leads }: StatsCardProps) {
  const totalLeads = leads.length;
  const hotLeads = leads.filter(l => l.status === 'caliente').length;
  const warmLeads = leads.filter(l => l.status === 'tibio').length;
  const coldLeads = leads.filter(l => l.status === 'frío').length;
  const closedLeads = leads.filter(l => l.status === 'cerrado').length;
  const avgScore = leads.length > 0 
    ? Math.round(leads.reduce((acc, l) => acc + (l.ai_score || 0), 0) / leads.length)
    : 0;

  const stats = [
    { label: 'Total', value: totalLeads, icon: TrendingUp, color: 'text-foreground' },
    { label: 'Calientes', value: hotLeads, icon: Flame, color: 'text-rose-500 dark:text-rose-400' },
    { label: 'Tibios', value: warmLeads, icon: Thermometer, color: 'text-amber-500 dark:text-amber-400' },
    { label: 'Fríos', value: coldLeads, icon: Snowflake, color: 'text-sky-500 dark:text-sky-400' },
    { label: 'Cerrados', value: closedLeads, icon: CheckCircle, color: 'text-emerald-500 dark:text-emerald-400' },
    { label: 'Score Prom', value: `${avgScore}%`, icon: TrendingUp, color: 'text-violet-500 dark:text-violet-400' },
  ];

  return (
    <Card className="border-border bg-card shadow-sm">
      <CardContent className="p-6">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {stats.map((stat, idx) => {
            const Icon = stat.icon;
            return (
              <div key={idx} className="space-y-1 p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors">
                <div className="flex items-center gap-2">
                  <Icon className={`h-4 w-4 ${stat.color}`} />
                  <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{stat.label}</span>
                </div>
                <p className="text-2xl font-semibold text-foreground">{stat.value}</p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
