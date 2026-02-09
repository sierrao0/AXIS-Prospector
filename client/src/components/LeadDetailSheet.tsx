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
  ExternalLink,
  MapPin,
  Phone,
  Star,
  Zap,
  Code2,
  Share2
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
    if (score >= 80) return "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400";
    if (score >= 60) return "bg-amber-500/15 text-amber-600 dark:text-amber-400";
    if (score >= 40) return "bg-orange-500/15 text-orange-600 dark:text-orange-400";
    return "bg-rose-500/15 text-rose-600 dark:text-rose-400";
  };

  const getScoreLabel = (score: number | null | undefined) => {
    if (score === null || score === undefined) return "Unknown";
    if (score >= 80) return "Excellent";
    if (score >= 60) return "Good";
    if (score >= 40) return "Fair";
    return "Needs Work";
  };

  const hasContactInfo = lead.website || lead.phone;
  const hasEmails = lead.emails && lead.emails.length > 0;
  const hasSocials = lead.social_links && Object.keys(lead.social_links).length > 0;
  const hasTechStack = lead.tech_stack && lead.tech_stack.length > 0;
  const hasAuditData = lead.website && (lead.ssl_valid !== null || hasTechStack || hasEmails || hasSocials);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[420px] sm:w-[540px] overflow-y-auto p-0">
        {/* Hero Header */}
        <div className="relative px-6 pt-6 pb-5 bg-gradient-to-b from-muted/80 to-background border-b">
          <SheetHeader className="space-y-3">
            {/* Score & Status Row */}
            <div className="flex items-center gap-2">
              <div className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold",
                getScoreColor(lead.ai_score)
              )}>
                <Zap className="h-3.5 w-3.5" />
                <span>{lead.ai_score ?? 0}</span>
                <span className="opacity-70">•</span>
                <span className="font-medium">{getScoreLabel(lead.ai_score)}</span>
              </div>
              
              {lead.status === 'caliente' && (
                <Badge className="bg-rose-500/15 text-rose-600 dark:text-rose-400 border-0">
                  Hot Lead
                </Badge>
              )}
              
              {lead.audit_status === 'auditing' && (
                <Badge variant="secondary" className="animate-pulse border-0">
                  Auditing...
                </Badge>
              )}
            </div>
            
            {/* Title */}
            <SheetTitle className="text-xl font-bold leading-tight pr-8">
              {lead.name}
            </SheetTitle>
            
            {/* Meta Info */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
              {lead.category && (
                <span className="font-medium text-foreground/80">{lead.category}</span>
              )}
              {lead.rating && (
                <div className="flex items-center gap-1 text-amber-500">
                  <Star className="h-3.5 w-3.5 fill-current" />
                  <span className="font-medium">{lead.rating}</span>
                  {lead.reviews_count && (
                    <span className="text-muted-foreground text-xs">({lead.reviews_count})</span>
                  )}
                </div>
              )}
            </div>
            
            {lead.location && (
              <div className="flex items-start gap-2 text-sm text-muted-foreground">
                <MapPin className="h-4 w-4 shrink-0 mt-0.5" />
                <span className="line-clamp-2">{lead.location}</span>
              </div>
            )}
          </SheetHeader>
        </div>

        <div className="px-6 py-5 space-y-5">
          
          {/* Contact Section */}
          {hasContactInfo && (
            <section className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Contact
              </h3>
              <div className="grid gap-2">
                {lead.website && (
                  <a 
                    href={lead.website} 
                    target="_blank" 
                    rel="noreferrer"
                    className="flex items-center gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors group"
                  >
                    <div className="p-2 rounded-md bg-muted">
                      <Globe className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate group-hover:text-foreground">
                        {(() => {
                          try { return new URL(lead.website).hostname; } 
                          catch { return lead.website; }
                        })()}
                      </p>
                    </div>
                    <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </a>
                )}
                
                {lead.phone && (
                  <a 
                    href={`tel:${lead.phone}`}
                    className="flex items-center gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                  >
                    <div className="p-2 rounded-md bg-muted">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <p className="text-sm font-medium">{lead.phone}</p>
                  </a>
                )}
              </div>
            </section>
          )}

          {/* Audit Results */}
          {hasAuditData && (
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Website Audit
                </h3>
                {lead.audit_completed_at && (
                  <span className="text-[10px] text-muted-foreground">
                    {new Date(lead.audit_completed_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              
              {/* Security & Tech Status Pills */}
              <div className="flex flex-wrap gap-2">
                {lead.ssl_valid !== null && (
                  <div className={cn(
                    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium",
                    lead.ssl_valid 
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" 
                      : "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                  )}>
                    {lead.ssl_valid ? (
                      <>
                        <Shield className="h-3.5 w-3.5" />
                        SSL Secure
                      </>
                    ) : (
                      <>
                        <XCircle className="h-3.5 w-3.5" />
                        No SSL
                      </>
                    )}
                  </div>
                )}
                
                {lead.web_obsoleta !== null && (
                  <div className={cn(
                    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium",
                    lead.web_obsoleta 
                      ? "bg-rose-500/10 text-rose-600 dark:text-rose-400" 
                      : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  )}>
                    {lead.web_obsoleta ? (
                      <>
                        <XCircle className="h-3.5 w-3.5" />
                        Outdated Tech
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Modern Stack
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Emails */}
              {hasEmails && (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                    <Mail className="h-3.5 w-3.5" />
                    Emails Found
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {lead.emails!.map((email) => (
                      <a
                        key={email}
                        href={`mailto:${email}`}
                        className="inline-flex items-center px-2.5 py-1 rounded-md bg-muted hover:bg-muted/80 text-xs font-mono transition-colors"
                      >
                        {email}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Social Links */}
              {hasSocials && (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                    <Share2 className="h-3.5 w-3.5" />
                    Social Presence
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(lead.social_links!).map(([network, url]) => (
                      <a 
                        key={network} 
                        href={url} 
                        target="_blank" 
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-muted hover:bg-muted/80 text-xs font-medium capitalize transition-colors"
                      >
                        {network}
                        <ExternalLink className="h-3 w-3 opacity-50" />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Tech Stack */}
              {hasTechStack && (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                    <Code2 className="h-3.5 w-3.5" />
                    Technologies
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {lead.tech_stack!.map((tech) => (
                      <Badge 
                        key={tech} 
                        variant="secondary" 
                        className="font-normal"
                      >
                        {tech}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Raw Data - Only if audit_data exists */}
          {lead.audit_data && Object.keys(lead.audit_data).length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground font-medium select-none flex items-center gap-2 py-2">
                <span>Raw Audit Data</span>
                <span className="group-open:rotate-180 transition-transform text-[10px]">▼</span>
              </summary>
              <pre className="mt-2 p-3 bg-muted/50 rounded-lg border overflow-x-auto text-[10px] leading-relaxed text-muted-foreground max-h-48">
                {JSON.stringify(lead.audit_data, null, 2)}
              </pre>
            </details>
          )}

        </div>
      </SheetContent>
    </Sheet>
  );
}
