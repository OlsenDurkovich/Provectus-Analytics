// Mirror of src/provectus_analytics/api/schemas.py.
// Any change here MUST be reflected there.

export type RatingCode = 'PPL' | 'IFR' | 'COM' | 'AMEL' | 'CFI' | 'CFII' | 'MEI';
export type RangeKey = '30d' | '90d' | '6mo' | '12mo' | 'ytd' | 'all';
export type MetricKey = 'hours' | 'cost' | 'days';
export type ThemeKey = 'dark' | 'light';
export type TabKey = 'overview' | 'rating' | 'student' | 'instructor' | 'flights';
export type FlightStatus = 'Active' | 'On checkride' | 'Completed';
export type BillingKind = 'Hobbs' | 'Tach' | 'Block' | '—';
export type AcClass = 'SE_BASIC' | 'SE_COMPLEX' | 'ME_BASIC' | 'HP_COMPLEX';
export type GroundFlag = 'Flight (0)' | 'Ground (1)';
export type OverridableField =
  | 'is_ground_lesson'
  | 'billing_category'
  | 'aircraft_class'
  | 'reservation_type';

export interface Kpi {
  key: string;
  label: string;
  value: string;
  sub: string;
  delta: number;
  positive: boolean;
  spark: number[];
  color: string;
}

export interface Rating {
  code: RatingCode;
  name: string;
  n: number;
  medianHrs: number;
  p25Hrs: number;
  p75Hrs: number;
  medianCost: number;
  p25Cost: number;
  p75Cost: number;
  medianDays: number;
  p25Days: number;
  p75Days: number;
  lowSample?: boolean;
}

export interface RatingCohortMember {
  studentId: string;
  name: string;
  hours: number;
  cost: number;
  days: number;
}

export interface RatingBarPoint {
  code: RatingCode;
  name: string;
  n: number;
  median: number;
  p25: number;
  p75: number;
}

export interface RatingsCompletedRow {
  rating: RatingCode;
  count: number;
}

export interface Heatmap {
  rows: number[][];
  buckets: string[];
}

export interface ClientRow {
  id: string;
  name: string;
  rating: RatingCode;
  progressPct: number;
  hoursToDate: number;
  daysEnrolled: number;
  status: FlightStatus;
  // Phase 11.5: restored from Dash design.
  costToDate: number;
  instructor: string;
  sparkline: number[]; // 8 trailing monthly hour totals, oldest first
}

export interface StudentTimelineMilestone {
  name: string;
  date: string;
}

export interface StudentTimelinePoint {
  rating: RatingCode;
  start: string;
  end: string | null;
  milestones: StudentTimelineMilestone[];
}

export interface StudentPerRating {
  rating: RatingCode;
  name: string;
  n: number;
  hours?: number | null;
  cost?: number | null;
  days?: number | null;
  medianHrs?: number | null;
  medianCost?: number | null;
  medianDays?: number | null;
  lowSample?: boolean;
}

export interface StudentDetail {
  id: string;
  name: string;
  timeline: StudentTimelinePoint[];
  perRating: StudentPerRating[];
}

export interface InstructorSummary {
  id: string;
  name: string;
  hours: number;
  students: number;
  passRate: number;
}

export interface InstructorPerRating {
  rating: RatingCode;
  n: number;
  avgHrs: number;
  avgCost: number;
  avgDays: number;
  studentIds: string[];
}

export interface InstructorDetail {
  id: string;
  name: string;
  students: ClientRow[];
  perRating: InstructorPerRating[];
}

export interface FlightRow {
  id: string;
  date: string;
  client: string;
  instructor: string;
  type: string;
  billing: BillingKind;
  acClass: AcClass;
  ground: GroundFlag;
  hours: number;
  cost: number;
}

export interface FlightUpdate {
  field: OverridableField;
  value: string | boolean | null;
}

export interface DataState {
  flights: number;
  invoices: number;
  students: number;
  surveys: number;
  overrides: number;
}

export interface Meta {
  mode: 'real' | 'synthetic';
  liveClientCount: number;
  dataState: DataState;
}

export type UserRole = 'admin' | 'instructor' | 'viewer' | 'student';

// A training record an admin can link a student account to (mirror of the
// users router StudentRecord).
export interface StudentRecord {
  student_id: number;
  name: string;
  email: string | null;
}

// An instructor name an admin can link an instructor account to.
export interface InstructorRecord {
  name: string;
  students: number;
}

// Cost-free roster served to an instructor account (/api/me/students).
export interface MyStudentRow {
  id: string;
  name: string;
  rating: RatingCode;
  progressPct: number;
  hoursToDate: number;
  daysEnrolled: number;
  status: FlightStatus;
}
export interface MyInstructorPerRating {
  rating: RatingCode;
  n: number;
  avgHrs: number;
  avgDays: number;
  studentIds: string[];
}
export interface MyStudentsView {
  instructor_name: string;
  students: MyStudentRow[];
  perRating: MyInstructorPerRating[];
}

// Toggleable dashboard pages (mirror of auth/users.py ALL_PAGES).
export type PageKey = 'overview' | 'ratings' | 'students' | 'instructors';
export const ALL_PAGES: { key: PageKey; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'ratings', label: 'Rating detail' },
  { key: 'students', label: 'Student' },
  { key: 'instructors', label: 'Instructor' },
];

export interface UserRow {
  user_id: number;
  email: string;
  role: string;
  is_active: boolean;
  pages: string[];
  is_admin: boolean;
  student_id?: number | null;
  instructor_name?: string | null;
  display_name?: string | null;
  phone?: string | null;
}

export interface PublicRatingNorm {
  code: string;
  label: string;
  n: number;
  low_sample: boolean;
  median_cost: number;
  p25_cost: number;
  p75_cost: number;
  median_hours: number;
  p25_hours: number;
  p75_hours: number;
  median_days: number;
}

export interface PublicTransparency {
  data_mode: 'real' | 'synthetic';
  ratings: PublicRatingNorm[];
}
