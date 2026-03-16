import { Phone } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message?: string;
}

export function EmptyState({
  title = 'No calls yet',
  message = 'Your AI receptionist is ready! Calls will appear here as they come in.',
}: EmptyStateProps) {
  return (
    <div className="text-center py-16">
      <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border border-white/10 mb-6">
        <Phone className="w-8 h-8 text-gray-500" />
      </div>
      <h3 className="text-xl font-display font-semibold tracking-tight text-gray-400 mb-2">
        {title}
      </h3>
      <p className="text-gray-500 max-w-sm mx-auto">{message}</p>
    </div>
  );
}
