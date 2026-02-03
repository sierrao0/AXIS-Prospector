import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Lead } from "@/lib/supabase";
import { 
  CheckCircle2, 
  XCircle, 
  Globe, 
  Mail, 
  Shield, 
  AlertTriangle, 
  ExternalLink,
  MapPin,
  Store,
  Phone,
  Info
} from "lucide-react";
import { cn } from "@/lib/utils";

interface LeadDetailSheetProps {
  lead: Lead | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function LeadDetailSheet({ lead, open, onOpenChange }: LeadDetailSheetProps) {
  if (!lead) return null;

  const getScoreColor = (score: number | null | undefined) => {
    if (score === null || score === undefined) return "bg-muted text-muted-foreground";
    if (score >= 80) return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
    if (score >= 60) return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
    if (score >= 40) return "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20";
    return "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20";
  };

  const getScoreExplanation = (lead: Lead) => {
    const parts = [];
    if (lead.ssl_valid) parts.push("• SSL Seguro (+15)");
    if (lead.emails?.length) parts.push("• Emails encontrados (+10)");
    if (lead.tech_stack?.length && lead.website && !lead.web_obsoleta) parts.push("• Stack Moderno (+10)");
    if (lead.social_links && Object.keys(lead.social_links).length > 0) parts.push("• Redes Sociales (+5/u)");
    if (!lead.website) parts.push("• Sin Website (-30)");
    
    return "Factores de Scoring:\n" + parts.join("\n") || "Sin datos suficientes";
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[600px] overflow-y-auto">
        <SheetHeader className="pb-4 border-b">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="group relative">
                 <Badge 
                    variant="outline" 
                    className={cn("text-white font-bold cursor-help pr-2", getScoreColor(lead.ai_score))}
                    title={getScoreExplanation(lead)}
                 >
                    AI Score: {lead.ai_score ?? 0}
                    <Info className="ml-1.5 h-3.5 w-3.5 opacity-80" />
                 </Badge>
              </div>
              
              {lead.status === 'caliente' && <Badge className="bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20">Hot</Badge>}
              {lead.audit_status === 'auditing' && <Badge variant="secondary" className="animate-pulse">Auditing...</Badge>}
            </div>
            {lead.rating && (
                <div className="flex items-center gap-1 text-xs font-medium text-amber-500">
                    <span className="text-sm">★</span> {lead.rating} ({lead.reviews_count})
                </div>
            )}
          </div>
          
          <SheetTitle className="text-2xl font-bold leading-tight">{lead.name}</SheetTitle>
          
          <div className="flex flex-col gap-1.5 mt-2 text-sm text-muted-foreground">
             <div className="flex items-center gap-2">
                <Store className="h-4 w-4 shrink-0" />
                <span>{lead.category || "Categoría desconocida"}</span>
             </div>
             <div className="flex items-start gap-2">
                <MapPin className="h-4 w-4 shrink-0 mt-0.5" />
                <span className="line-clamp-2">{lead.location || "Ubicación desconocida"}</span>
             </div>
          </div>
        </SheetHeader>

        <div className="space-y-6 pt-6">
          {/* Contact Info Card */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 bg-muted/60 rounded-lg border">
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                 <Globe className="h-3.5 w-3.5" /> Website
              </h4>
              {lead.website ? (
                <a 
                  href={lead.website} 
                  target="_blank" 
                  rel="noreferrer"
                  className="flex items-center gap-2 text-foreground hover:text-muted-foreground transition-colors break-all text-sm font-medium"
                >
                  {(() => {
                    try {
                      return new URL(lead.website).hostname;
                    } catch {
                      return "Ver enlace";
                    }
                  })()}
                  <ExternalLink className="h-3 w-3" />
                </a>
              ) : (
                <span className="text-muted-foreground text-sm flex items-center gap-2">
                  <XCircle className="h-4 w-4 opacity-50" /> No disponible
                </span>
              )}
            </div>

            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Phone className="h-3.5 w-3.5" /> Teléfono
              </h4>
              {lead.phone ? (
                 <a href={`tel:${lead.phone}`} className="text-sm font-medium hover:text-foreground/80 block truncate">
                    {lead.phone}
                 </a>
              ) : (
                <span className="text-muted-foreground text-sm flex items-center gap-2">
                   <AlertTriangle className="h-3.5 w-3.5 opacity-50" /> No disponible
                </span>
              )}
            </div>
          </div>

          {/* Audit Results */}
          <div>
            <h3 className="text-base font-semibold mb-4 flex items-center gap-2">
                Deep Audit Results
                {lead.audit_completed_at && <span className="text-xs font-normal text-muted-foreground ml-auto">Actualizado: {new Date(lead.audit_completed_at).toLocaleDateString()}</span>}
            </h3>
            
            {/* Grid for Security and Tech Status */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="p-3 border rounded-lg bg-muted/50 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs font-semibold text-muted-foreground uppercase">Security</span>
                </div>
                <div className="flex items-center gap-2">
                  {lead.ssl_valid ? (
                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="h-5 w-5" />
                      <span className="font-medium text-sm">Secure (SSL)</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400">
                      <XCircle className="h-5 w-5" />
                      <span className="font-medium text-sm">Insecure</span>
                    </div>
                  )}
                </div>
              </div>

               <div className="p-3 border rounded-lg bg-muted/50 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs font-semibold text-muted-foreground uppercase">Tech Status</span>
                </div>
                <div className="flex items-center">
                  {lead.web_obsoleta ? (
                    <Badge variant="destructive" className="h-6">Obsolete</Badge>
                  ) : lead.website ? (
                    <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 h-6">Modern Stack</Badge>
                  ) : (
                    <Badge variant="secondary" className="h-6">N/A</Badge>
                  )}
                </div>
              </div>
            </div>

            {/* Found Data Grid */}
            <div className="grid grid-cols-1 gap-4">
                
                {/* Emails & Socials Row */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Emails */}
                    <div className="border rounded-lg p-3 bg-muted/40">
                        <h4 className="text-xs font-semibold text-muted-foreground mb-3 flex items-center gap-2">
                            <Mail className="h-3.5 w-3.5" /> Contact Emails
                        </h4>
                        {lead.emails && lead.emails.length > 0 ? (
                            <div className="flex flex-col gap-2">
                            {lead.emails.map((email) => (
                                <div key={email} className="flex items-center gap-2 text-sm bg-muted/50 p-1.5 rounded border border-border">
                                    <div className="h-2 w-2 rounded-full bg-foreground/30 shrink-0" />
                                    <span className="truncate select-all text-xs font-mono">{email}</span>
                                </div>
                            ))}
                            </div>
                        ) : (
                            <div className="text-xs text-muted-foreground py-2 italic opacity-60">No emails found</div>
                        )}
                    </div>

                    {/* Socials */}
                    <div className="border rounded-lg p-3 bg-muted/40">
                        <h4 className="text-xs font-semibold text-muted-foreground mb-3 flex items-center gap-2">
                            <Globe className="h-3.5 w-3.5" /> Social Presence
                        </h4>
                        {lead.social_links && Object.keys(lead.social_links).length > 0 ? (
                            <div className="flex flex-col gap-2">
                            {Object.entries(lead.social_links).map(([network, url]) => (
                                <a 
                                key={network} 
                                href={url} 
                                target="_blank" 
                                rel="noreferrer"
                                className="flex items-center justify-between text-xs px-2 py-1.5 rounded hover:bg-muted border border-transparent hover:border-border transition-colors group"
                                >
                                <span className="capitalize font-medium text-foreground/80 group-hover:text-foreground">{network}</span>
                                <ExternalLink className="h-3 w-3 opacity-30 group-hover:opacity-100" />
                                </a>
                            ))}
                            </div>
                        ) : (
                            <div className="text-xs text-muted-foreground py-2 italic opacity-60">No profiles found</div>
                        )}
                    </div>
                </div>

                {/* Tech Stack */}
                <div className="border rounded-lg p-4 bg-muted/40">
                    <h4 className="text-xs font-semibold text-muted-foreground mb-3">Technology Stack</h4>
                    {lead.tech_stack && lead.tech_stack.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                        {lead.tech_stack.map((tech) => (
                            <Badge key={tech} variant="outline" className="bg-muted/50 text-foreground border-border px-3 py-1">
                                {tech}
                            </Badge>
                        ))}
                        </div>
                    ) : (
                        <span className="text-sm text-muted-foreground italic">No technology detected</span>
                    )}
                </div>
            </div>

          </div>

          {/* Raw Data (Collapsible) */}
          <div className="pt-4 border-t">
             <details className="text-xs group">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground font-medium select-none flex items-center gap-2">
                  <span>View Raw Audit Data</span>
                  <span className="group-open:rotate-180 transition-transform text-[10px]">▼</span>
              </summary>
              <pre className="mt-2 p-3 bg-muted/50 rounded border overflow-x-auto text-[10px] leading-relaxed text-muted-foreground">
                {JSON.stringify(lead.audit_data || {}, null, 2)}
              </pre>
             </details>
          </div>

        </div>
      </SheetContent>
    </Sheet>
  );
}
