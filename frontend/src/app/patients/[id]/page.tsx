type Props = { params: Promise<{ id: string }> };

export default async function PatientDetailPage({ params }: Props) {
  const { id } = await params;
  return (
    <section>
      <h1>Patient</h1>
      <p>Placeholder for synthetic patient {id}.</p>
    </section>
  );
}
