import { motion } from 'framer-motion';
import {
  CheckCircle,
  XCircle,
  MessageSquare,
  Phone,
  User,
  Copy,
} from 'lucide-react';
import type { Call } from '../../types';
import { formatTimeAgo, formatDuration, copyToClipboard } from '../../lib/utils';
import { showToast } from '../ui/Toast';

interface CallCardProps {
  call: Call;
  index: number;
  onView: (call: Call) => void;
}

const statusConfig = {
  booked: {
    icon: CheckCircle,
    label: 'Booked',
    dotColor: 'bg-cyan-400',
    bgColor: 'bg-cyan-400/30',
    borderColor: 'border-cyan-400/50',
    textColor: 'text-cyan-100',
  },
  inquiry: {
    icon: MessageSquare,
    label: 'Inquiry',
    dotColor: 'bg-purple-400',
    bgColor: 'bg-purple-400/30',
    borderColor: 'border-purple-400/50',
    textColor: 'text-purple-100',
  },
  callback: {
    icon: Phone,
    label: 'Callback',
    dotColor: 'bg-yellow-400',
    bgColor: 'bg-yellow-400/30',
    borderColor: 'border-yellow-400/50',
    textColor: 'text-yellow-100',
  },
  ended: {
    icon: Phone,
    label: 'Completed',
    dotColor: 'bg-gray-400',
    bgColor: 'bg-gray-400/30',
    borderColor: 'border-gray-400/50',
    textColor: 'text-gray-100',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    dotColor: 'bg-red-400',
    bgColor: 'bg-red-400/30',
    borderColor: 'border-red-400/50',
    textColor: 'text-red-100',
  },
} as const;

/**
 * Derive a display outcome from the call data.
 * When outcome is null (common), infer from the summary text.
 */
function deriveOutcome(call: Call): keyof typeof statusConfig {
  // Use explicit outcome if it matches a known key
  if (call.outcome && call.outcome in statusConfig) {
    return call.outcome as keyof typeof statusConfig;
  }

  // Infer from summary when outcome is null/empty
  const summary = (call.summary || '').toLowerCase();
  if (
    summary.includes('book') ||
    summary.includes('scheduled') ||
    summary.includes('appointment')
  ) {
    return 'booked';
  }
  if (summary.includes('callback') || summary.includes('call back')) {
    return 'callback';
  }
  if (
    summary.includes('no interaction') ||
    summary.includes('ended immediately') ||
    summary.includes('silence')
  ) {
    return 'ended';
  }

  // Fall back to status field
  if (call.status === 'ended') return 'ended';

  return 'inquiry';
}

export function CallCard({ call, index, onView }: CallCardProps) {
  const outcome = deriveOutcome(call);
  const config = statusConfig[outcome];
  const StatusIcon = config.icon;

  const handleCopyPhone = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!call.caller_phone) return;
    const ok = await copyToClipboard(call.caller_phone);
    if (ok) showToast('Phone number copied');
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      whileHover={{ scale: 1.01 }}
      onClick={() => onView(call)}
      className="glass glass-hover rounded-xl p-4 cursor-pointer group transition-all duration-200"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div
          className={`w-2 h-2 rounded-full ${config.dotColor} shadow-[0_0_10px] ${config.dotColor}/60 flex-shrink-0`}
        />

        <span className="text-gray-400 text-sm font-semibold min-w-[90px]">
          {formatTimeAgo(call.started_at || call.created_at)}
        </span>

        <div className="w-10 h-10 bg-gradient-to-br from-cyan-500/20 to-purple-500/20 rounded-full flex items-center justify-center border border-white/10 flex-shrink-0">
          <User className="w-5 h-5 text-gray-200" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-white font-semibold truncate">
              {call.caller_name || call.caller_phone || 'Unknown'}
            </span>
            <button
              onClick={handleCopyPhone}
              className="p-1 rounded hover:bg-white/10 text-gray-500 hover:text-white transition-colors"
              title="Copy phone number"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
          </div>
          {call.duration_seconds != null && (
            <div className="text-gray-400 text-xs font-medium">
              {formatDuration(call.duration_seconds)}
            </div>
          )}
        </div>

        {call.status && (
          <div className="text-gray-300 text-sm font-medium capitalize hidden md:block">
            {call.status}
          </div>
        )}

        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1 px-2 py-1 ${config.bgColor} border ${config.borderColor} rounded-lg ${config.textColor} text-xs font-semibold`}
          >
            <StatusIcon className="w-3 h-3" />
            {config.label}
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onView(call);
            }}
            className="px-4 py-2 glass glass-hover rounded-lg text-gray-200 text-sm font-semibold transition-all opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
          >
            View
          </button>
        </div>
      </div>

      {call.transcript && (
        <div className="mt-3 pt-3 border-t border-white/5">
          <p className="text-gray-400 text-sm line-clamp-2">
            {call.transcript.split('\n')[0]}
          </p>
        </div>
      )}
    </motion.div>
  );
}
