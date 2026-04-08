// The main dashboard lives at the root route (/)
// This file redirects /dashboard → / for any direct navigation
import { redirect } from "next/navigation";

export default function DashboardRedirect() {
  redirect("/");
}
