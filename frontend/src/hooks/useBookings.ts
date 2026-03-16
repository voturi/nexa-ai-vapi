import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export function useBookings(limit = 20) {
  return useQuery({
    queryKey: ['bookings', limit],
    queryFn: () => api.getBookings(limit),
    refetchInterval: 30_000,
    staleTime: 30_000,
    retry: 3,
  });
}
