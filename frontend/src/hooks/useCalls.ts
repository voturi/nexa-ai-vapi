import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export function useCalls(limit = 20) {
  return useQuery({
    queryKey: ['calls', limit],
    queryFn: () => api.getCalls(limit),
    refetchInterval: 30_000,
    staleTime: 30_000,
    retry: 3,
  });
}
