import type { IconName } from "@/components/ui/Icon";
import { APP_ROUTES } from "@/config/app";
import type { DemoRole } from "@/lib/auth";

export interface NavigationItem {
  href: string;
  label: string;
  icon: IconName;
}

export interface RoleNavigation {
  home: string;
  label: string;
  navigation: NavigationItem[];
  shell: {
    columns: string;
    content: string;
    density: string;
    navPadding: string;
    navRow: string;
  };
}

export const PUBLIC_NAVIGATION: NavigationItem[] = [
  { href: APP_ROUTES.home, label: "Home", icon: "home" },
  { href: APP_ROUTES.demo, label: "Demo", icon: "fleet" },
  { href: APP_ROUTES.patients, label: "Patients", icon: "patients" },
  { href: APP_ROUTES.recovery, label: "Recovery", icon: "recovery" },
  { href: APP_ROUTES.agents, label: "Agents", icon: "overview" },
  { href: APP_ROUTES.observability, label: "Observability", icon: "observe" },
  { href: APP_ROUTES.voicePreview, label: "Voice", icon: "voice" },
];

export const ROLE_NAVIGATION: Record<DemoRole, RoleNavigation> = {
  PATIENT: {
    home: APP_ROUTES.patient.home,
    label: "Patient",
    navigation: [
      { href: APP_ROUTES.patient.home, label: "Home", icon: "home" },
      { href: APP_ROUTES.patient.appointments, label: "Appointments", icon: "schedule" },
      { href: APP_ROUTES.patient.recovery, label: "Recovery", icon: "recovery" },
      { href: APP_ROUTES.patient.assistant, label: "Ask EIR", icon: "assistant" },
    ],
    shell: {
      columns: "lg:grid-cols-[272px_minmax(0,1fr)]",
      content: "gap-14 px-5 py-10 sm:px-10 sm:py-12 lg:mx-auto lg:max-w-[1100px] lg:px-14",
      density: "text-[0.9375rem]",
      navPadding: "px-5 py-6",
      navRow: "min-h-12 px-3",
    },
  },
  CLINICIAN: {
    home: APP_ROUTES.clinician.home,
    label: "Clinician",
    navigation: [
      { href: APP_ROUTES.clinician.home, label: "Today", icon: "today" },
      { href: APP_ROUTES.clinician.schedule, label: "Schedule", icon: "schedule" },
      { href: APP_ROUTES.clinician.reviews, label: "Reviews", icon: "reviews" },
      { href: APP_ROUTES.clinician.patients, label: "Patients", icon: "patients" },
    ],
    shell: {
      columns: "lg:grid-cols-[244px_minmax(0,1fr)]",
      content: "gap-7 px-5 py-7 sm:px-8",
      density: "text-[14.5px]",
      navPadding: "px-4 py-5",
      navRow: "min-h-11 px-2.5",
    },
  },
  OPERATIONS_ADMIN: {
    home: APP_ROUTES.admin.home,
    label: "Operations",
    navigation: [
      { href: APP_ROUTES.admin.home, label: "Overview", icon: "overview" },
      { href: APP_ROUTES.admin.fleet, label: "Fleet", icon: "fleet" },
      { href: APP_ROUTES.admin.observability, label: "Observability", icon: "observe" },
      { href: APP_ROUTES.admin.appointments, label: "Appointments", icon: "schedule" },
      { href: APP_ROUTES.admin.patients, label: "Patients", icon: "patients" },
      { href: APP_ROUTES.admin.inventory, label: "Inventory", icon: "inventory" },
    ],
    shell: {
      columns: "lg:grid-cols-[224px_minmax(0,1fr)]",
      content: "gap-6 px-5 py-6 sm:px-7",
      density: "text-[0.875rem]",
      navPadding: "px-3.5 py-4.5",
      navRow: "min-h-11 px-2.5",
    },
  },
};

const ROOT_ROLE_ROUTES = new Set<string>([
  APP_ROUTES.patient.home,
  APP_ROUTES.clinician.home,
  APP_ROUTES.admin.home,
]);

export function isNavigationItemActive(pathname: string, href: string): boolean {
  const isRootRoute = href === APP_ROUTES.home || ROOT_ROLE_ROUTES.has(href);
  return isRootRoute ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}
