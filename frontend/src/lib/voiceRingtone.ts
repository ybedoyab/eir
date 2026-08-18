type Ringer = {
  start: () => void;
  stop: () => void;
};

export function createLocalRinger(ctx: AudioContext): Ringer {
  let timer: number | null = null;
  const nodes: OscillatorNode[] = [];

  function burst() {
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + 0.04);
    gain.gain.setValueAtTime(0.18, ctx.currentTime + 1.85);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 2);
    gain.connect(ctx.destination);
    for (const freq of [440, 480]) {
      const oscillator = ctx.createOscillator();
      oscillator.type = "sine";
      oscillator.frequency.value = freq;
      oscillator.connect(gain);
      oscillator.start();
      oscillator.stop(ctx.currentTime + 2.05);
      nodes.push(oscillator);
    }
  }

  return {
    start() {
      void ctx.resume();
      burst();
      timer = window.setInterval(burst, 6000);
    },
    stop() {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
      while (nodes.length) {
        const oscillator = nodes.pop();
        try {
          oscillator?.stop();
        } catch {
          // already stopped
        }
      }
    },
  };
}
