import { useState } from 'react';
import { Phone, Clock } from 'lucide-react';
import { CallCard } from '../components/dashboard/CallCard';
import { TranscriptModal } from '../components/dashboard/TranscriptModal';
import { EmptyState } from '../components/ui/EmptyState';
import { CallCardSkeleton } from '../components/ui/Skeleton';
import { useCalls } from '../hooks/useCalls';
import type { Call } from '../types';

export function CallsPage() {
  const [activeCall, setActiveCall] = useState<Call | null>(null);
  const { data: calls, isLoading, isError, error, refetch } = useCalls(50);

  return (
    <>
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl sm:text-4xl font-display font-semibold tracking-[-0.02em] text-white mb-1">
            Calls
          </h1>
          <p className="text-gray-400 text-sm font-medium">
            All incoming call records
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-400 font-medium">
          <Clock className="w-4 h-4" />
          <span className="hidden sm:inline">Auto-refreshing</span>
        </div>
      </div>

      {/* Error */}
      {isError && (
        <div className="glass rounded-2xl p-8 mb-6 text-center">
          <h2 className="text-xl font-bold text-red-400 mb-2">Error</h2>
          <p className="text-gray-300 mb-4">{error?.message}</p>
          <button
            onClick={() => refetch()}
            className="px-6 py-2 bg-cyan-500 hover:bg-cyan-600 rounded-xl text-white font-semibold transition-all"
          >
            Retry
          </button>
        </div>
      )}

      {/* Call List */}
      <div className="glass rounded-2xl p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-6">
          <Phone className="w-5 h-5 text-cyan-400" />
          <h2 className="text-xl font-display font-semibold text-white">
            {calls ? `${calls.length} calls` : 'Loading...'}
          </h2>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <CallCardSkeleton key={i} />
            ))}
          </div>
        ) : calls && calls.length > 0 ? (
          <div className="space-y-3">
            {calls.map((call, index) => (
              <CallCard
                key={call.id}
                call={call}
                index={index}
                onView={setActiveCall}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No calls recorded"
            message="When customers call your AI receptionist, their calls will appear here."
          />
        )}
      </div>

      <TranscriptModal call={activeCall} onClose={() => setActiveCall(null)} />
    </>
  );
}
