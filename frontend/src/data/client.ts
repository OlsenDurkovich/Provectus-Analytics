import { authFetch } from '../auth/authFetch';
import type {
  Meta,
  Kpi,
  RatingBarPoint,
  RatingsCompletedRow,
  Heatmap,
  ClientRow,
  StudentDetail,
  InstructorSummary,
  InstructorDetail,
  FlightRow,
  FlightUpdate,
  RangeKey,
  MetricKey,
  RatingCode,
  Rating,
  RatingCohortMember,
  UserRow,
} from './types';

export class ApiError extends Error {
  status: number;
  body: string;
  constructor(status: number, body: string, message?: string) {
    super(message ?? `API error ${status}: ${body}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

function buildQuery(params?: Record<string, string | undefined>): string {
  if (!params) return '';
  const pairs: [string, string][] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) pairs.push([k, String(v)]);
  }
  if (pairs.length === 0) return '';
  return '?' + new URLSearchParams(pairs).toString();
}

async function get<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const res = await authFetch(path + buildQuery(params), {
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return (await res.json()) as T;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await authFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return (await res.json()) as T;
}

async function patchReq<T>(path: string, body: unknown): Promise<T> {
  const res = await authFetch(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return (await res.json()) as T;
}

// For endpoints that return 204 No Content (e.g. change-password).
async function postNoContent(path: string, body?: unknown): Promise<void> {
  const res = await authFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
}

export const client = {
  getMeta: () => get<Meta>('/api/meta'),
  getKpis: (range: RangeKey) => get<Kpi[]>('/api/kpis', { range }),
  getRatingBars: (metric: MetricKey, range: RangeKey) =>
    get<RatingBarPoint[]>('/api/ratings', { metric, range }),
  getRating: (code: RatingCode, range: RangeKey) =>
    get<Rating>(`/api/ratings/${code}`, { range }),
  getRatingCohort: (code: RatingCode) =>
    get<RatingCohortMember[]>(`/api/ratings/${code}/cohort`),
  getRatingsCompleted: (range: RangeKey) =>
    get<RatingsCompletedRow[]>('/api/ratings/completed', { range }),
  getHeatmap: (range: RangeKey) => get<Heatmap>('/api/heatmap', { range }),
  getClients: (range: RangeKey, rating?: RatingCode) =>
    get<ClientRow[]>('/api/students', { range, rating }),
  getStudent: (id: string) => get<StudentDetail>(`/api/students/${id}`),
  getInstructors: () => get<InstructorSummary[]>('/api/instructors'),
  getInstructor: (id: string) => get<InstructorDetail>(`/api/instructors/${id}`),
  getFlights: (filter: {
    instructor?: string;
    client?: string;
    ground?: string;
    sort?: string;
  }) => get<FlightRow[]>('/api/flights', filter),
  updateFlight: (id: string, body: FlightUpdate) =>
    patchReq<FlightRow>(`/api/flights/${id}`, body),
  importFsp: () => post<{ imported: unknown; built: unknown }>('/api/import-fsp'),
  rebuild: (synthetic = false) =>
    post<{ built: unknown }>(`/api/rebuild${synthetic ? '?synthetic=true' : ''}`),
  uploadFsp: async (files: { flight_detail?: File; invoice_detail?: File }) => {
    const form = new FormData();
    if (files.flight_detail) form.append('flight_detail', files.flight_detail);
    if (files.invoice_detail) form.append('invoice_detail', files.invoice_detail);
    const res = await authFetch('/api/upload/fsp', { method: 'POST', body: form });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    return (await res.json()) as { saved: unknown; built: unknown };
  },
  // User & access management (admin-only on the server).
  listUsers: () => get<UserRow[]>('/api/users'),
  createUser: (body: { email: string; password: string; role: string }) =>
    post<UserRow>('/api/users', body),
  updateUser: (id: number, body: { role?: string; is_active?: boolean }) =>
    patchReq<UserRow>(`/api/users/${id}`, body),
  changePassword: (body: { current_password: string; new_password: string }) =>
    postNoContent('/api/auth/change-password', body),
};

export type Client = typeof client;
