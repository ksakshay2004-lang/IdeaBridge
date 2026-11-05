import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import { api, setUnauthorizedHandler, tokenStore } from "./api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null; loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (data: { email: string; password: string; full_name: string; role: "creator" | "entrepreneur"; company_name?: string }) => Promise<User>;
  logout: () => void; refresh: () => Promise<void>;
}
const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);
export const useAuth = () => useContext(Ctx);
export const homePath = (u: User) => `/app/${u.role}`;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(!!tokenStore.get());

  const logout = useCallback(() => { tokenStore.clear(); setUser(null); }, []);
  const refresh = useCallback(async () => { setUser(await api.get<User>("/auth/me")); }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (tokenStore.get()) refresh().catch(logout).finally(() => setLoading(false));
  }, [logout, refresh]);

  const accept = (r: { access_token: string; user: User }) => { tokenStore.set(r.access_token); setUser(r.user); return r.user; };
  const value = useMemo<AuthCtx>(() => ({
    user, loading, logout, refresh,
    login: async (email, password) => accept(await api.post("/auth/login", { email, password })),
    register: async (data) => accept(await api.post("/auth/register", data)),
  }), [user, loading, logout, refresh]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
