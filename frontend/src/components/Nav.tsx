import Link from "next/link";

const links = [
  { href: "/", label: "Home" },
  { href: "/patients", label: "Patients" },
  { href: "/recovery", label: "Recovery" },
  { href: "/agents", label: "Agents" },
  { href: "/observability", label: "Observability" },
];

export function Nav() {
  return (
    <nav
      style={{
        display: "flex",
        gap: "1rem",
        padding: "0.75rem 1.5rem",
        borderBottom: "1px solid #ddd",
      }}
    >
      {links.map((link) => (
        <Link key={link.href} href={link.href}>
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
