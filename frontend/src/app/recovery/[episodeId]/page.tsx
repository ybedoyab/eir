type Props = { params: Promise<{ episodeId: string }> };

export default async function RecoveryEpisodePage({ params }: Props) {
  const { episodeId } = await params;
  return (
    <section>
      <h1>Recovery episode</h1>
      <p>Placeholder for episode {episodeId}.</p>
    </section>
  );
}
