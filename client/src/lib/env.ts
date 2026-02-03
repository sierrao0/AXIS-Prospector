/**
 * Configuración de variables de entorno para el cliente.
 */

interface ClientEnv {
  apiUrl: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
}

function getEnvVar(key: string, fallback?: string): string {
  const value = process.env[key] ?? fallback;
  
  if (value === undefined) {
    throw new Error(`❌ Variable de entorno faltante: ${key}`);
  }
  
  return value;
}

export const env: ClientEnv = {
  apiUrl: getEnvVar('NEXT_PUBLIC_API_URL', 'http://localhost:8000/api/v1'),
  supabaseUrl: getEnvVar('NEXT_PUBLIC_SUPABASE_URL', 'https://znpcflxboiktmekgcdue.supabase.co'),
  supabaseAnonKey: getEnvVar('NEXT_PUBLIC_SUPABASE_ANON_KEY', ''),
};

// Validación en desarrollo
if (process.env.NODE_ENV === 'development') {
  console.log('🔧 Environment config loaded:', {
    apiUrl: env.apiUrl,
    supabaseUrl: env.supabaseUrl ? '✓ configured' : '✗ missing',
  });
}
