'use client';

import { useState } from 'react';
import { Lead } from '@/lib/supabase';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ExternalLink, Phone, MapPin, Star, AlertTriangle, Loader2, Lock, AlertCircle } from 'lucide-react';
import { LeadDetailSheet } from './LeadDetailSheet';

interface LeadsTableProps {
  leads: Lead[];
  isLoading?: boolean;
}

/**
 * Mapeo de status a variantes de badge con colores.
 */
const statusConfig: Record<
  Lead['status'],
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; className: string }
> = {
  caliente: {
    label: 'Caliente',
    variant: 'destructive',
    className: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20 hover:bg-rose-500/20',
  },
  tibio: {
    label: 'Tibio',
    variant: 'default',
    className: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 hover:bg-amber-500/20',
  },
  frío: {
    label: 'Frío',
    variant: 'secondary',
    className: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20 hover:bg-sky-500/20',
  },
  contactado: {
    label: 'Contactado',
    variant: 'outline',
    className: 'bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20 hover:bg-violet-500/20',
  },
  cerrado: {
    label: 'Cerrado',
    variant: 'default',
    className: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20',
  },
};

/**
 * THE HUNTER LOGIC: Configuración de categorías de leads
 * 🎯 ARCHITECT_TARGET = Sin web, máxima oportunidad
 * 🔥 HOT_OPTIMIZATION = Infraestructura sólida, listo para optimizar
 */
const categoryConfig: Record<string, { label: string; className: string; description: string }> = {
  ARCHITECT_TARGET: {
    label: 'Target',
    className: 'bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20 hover:bg-violet-500/20',
    description: 'Sin presencia web - Candidato ideal para The Architect'
  },
  HOT_OPTIMIZATION: {
    label: 'Hot',
    className: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20',
    description: 'Infraestructura sólida - Listo para optimización'
  },
  WARM_IMPROVEMENT: {
    label: 'Warm',
    className: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 hover:bg-amber-500/20',
    description: 'Tiene base, necesita mejoras técnicas'
  },
  COLD_PROBLEMS: {
    label: 'Cold',
    className: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20 hover:bg-sky-500/20',
    description: 'Problemas técnicos evidentes'
  },
  ICE: {
    label: 'Ice',
    className: 'bg-muted text-muted-foreground',
    description: 'Baja prioridad - Poca oportunidad'
  },
};

