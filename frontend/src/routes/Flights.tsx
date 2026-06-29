import { useMemo, useState } from 'react';
import { Select } from '../components/helpers';
import { ClientsTable } from '../components/ClientsTable';
import { OverrideMenu } from '../components/OverrideMenu';
import { Skel } from '../components/primitives';
import { useClients, useFlights, useInstructors, useUpdateFlight } from '../data/queries';
import type { AcClass, BillingKind, FlightUpdate, GroundFlag } from '../data/types';

const BILLING_OPTS: BillingKind[] = ['Hobbs', 'Tach', 'Block', '—'];
const AC_CLASS_OPTS: AcClass[] = ['SE_BASIC', 'SE_COMPLEX', 'ME_BASIC', 'HP_COMPLEX'];
const GROUND_OPTS: GroundFlag[] = ['Flight (0)', 'Ground (1)'];
const FLIGHT_TYPES = [
  'Dual flight training',
  'Solo',
  'Check Ride',
  'Stage Check',
  'Ground',
  'Mock Checkride',
  'XC Solo',
];

type GroundFilter = 'All' | GroundFlag;

const GROUND_FILTER_OPTS: { value: GroundFilter; label: string }[] = [
  { value: 'All', label: 'All' },
  { value: 'Flight (0)', label: 'Flights only' },
  { value: 'Ground (1)', label: 'Ground only' },
];

export default function Flights() {
  const [instructor, setInstructor] = useState('');
  const [client, setClient] = useState('');
  const [ground, setGround] = useState<GroundFilter>('All');
  const [sort, setSort] = useState('-date');

  const instructorsQ = useInstructors();
  const instructorOpts = useMemo(
    () => [
      { value: '', label: 'All instructors' },
      ...(instructorsQ.data ?? []).map((i) => ({ value: i.id, label: i.name })),
    ],
    [instructorsQ.data],
  );

  const filter = useMemo(
    () => ({
      instructor: instructor || undefined,
      client: client.trim() || undefined,
      ground: ground === 'All' ? undefined : ground,
      sort,
    }),
    [instructor, client, ground, sort],
  );

  const flightsQ = useFlights(filter);
  const clientsQ = useClients('all');
  const updateMut = useUpdateFlight();
  const rows = flightsQ.data ?? [];

  function patchFlight(id: string, patch: FlightUpdate) {
    updateMut.mutate({ id, patch });
  }

  return (
    <div className="flights-tab">
      <div className="page-head">
        <div>
          <div className="eyebrow">Raw flight rows</div>
          <h1 className="page-title">Flights</h1>
          <div className="page-sub">
            Edit Type, Billing, AC class, or Ground? to override the auto-classification.
            Edits persist across weekly re-imports.
          </div>
        </div>
        <div className="page-head-tools">
          {updateMut.isPending && <span className="muted tiny">Saving…</span>}
        </div>
      </div>

      <div className="card table-card flights-card">
        <div className="flights-toolbar">
          <Select<string>
            label="Instructor"
            value={instructor}
            onChange={(v) => setInstructor(v ?? '')}
            options={instructorOpts}
            width={200}
          />
          <div className="select-wrap" style={{ minWidth: 220 }}>
            <div className="select-label">Client contains</div>
            <div className="select">
              <input
                className="flights-text-input"
                type="text"
                value={client}
                onChange={(e) => setClient(e.target.value)}
                placeholder="Filter by client name…"
              />
            </div>
          </div>
          <Select<GroundFilter>
            label="Ground/flight"
            value={ground}
            onChange={(v) => setGround((v as GroundFilter) ?? 'All')}
            options={GROUND_FILTER_OPTS}
            width={160}
          />
          <div className="spacer" />
          <div className="muted tiny">
            {rows.length.toLocaleString()} row{rows.length === 1 ? '' : 's'}
          </div>
        </div>

        {flightsQ.isLoading ? (
          <Skel h={240} />
        ) : (
          <div className="table-wrap" style={{ maxHeight: 'calc(100vh - 320px)' }}>
            <table className="dt flights-dt">
              <thead>
                <tr>
                  <th onClick={() => setSort(sort === '-date' ? 'date' : '-date')} style={{ cursor: 'pointer' }}>
                    Date <span className="sort-ind">{sort.endsWith('date') ? (sort.startsWith('-') ? '↓' : '↑') : '↕'}</span>
                  </th>
                  <th>Client</th>
                  <th>Instructor</th>
                  <th className="num">Hours</th>
                  <th className="num">Cost</th>
                  <th className="col-editable">Type</th>
                  <th className="col-editable">Billing</th>
                  <th className="col-editable">AC class</th>
                  <th className="col-editable">Ground?</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={9}>
                      <div className="empty">
                        <div className="empty-title">No flight rows match</div>
                        <div className="empty-sub">Try clearing the instructor or client filter.</div>
                      </div>
                    </td>
                  </tr>
                ) : (
                  rows.map((r) => (
                    <tr key={r.id}>
                      <td className="num muted">{r.date}</td>
                      <td>{r.client || <span className="muted tiny">—</span>}</td>
                      <td className="muted">
                        {r.instructor || <span className="muted tiny">—</span>}
                      </td>
                      <td className="num">{r.hours.toFixed(1)}</td>
                      <td className="num">
                        {r.cost ? `$${Math.round(r.cost).toLocaleString()}` : <span className="muted tiny">—</span>}
                      </td>
                      <td className="cell-editable">
                        <OverrideMenu
                          value={r.type}
                          options={FLIGHT_TYPES}
                          onChange={(v) =>
                            patchFlight(r.id, { field: 'reservation_type', value: v })
                          }
                        />
                      </td>
                      <td className="cell-editable">
                        <OverrideMenu
                          value={r.billing}
                          options={BILLING_OPTS}
                          onChange={(v) =>
                            patchFlight(r.id, {
                              field: 'billing_category',
                              value: v === '—' ? null : v,
                            })
                          }
                        />
                      </td>
                      <td className="cell-editable">
                        <OverrideMenu
                          value={r.acClass}
                          options={AC_CLASS_OPTS}
                          onChange={(v) =>
                            patchFlight(r.id, { field: 'aircraft_class', value: v })
                          }
                        />
                      </td>
                      <td className="cell-editable">
                        <OverrideMenu
                          value={r.ground}
                          options={GROUND_OPTS}
                          onChange={(v) =>
                            patchFlight(r.id, {
                              field: 'is_ground_lesson',
                              value: v === 'Ground (1)',
                            })
                          }
                        />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="section-head" style={{ marginTop: 20 }}>
        <h2 className="section-title">Client roster</h2>
        <div className="muted tiny">All active and recently completed clients</div>
      </div>
      {clientsQ.isLoading ? (
        <Skel h={300} />
      ) : clientsQ.data ? (
        <ClientsTable rows={clientsQ.data} />
      ) : null}
    </div>
  );
}
