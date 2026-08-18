import Link from "next/link";

import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { listPatients } from "@/services/api";

export default async function AdminPatientsPage() {
  const patients = await listPatients();
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Operations" title="Patient directory" />
      <div className="grid gap-4 sm:grid-cols-2">
        {patients.map((patient) => (
          <Link key={patient.id} href={`/clinician/patients/${patient.id}`}>
            <Card>
              <CardHeader title={patient.name} description={patient.id} />
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
