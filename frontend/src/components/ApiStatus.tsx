import { getHealth } from "@/services/api";

export async function ApiStatus() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const health = await getHealth();
    return (
      <p style={{ fontSize: "0.85rem", opacity: 0.75, margin: "0.25rem 0 0" }}>
        API {health.status} · {apiUrl}
      </p>
    );
  } catch {
    return (
      <p style={{ fontSize: "0.85rem", color: "#b91c1c", margin: "0.25rem 0 0" }}>
        API unreachable · {apiUrl}
      </p>
    );
  }
}
