export function BackgroundOrbs() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      <div className="absolute top-1/4 left-1/4 w-[520px] h-[520px] bg-cyan-300/10 rounded-full blur-3xl animate-orb-drift" />
      <div
        className="absolute bottom-1/4 right-1/4 w-[520px] h-[520px] bg-purple-300/10 rounded-full blur-3xl animate-orb-drift-slow"
        style={{ animationDelay: '2s' }}
      />
    </div>
  );
}
