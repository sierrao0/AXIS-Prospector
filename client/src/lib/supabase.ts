import { createClient, SupabaseClient } from '@supabase/supabase-js';

/**
 * Configuración de Supabase - Lee directamente de process.env
 * para evitar problemas de timing con la carga de módulos
 */
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

/**
 * Cliente Supabase para el frontend.
 * Se inicializa de forma lazy para evitar errores si las credenciales no están disponibles.
 */
let _supabase: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (!_supabase) {
    if (!supabaseUrl || !supabaseAnonKey) {
      console.warn('⚠️ Supabase credentials not configured. Realtime features disabled.');
      // Crear cliente con valores dummy que fallarán silenciosamente
      _supabase = createClient('https://placeholder.supabase.co', 'placeholder-key');
    } else {
      _supabase = createClient(supabaseUrl, supabaseAnonKey);
    }
  }
  return _supabase;
}

// Export para compatibilidad con código existente
export const supabase = getSupabase();

/**
 * Tipos para la tabla de leads (espejo del backend)
 * 
 * 🎯 THE HUNTER LOGIC:
 * - ai_score: Calidad del lead (0-100)
 * - opportunity_score: Qué tanto NECESITA nuestros servicios (0-100)
 * 
 * Categorías:
 * - 80-100 ai_score = Hot (infraestructura sólida)
 * - 60-79 = Warm (necesita mejoras)
 * - 40-59 = Cold (problemas técnicos)
 * - 0-39 + alto opportunity = OPPORTUNITY (sin web = The Architect target)
 */
export interface Lead {
  id: number | string;
  name: string | null;
  website: string | null;
  phone: string | null;
  rating: number | null;
  reviews_count: number | null;
  location: string | null;
  category: string | null;
  status: 'caliente' | 'tibio' | 'frío' | 'contactado' | 'cerrado';
  web_obsoleta: boolean | null;
  web_analisis_motivo: string | null;
  created_at: string;
  
  // Phase 1: Deep Audit Fields
  audit_status?: 'pending' | 'auditing' | 'completed' | 'failed';
  audit_data?: Record<string, any> | null;
  ai_score?: number | null;
  opportunity_score?: number | null;  // 🎯 THE HUNTER: Qué tanto necesita nuestros servicios
  lead_category?: 'ARCHITECT_TARGET' | 'HOT_OPTIMIZATION' | 'WARM_IMPROVEMENT' | 'COLD_PROBLEMS' | 'ICE' | null;  // 🎯 Categoría final
  ssl_valid?: boolean | null;
  emails?: string[] | null;
  tech_stack?: string[] | null;
  social_links?: Record<string, string> | null;
  audit_completed_at?: string | null;
}

export type LeadInsert = Omit<Lead, 'id' | 'created_at'>;
export type LeadUpdate = Partial<LeadInsert>;
