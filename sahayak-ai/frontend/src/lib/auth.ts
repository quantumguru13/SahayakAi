// Local authentication management for Sahayak AI (Demo/Hackathon mode)

export interface AuthUser {
  email: string;
  name: string;
  role: string;
  loginTime: string;
}

const AUTH_KEY = "sahayak.auth_user";

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const local = localStorage.getItem(AUTH_KEY);
    const session = sessionStorage.getItem(AUTH_KEY);
    return Boolean(local || session);
  } catch {
    return false;
  }
}

export function getAuthUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(AUTH_KEY) || sessionStorage.getItem(AUTH_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function loginLocal(
  email: string,
  pass: string,
  rememberMe: boolean = true
): { success: boolean; error?: string; user?: AuthUser } {
  const cleanEmail = email.trim().toLowerCase();
  
  if (!cleanEmail || !pass) {
    return { success: false, error: "Please enter both email and password." };
  }

  if (cleanEmail !== "admin@sahayak.ai" || pass !== "admin123") {
    return { success: false, error: "Invalid credentials. Use admin@sahayak.ai / admin123" };
  }

  const user: AuthUser = {
    email: "admin@sahayak.ai",
    name: "NGO Administrator",
    role: "Field Director",
    loginTime: new Date().toISOString(),
  };

  try {
    const serialized = JSON.stringify(user);
    if (rememberMe) {
      localStorage.setItem(AUTH_KEY, serialized);
      sessionStorage.removeItem(AUTH_KEY);
    } else {
      sessionStorage.setItem(AUTH_KEY, serialized);
      localStorage.removeItem(AUTH_KEY);
    }
    return { success: true, user };
  } catch (e) {
    return { success: false, error: "Failed to save login session." };
  }
}

export function loginDemoUser(): { success: boolean; error?: string; user?: AuthUser } {
  return loginLocal("admin@sahayak.ai", "admin123", true);
}

export function logoutLocal(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(AUTH_KEY);
    sessionStorage.removeItem(AUTH_KEY);
  } catch {
    // ignore
  }
}
