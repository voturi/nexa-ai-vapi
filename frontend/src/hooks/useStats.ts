import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export function useStats() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getStats(),
    refetchInterval: 30_000,
    staleTime: 30_000,
    retry: 3,
  });
}
