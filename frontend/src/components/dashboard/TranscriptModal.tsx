import { useMemo, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { Call } from '../../types';
import { formatTimeAgo } from '../../lib/utils';

interface TranscriptModalProps {
  call: Call | null;
  onClose: () => void;
}

export function TranscriptModal({ call, onClose }: TranscriptModalProps) {
  const transcriptLines = useMemo(() => {
    if (!call?.transcript) return [];
    return call.transcript.split('\n').filter(Boolean);
  }, [call]);

  useEffect(() => {
    if (!call) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [call, onClose]);

  return (
    <AnimatePresence>
      {call && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
        >
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            className="relative w-full max-w-3xl overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-cyan-500/10 via-white/5 to-purple-500/10 p-6 shadow-[0_45px_140px_rgba(0,0,0,0.65)]"
          >
            {/* Decorative blurs */}
            <div className="pointer-events-none absolute inset-0 opacity-70">
              <div className="absolute -top-24 right-0 h-56 w-56 rounded-full bg-cyan-300/15 blur-3xl" />
              <div className="absolute -bottom-24 left-10 h-56 w-56 rounded-full bg-purple-300/15 blur-3xl" />
            </div>

            {/* Header */}
            <div className="relative flex items-start justify-between gap-6">
              <div>
                <div className="text-sm text-gray-400 font-semibold uppercase tracking-[0.3em]">
                  Call Transcript
                </div>
                <div className="text-2xl font-display font-semibold tracking-tight text-white mt-2">
                  {call.caller_phone}
                </div>
                <div className="text-gray-400 text-sm mt-1">
                  {formatTimeAgo(call.started_at)}
                </div>
              </div>
              <button
                onClick={onClose}
                className="px-4 py-2 glass glass-hover rounded-xl text-white/80 text-sm font-semibold transition-all"
              >
                Close
              </button>
              <div className="pointer-events-none absolute left-0 right-24 top-8 h-px overflow-hidden">
                <div className="h-px w-[200%] bg-gradient-to-r from-transparent via-white/40 to-transparent animate-sheen-slide" />
              </div>
            </div>

            {/* Transcript */}
            <div className="mt-6 relative">
              <div className="rounded-2xl border border-white/10 bg-black/30 p-5 max-h-[55vh] overflow-y-auto">
                {transcriptLines.length > 0 ? (
                  <div className="space-y-3">
                    {transcriptLines.map((line, idx) => (
                      <div key={`${call.id}-${idx}`} className="flex gap-3">
                        <div className="text-xs font-bold uppercase tracking-widest text-cyan-300 min-w-[70px]">
                          {line.startsWith('AI:') ? 'AI' : 'Customer'}
                        </div>
                        <div className="text-gray-200 text-sm leading-relaxed">
                          {line.replace(/^AI:\s?/, '').replace(/^Customer:\s?/, '')}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-400 text-sm text-center py-8">
                    No transcript available for this call yet.
                  </div>
                )}
              </div>
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 rounded-b-2xl bg-gradient-to-t from-black/50 to-transparent" />
            </div>

            {/* Footer */}
            <div className="mt-5 flex items-center justify-between text-xs text-gray-400">
              <div>Auto-saved transcript</div>
              <div className="text-gray-500">Press Esc to close</div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
