import { useQueries, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';
import { client } from './client';
import type {
  RangeKey,
  MetricKey,
  RatingCode,
  RatingCohortMember,
  FlightUpdate,
} from './types';

export const queryKeys = {
  meta: ['meta'] as const,
  kpis: (range: RangeKey) => ['kpis', range] as const,
  ratingBars: (metric: MetricKey, range: RangeKey) =>
    ['ratingBars', metric, range] as const,
  rating: (code: RatingCode, range: RangeKey) => ['rating', code, range] as const,
  ratingCohort: (code: RatingCode) => ['ratingCohort', code] as const,
  ratingsCompleted: (range: RangeKey) => ['ratingsCompleted', range] as const,
  heatmap: (range: RangeKey) => ['heatmap', range] as const,
  clients: (range: RangeKey, rating?: RatingCode) =>
    ['clients', range, rating ?? null] as const,
  student: (id: string) => ['student', id] as const,
  instructors: ['instructors'] as const,
  instructor: (id: string) => ['instructor', id] as const,
  flights: (filter: object) => ['flights', filter] as const,
};

export const useMeta = () =>
  useQuery({ queryKey: queryKeys.meta, queryFn: client.getMeta });

export const useKpis = (range: RangeKey) =>
  useQuery({ queryKey: queryKeys.kpis(range), queryFn: () => client.getKpis(range) });

export const useRatingBars = (metric: MetricKey, range: RangeKey) =>
  useQuery({
    queryKey: queryKeys.ratingBars(metric, range),
    queryFn: () => client.getRatingBars(metric, range),
  });

export const useRating = (code: RatingCode | undefined, range: RangeKey) =>
  useQuery({
    queryKey: queryKeys.rating(code as RatingCode, range),
    queryFn: () => client.getRating(code as RatingCode, range),
    enabled: !!code,
  });

export const useRatingCohort = (code: RatingCode) =>
  useQuery({
    queryKey: queryKeys.ratingCohort(code),
    queryFn: () => client.getRatingCohort(code),
  });

export const useRatingCohorts = (
  codes: RatingCode[],
): Map<RatingCode, UseQueryResult<RatingCohortMember[]>> => {
  const queries = useQueries({
    queries: codes.map((code) => ({
      queryKey: queryKeys.ratingCohort(code),
      queryFn: () => client.getRatingCohort(code),
    })),
  });
  const map = new Map<RatingCode, UseQueryResult<RatingCohortMember[]>>();
  codes.forEach((code, i) => {
    map.set(code, queries[i] as UseQueryResult<RatingCohortMember[]>);
  });
  return map;
};

export const useRatingsCompleted = (range: RangeKey) =>
  useQuery({
    queryKey: queryKeys.ratingsCompleted(range),
    queryFn: () => client.getRatingsCompleted(range),
  });

export const useHeatmap = (range: RangeKey) =>
  useQuery({ queryKey: queryKeys.heatmap(range), queryFn: () => client.getHeatmap(range) });

export const useClients = (range: RangeKey, rating?: RatingCode) =>
  useQuery({
    queryKey: queryKeys.clients(range, rating),
    queryFn: () => client.getClients(range, rating),
  });

export const useStudent = (id: string | undefined) =>
  useQuery({
    queryKey: queryKeys.student(id ?? ''),
    queryFn: () => client.getStudent(id as string),
    enabled: !!id,
  });

export const useMyTraining = () =>
  useQuery({
    queryKey: ['me', 'training'],
    queryFn: () => client.getMyTraining(),
  });

export const useInstructors = () =>
  useQuery({ queryKey: queryKeys.instructors, queryFn: client.getInstructors });

export const useInstructor = (id: string | undefined) =>
  useQuery({
    queryKey: queryKeys.instructor(id ?? ''),
    queryFn: () => client.getInstructor(id as string),
    enabled: !!id,
  });

export const useFlights = (filter: {
  instructor?: string;
  client?: string;
  ground?: string;
  sort?: string;
}) =>
  useQuery({
    queryKey: queryKeys.flights(filter),
    queryFn: () => client.getFlights(filter),
  });

export const useUpdateFlight = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: FlightUpdate }) =>
      client.updateFlight(id, patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['flights'] });
      qc.invalidateQueries({ queryKey: ['student'] });
      qc.invalidateQueries({ queryKey: ['kpis'] });
      qc.invalidateQueries({ queryKey: ['ratingBars'] });
      qc.invalidateQueries({ queryKey: ['meta'] });
    },
  });
};

export const useImportFsp = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: client.importFsp,
    onSuccess: () => {
      void qc.invalidateQueries();
    },
  });
};

export const useRebuild = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ synthetic }: { synthetic: boolean }) => client.rebuild(synthetic),
    onSuccess: () => {
      void qc.invalidateQueries();
    },
  });
};

export const useUploadFsp = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (files: { flight_detail?: File; invoice_detail?: File }) =>
      client.uploadFsp(files),
    onSuccess: () => {
      void qc.invalidateQueries();
    },
  });
};

// --- user & access management ---------------------------------------------

export const useUsers = () =>
  useQuery({ queryKey: ['users'], queryFn: client.listUsers });

export const useStudentRecords = (enabled = true) =>
  useQuery({
    queryKey: ['users', 'student-records'],
    queryFn: client.listStudentRecords,
    enabled,
  });

export const useCreateUser = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string; role: string; student_id?: number | null }) =>
      client.createUser(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['users'] });
    },
  });
};

export const useUpdateUser = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      patch,
    }: {
      id: number;
      patch: {
        role?: string;
        is_active?: boolean;
        pages?: string[];
        new_password?: string;
        student_id?: number | null;
      };
    }) => client.updateUser(id, patch),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['users'] });
    },
  });
};

export const useChangePassword = () =>
  useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      client.changePassword(body),
  });
export const usePublicTransparency = () =>
  useQuery({ queryKey: ['publicTransparency'], queryFn: client.getPublicTransparency });