export function LeadsTable({ leads, isLoading }: LeadsTableProps) {
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);

  const handleRowClick = (lead: Lead) => {
    setSelectedLead(lead);
    setIsSheetOpen(true);
  };

  const getScoreBadgeClass = (score: number | null | undefined) => {
    if (score === null || score === undefined) return "bg-muted text-muted-foreground";
    if (score >= 80) return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
    if (score >= 60) return "bg-amber-500/10 text-amber-600 dark:text-amber-400";
    if (score >= 40) return "bg-orange-500/10 text-orange-600 dark:text-orange-400";
    return "bg-rose-500/10 text-rose-600 dark:text-rose-400";
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-3">
          <div className="size-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          <p className="text-slate-300 font-medium">Cargando leads...</p>
        </div>
      </div>
    );
  }

  if (leads.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <p className="text-lg font-semibold">No hay leads aún</p>
        <p className="text-sm">Inicia una prospección para generar leads</p>
      </div>
    );
  }

  return (
    <>
      <div className="border border-border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-b border-border hover:bg-transparent bg-muted/50">
              <TableHead className="text-foreground font-medium">Nombre</TableHead>
              <TableHead className="text-foreground font-medium">Score IA</TableHead>
              <TableHead className="text-foreground font-medium" title="SSL y seguridad">SSL</TableHead>
              <TableHead className="text-foreground font-medium" title="The Hunter Logic - Categoría de oportunidad">Hunter</TableHead>
              <TableHead className="text-foreground font-medium">Status</TableHead>
              <TableHead className="text-foreground font-medium">Rating</TableHead>
              <TableHead className="text-foreground font-medium">Ubicación</TableHead>
              <TableHead className="text-foreground font-medium">Contacto</TableHead>
              <TableHead className="text-foreground font-medium">Web</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {leads.map((lead, idx) => {
              const status = statusConfig[lead.status] || statusConfig.frío;

              return (
                <TableRow 
                  key={lead.id}
                  className={`cursor-pointer border-b border-border hover:bg-muted/50 transition-colors ${
                    idx % 2 === 0 ? 'bg-background' : 'bg-muted/30'
                  }`}
                  onClick={() => handleRowClick(lead)}
                >
                  {/* Nombre */}
                  <TableCell className="font-medium text-foreground">
                    {lead.name || 'Sin nombre'}
                  </TableCell>

                  {/* Audit Score */}
                  <TableCell>
                    {lead.audit_status === 'auditing' ? (
                      <div className="flex items-center gap-2" title="Auditando website...">
                        <Loader2 className="size-4 animate-spin text-muted-foreground" />
                        <span className="text-xs text-muted-foreground hidden lg:inline">Auditando...</span>
                      </div>
                    ) : lead.audit_status === 'completed' && lead.ai_score !== null ? (
                      <div className="flex items-center gap-2">
                        <div className="w-12 bg-muted rounded-full h-2 overflow-hidden">
                          <div 
                            className={`h-full transition-all ${
                              (lead.ai_score ?? 0) >= 80 ? 'bg-emerald-500' :
                              (lead.ai_score ?? 0) >= 60 ? 'bg-amber-500' :
                              (lead.ai_score ?? 0) >= 40 ? 'bg-orange-500' : 'bg-rose-500'
                            }`}
                            style={{ width: `${lead.ai_score}%` }}
                          />
                        </div>
                        <Badge className={`${getScoreBadgeClass(lead.ai_score)} text-xs`}>
                          {lead.ai_score}
                        </Badge>
                      </div>
                    ) : lead.audit_status === 'failed' ? (
                      <Badge variant="destructive" className="text-xs">Falló</Badge>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </TableCell>

                  {/* SSL Status */}
                  <TableCell title={lead.ssl_valid ? "SSL válido" : lead.ssl_valid === false ? "SSL inválido o ausente" : "Pendiente"}>
                    {lead.audit_status === 'auditing' ? (
                      <span className="text-muted-foreground text-xs">—</span>
                    ) : lead.audit_status === 'completed' ? (
                      lead.ssl_valid ? (
                        <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
                          <Lock className="size-3.5" />
                          <span className="hidden sm:inline">Seguro</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-rose-600 dark:text-rose-400 text-xs font-medium">
                          <AlertCircle className="size-3.5" />
                          <span className="hidden sm:inline">No</span>
                        </div>
                      )
                    ) : lead.audit_status === 'failed' ? (
                      <span className="text-muted-foreground text-xs">Error</span>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </TableCell>

                  {/* Hunter Category - THE HUNTER LOGIC */}
                  <TableCell>
                    {lead.lead_category ? (
                      <Badge 
                        className={categoryConfig[lead.lead_category]?.className || 'bg-muted'}
                        title={categoryConfig[lead.lead_category]?.description}
                      >
                        {categoryConfig[lead.lead_category]?.label || lead.lead_category}
                      </Badge>
                    ) : lead.audit_status === 'auditing' ? (
                      <span className="text-muted-foreground text-xs">—</span>
                    ) : (
                      <span className="text-muted-foreground text-xs">Pendiente</span>
                    )}
                  </TableCell>

                  {/* Status Badge */}
                  <TableCell>
                    <Badge className={status.className}>{status.label}</Badge>
                  </TableCell>

                {/* Rating */}
                <TableCell>
                  {lead.rating !== null ? (
                    <div className="flex items-center gap-1">
                      <Star className="size-4 fill-yellow-400 text-yellow-400" />
                      <span>{lead.rating.toFixed(1)}</span>
                      {lead.reviews_count !== null && (
                        <span className="text-xs text-muted-foreground">
                          ({lead.reviews_count})
                        </span>
                      )}
                    </div>
                  ) : (
                    '—'
                  )}
                </TableCell>

                {/* Ubicación */}
                <TableCell>
                  {lead.location ? (
                    <div className="flex items-center gap-1 text-sm">
                      <MapPin className="size-3 text-muted-foreground" />
                      <span className="truncate" title={lead.location}>{lead.location}</span>
                    </div>
                  ) : (
                    '—'
                  )}
                </TableCell>

                {/* Teléfono */}
                <TableCell>
                  {lead.phone ? (
                    <div 
                      className="flex items-center gap-1 text-sm text-primary hover:underline"
                      onClick={(e) => { e.stopPropagation(); window.location.href = `tel:${lead.phone}`; }}
                    >
                      <Phone className="size-3" />
                      {lead.phone}
                    </div>
                  ) : (
                    '—'
                  )}
                </TableCell>

                {/* Website */}
                <TableCell>
                  {lead.website ? (
                    <div className="flex items-center gap-2">
                       <div 
                        className="flex items-center gap-1 text-sm text-foreground hover:text-muted-foreground transition-colors"
                        onClick={(e) => { e.stopPropagation(); window.open(lead.website || '', '_blank'); }}
                      >
                        <ExternalLink className="size-3" />
                        Link
                      </div>
                      {lead.web_obsoleta && (
                        <span title={lead.web_analisis_motivo || 'Web obsoleta'}>
                          <AlertTriangle className="size-4 text-amber-500 dark:text-amber-400" />
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-muted-foreground text-xs">No web</span>
                  )}
                </TableCell>
              </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <LeadDetailSheet 
        lead={selectedLead} 
        open={isSheetOpen} 
        onOpenChange={setIsSheetOpen} 
      />
    </>
  );
}
