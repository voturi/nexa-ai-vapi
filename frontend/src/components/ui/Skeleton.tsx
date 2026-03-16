interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-white/5 ${className}`}
    />
  );
}

export function StatCardSkeleton() {
  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="w-11 h-11 rounded-xl" />
        <Skeleton className="w-12 h-5 rounded-lg" />
      </div>
      <Skeleton className="w-20 h-12 mb-2" />
      <Skeleton className="w-28 h-4" />
    </div>
  );
}

export function CallCardSkeleton() {
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center gap-4">
        <Skeleton className="w-2 h-2 rounded-full" />
        <Skeleton className="w-16 h-4" />
        <Skeleton className="w-10 h-10 rounded-full" />
        <div className="flex-1">
          <Skeleton className="w-32 h-5 mb-1" />
          <Skeleton className="w-16 h-3" />
        </div>
        <Skeleton className="w-16 h-6 rounded-lg" />
      </div>
    </div>
  );
}
