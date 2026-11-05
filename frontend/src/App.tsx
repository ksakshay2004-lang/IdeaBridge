import { ReactNode } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { homePath, useAuth } from "./lib/auth";
import type { Role } from "./lib/types";
import { DashboardLayout, PublicLayout } from "./components/Layout";
import { Button, Spinner } from "./components/ui";
import Landing from "./pages/public/Landing";
import { About, HowItWorks } from "./pages/public/Info";
import Explore from "./pages/public/Explore";
import { Login, Register } from "./pages/public/Auth";
import IdeaDetail from "./pages/shared/IdeaDetail";
import Collaboration from "./pages/shared/Collaboration";
import Messages from "./pages/shared/Messages";
import Profile from "./pages/shared/Profile";
import { CreatorOverview, MyIdeas, Reports, SubmitIdea } from "./pages/creator/Creator";
import { Discover, EntrepreneurOverview, Recommended, Saved } from "./pages/entrepreneur/Entrepreneur";
import { AdminAnalytics, AdminCategories, AdminIdeas, AdminReports, AdminUsers } from "./pages/admin/Admin";

function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />;
  if (user.role !== role) return <Navigate to={homePath(user)} replace />;
  return <>{children}</>;
}
function AppHome() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner />;
  return <Navigate to={user ? homePath(user) : "/login"} replace />;
}
const NotFound = () => (
  <div className="mx-auto max-w-md px-4 py-24 text-center"><h1 className="text-5xl font-extrabold">404</h1><p className="mt-3 text-slate-600">This page doesn't exist.</p><Link to="/" className="mt-6 inline-block"><Button>Back to home</Button></Link></div>
);

export default function App() {
  const guard = (role: Role) => <RequireRole role={role}><DashboardLayout /></RequireRole>;
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Landing />} /><Route path="/about" element={<About />} /><Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/explore" element={<Explore />} />
        <Route path="/ideas/:id" element={<div className="mx-auto max-w-6xl px-4 py-10 sm:px-6"><IdeaDetail /></div>} />
        <Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} />
      </Route>
      <Route path="/app" element={<AppHome />} />
      <Route path="/app/creator" element={guard("creator")}>
        <Route index element={<CreatorOverview />} /><Route path="submit" element={<SubmitIdea />} /><Route path="ideas" element={<MyIdeas />} /><Route path="ideas/:id" element={<IdeaDetail />} />
        <Route path="reports" element={<Reports />} /><Route path="collaboration" element={<Collaboration />} /><Route path="messages" element={<Messages />} /><Route path="profile" element={<Profile />} />
      </Route>
      <Route path="/app/entrepreneur" element={guard("entrepreneur")}>
        <Route index element={<EntrepreneurOverview />} /><Route path="discover" element={<Discover />} /><Route path="recommended" element={<Recommended />} /><Route path="saved" element={<Saved />} />
        <Route path="ideas/:id" element={<IdeaDetail />} /><Route path="collaboration" element={<Collaboration />} /><Route path="messages" element={<Messages />} /><Route path="profile" element={<Profile />} />
      </Route>
      <Route path="/app/admin" element={guard("admin")}>
        <Route index element={<AdminAnalytics />} /><Route path="users" element={<AdminUsers />} /><Route path="ideas" element={<AdminIdeas />} /><Route path="ideas/:id" element={<IdeaDetail />} />
        <Route path="reports" element={<AdminReports />} /><Route path="categories" element={<AdminCategories />} />
      </Route>
      <Route path="*" element={<PublicLayout />}><Route path="*" element={<NotFound />} /></Route>
    </Routes>
  );
}
