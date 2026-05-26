import { useEffect, useRef, useState } from 'react';
import { Icon } from '../Icon';

type Opt<T extends string> = { value: T; label: string };

type Props<T extends string> = {
  value: T | null;
  onChange: (v: T | null) => void;
  options: Array<T | Opt<T>>;
  label?: string;
  width?: number;
  allowClear?: boolean;
};

export function Select<T extends string>({
  value,
  onChange,
  options,
  label,
  width = 220,
  allowClear = false,
}: Props<T>) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const opts: Opt<T>[] = options.map((o) =>
    typeof o === 'string' ? { value: o, label: o } : o
  );
  const current = opts.find((o) => o.value === value);

  return (
    <div className="select-wrap" style={{ minWidth: width }}>
      {label && <div className="select-label">{label}</div>}
      <div className="select" ref={ref}>
        <button
          type="button"
          className="select-trigger"
          onClick={() => setOpen((o) => !o)}
        >
          <span className="select-trigger-value">{current?.label ?? '—'}</span>
          <span className="select-trigger-tools">
            {allowClear && value && (
              <span
                className="select-clear"
                onClick={(e) => {
                  e.stopPropagation();
                  onChange(null);
                }}
                title="Clear"
              >
                <Icon name="close" size={11} />
              </span>
            )}
            <Icon name="chevron" size={12} />
          </span>
        </button>
        {open && (
          <div className="select-pop">
            {opts.map((o) => (
              <button
                key={o.value}
                type="button"
                className={`select-opt ${o.value === value ? 'active' : ''}`}
                onClick={() => {
                  onChange(o.value);
                  setOpen(false);
                }}
              >
                <span>{o.label}</span>
                {o.value === value && <Icon name="check" size={13} />}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
