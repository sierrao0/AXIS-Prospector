'use client';

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
import { ExternalLink, Phone, MapPin, Star, AlertTriangle } from 'lucide-react';

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
    label: '🔥 Caliente',
    variant: 'destructive',
    className: 'bg-red-500 hover:bg-red-600 text-white',
  },
  tibio: {
    label: '🌡️ Tibio',
    variant: 'default',
    className: 'bg-blue-500 hover:bg-blue-600 text-white',
  },
  frío: {
    label: '❄️ Frío',
    variant: 'secondary',
    className: 'bg-slate-400 hover:bg-slate-500 text-white',
  },
  contactado: {
    label: '📞 Contactado',
    variant: 'outline',
    className: 'border-green-500 text-green-600',
  },
  cerrado: {
    label: '✅ Cerrado',
    variant: 'default',
    className: 'bg-green-600 hover:bg-green-700 text-white',
  },
};

/**
 * Tabla de leads con badges de color dinámico según status.
 */
export function LeadsTable({ leads, isLoading }: LeadsTableProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <div className="size-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p>Cargando leads...</p>
        </div>
      </div>
    );
  }

  if (leads.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <p className="text-lg font-medium">No hay leads aún</p>
        <p className="text-sm">Inicia una prospección para generar leads</p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Nombre</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Categoría</TableHead>
          <TableHead>Rating</TableHead>
          <TableHead>Ubicación</TableHead>
          <TableHead>Contacto</TableHead>
          <TableHead>Web</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {leads.map((lead) => {
          const status = statusConfig[lead.status] || statusConfig.frío;

          return (
            <TableRow key={lead.id}>
              {/* Nombre */}
              <TableCell className="font-medium">
                {lead.name || 'Sin nombre'}
              </TableCell>

              {/* Status Badge */}
              <TableCell>
                <Badge className={status.className}>{status.label}</Badge>
              </TableCell>

              {/* Categoría */}
              <TableCell className="text-muted-foreground">
                {lead.category || '—'}
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
                    <span className="max-w-50 truncate">{lead.location}</span>
                  </div>
                ) : (
                  '—'
                )}
              </TableCell>

              {/* Teléfono */}
              <TableCell>
                {lead.phone ? (
                  <a
                    href={`tel:${lead.phone}`}
                    className="flex items-center gap-1 text-sm text-primary hover:underline"
                  >
                    <Phone className="size-3" />
                    {lead.phone}
                  </a>
                ) : (
                  '—'
                )}
              </TableCell>

              {/* Website */}
              <TableCell>
                {lead.website ? (
                  <div className="flex items-center gap-2">
                    <a
                      href={lead.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-sm text-primary hover:underline"
                    >
                      <ExternalLink className="size-3" />
                      Ver sitio
                    </a>
                    {lead.web_obsoleta && (
                      <span title={lead.web_analisis_motivo || 'Web obsoleta'}>
                        <AlertTriangle className="size-4 text-amber-500" />
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="text-muted-foreground">Sin web</span>
                )}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
