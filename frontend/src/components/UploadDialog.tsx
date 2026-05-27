// Modal upload dialog — drops files from the user's machine into the FSP
// Exports/ folder via POST /api/upload/fsp. Replaces the sidebar "Import FSP"
// button on hosted deploys where there's no ~/Downloads scan target.

import { useRef, useState } from 'react';
import { useUploadFsp } from '../data/queries';

type Props = {
  open: boolean;
  onClose: () => void;
};

export function UploadDialog({ open, onClose }: Props) {
  const flightRef = useRef<HTMLInputElement>(null);
  const invoiceRef = useRef<HTMLInputElement>(null);
  const [flight, setFlight] = useState<File | null>(null);
  const [invoice, setInvoice] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const upload = useUploadFsp();

  if (!open) return null;

  const canSubmit = (flight || invoice) && !upload.isPending;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await upload.mutateAsync({
        flight_detail: flight ?? undefined,
        invoice_detail: invoice ?? undefined,
      });
      setFlight(null);
      setInvoice(null);
      if (flightRef.current) flightRef.current.value = '';
      if (invoiceRef.current) invoiceRef.current.value = '';
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    }
  }

  return (
    <div
      className="upload-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Upload FSP exports"
    >
      <form
        className="upload-card"
        onClick={(e) => e.stopPropagation()}
        onSubmit={onSubmit}
      >
        <div className="upload-head">
          <h3>Upload FSP exports</h3>
          <button
            type="button"
            className="btn btn-icon"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <p className="upload-sub">
          Drop in the newest Flight Detail and Invoice Detail XLSX exports from
          Flight Schedule Pro. Either is optional, but pick at least one.
        </p>

        <label className="upload-field">
          <span>Flight Detail XLSX</span>
          <input
            ref={flightRef}
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(e) => setFlight(e.target.files?.[0] ?? null)}
          />
          {flight && <span className="upload-filename">{flight.name}</span>}
        </label>

        <label className="upload-field">
          <span>Invoice Detail XLSX</span>
          <input
            ref={invoiceRef}
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(e) => setInvoice(e.target.files?.[0] ?? null)}
          />
          {invoice && <span className="upload-filename">{invoice.name}</span>}
        </label>

        {error && <div className="login-error" role="alert">{error}</div>}

        <div className="upload-actions">
          <button
            type="button"
            className="btn btn-outline"
            onClick={onClose}
            disabled={upload.isPending}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!canSubmit}
          >
            {upload.isPending ? 'Uploading…' : 'Upload + rebuild'}
          </button>
        </div>
      </form>
    </div>
  );
}
