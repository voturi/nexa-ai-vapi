import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Phone, Calendar, Clock, TrendingUp } from 'lucide-react';
import { StatCard } from '../components/dashboard/StatCard';
import { CallCard } from '../components/dashboard/CallCard';
import { TranscriptModal } from '../components/dashboard/TranscriptModal';
import { EmptyState } from '../components/ui/EmptyState';
import { StatCardSkeleton, CallCardSkeleton } from '../components/ui/Skeleton';
import { useStats } from '../hooks/useStats';
import { useCalls } from '../hooks/useCalls';
import { formatDate } from '../lib/utils';
import type { Call } from '../types';

export function DashboardPage() {
  const [activeCall, setActiveCall] = useState<Call | null>(null);
  const stats = useStats();
  const calls = useCalls(10);

  const isLoading = stats.isLoading || calls.isLoading;
  const hasError = stats.isError || calls.isError;

  const today = stats.data?.today;
  const week = stats.data?.this_week;

  return (
    <>
      {/* Header */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl sm:text-4xl font-display font-semibold tracking-[-0.02em] text-white mb-1">
            Dashboard
          </h1>
          <p className="text-gray-400 text-sm font-medium">
            AI Receptionist Overview &middot; {formatDate(new Date().toISOString())}
          </p>
        </div>
      </div>

      {/* Error state */}
      {hasError && !isLoading && (
        <div className="glass rounded-2xl p-8 mb-8 text-center">
          <h2 className="text-xl font-bold text-red-400 mb-2">
            Error Loading Data
          </h2>
          <p className="text-gray-300 mb-4">
            {stats.error?.message || calls.error?.message || 'Failed to load dashboard data.'}
          </p>
          <button
            onClick={() => {
              stats.refetch();
              calls.refetch();
            }}
            className="px-6 py-2 bg-cyan-500 hover:bg-cyan-600 rounded-xl text-white font-semibold transition-all"
          >
            Retry
          </button>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {isLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : today && week ? (
          <>
            <StatCard
              title="Calls Today"
              value={today.calls}
              icon={Phone}
              color="cyan"
            />
            <StatCard
              title="Bookings Today"
              value={today.bookings}
              icon={Calendar}
              color="purple"
            />
            <StatCard
              title="This Week"
              value={week.calls}
              icon={Clock}
              color="yellow"
            />
            <StatCard
              title="Conversion Rate"
              value={week.conversion_rate}
              suffix="%"
              icon={TrendingUp}
              color="green"
            />
          </>
        ) : null}
      </div>

      {/* Recent Calls */}
      <div className="glass rounded-2xl p-4 sm:p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl sm:text-2xl font-display font-semibold tracking-tight text-white">
            Recent Calls
          </h2>
          <div className="flex items-center gap-2 text-sm text-gray-400 font-medium">
            <Clock className="w-4 h-4" />
            <span className="hidden sm:inline">Auto-refreshing every 30s</span>
            <span className="sm:hidden">Live</span>
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            <CallCardSkeleton />
            <CallCardSkeleton />
            <CallCardSkeleton />
          </div>
        ) : calls.data && calls.data.length > 0 ? (
          <div className="space-y-3">
            {calls.data.map((call, index) => (
              <CallCard
                key={call.id}
                call={call}
                index={index}
                onView={setActiveCall}
              />
            ))}
          </div>
        ) : (
          <EmptyState />
        )}

        <Link
          to="/calls"
          className="block w-full mt-4 py-3 glass glass-hover rounded-xl text-gray-300 hover:text-white transition-all duration-200 text-sm font-bold text-center card-lift"
        >
          View All Calls &rarr;
        </Link>
      </div>

      {/* Bottom CTA */}
      {week && week.calls > 0 && (
        <div className="mt-6 bg-gradient-to-r from-cyan-500/10 to-purple-500/10 backdrop-blur-xl border border-cyan-500/20 rounded-2xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4 card-lift">
          <div>
            <h3 className="text-lg sm:text-xl font-display font-semibold tracking-tight text-white mb-1">
              Your AI is performing great!
            </h3>
            <p className="text-gray-300 text-sm font-medium">
              {week.conversion_rate}% booking rate &middot; {week.bookings} bookings this week
            </p>
          </div>
          <button className="px-6 py-3 bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl text-white font-bold hover:shadow-[0_0_30px_rgba(178,75,243,0.45)] transition-all duration-300 transform hover:-translate-y-0.5 whitespace-nowrap">
            View Analytics
          </button>
        </div>
      )}

      {/* Transcript Modal */}
      <TranscriptModal call={activeCall} onClose={() => setActiveCall(null)} />
    </>
  );
}
