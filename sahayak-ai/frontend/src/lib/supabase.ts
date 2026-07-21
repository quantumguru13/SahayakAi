// Supabase browser client + a module-level access-token holder.
//
// When NEXT_PUBLIC_SUPABASE_URL / _PUBLISHABLE_KEY are absent, auth is disabled
// and the app runs in the keyless demo mode (no login gate). When present, the
// client manages the session and the token is attached to backend requests.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

export const authEnabled = Boolean(url && publishableKey);

export const supabase: SupabaseClient | null = authEnabled
  ? createClient(url as string, publishableKey as string, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null;

// The api client isn't a React hook, so it reads the current token from here.
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}
