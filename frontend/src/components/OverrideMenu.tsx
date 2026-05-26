import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';

type Props = {
  value: string;
  options: string[];
  onChange: (v: string) => void;
  disabled?: boolean;
};

export function OverrideMenu({ value, options, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  return (
    <div className="editable-cell" ref={ref}>
      <button
        type="button"
        className="editable-trigger"
        disabled={disabled}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((o) => !o);
        }}
      >
        <span className="editable-value">{value}</span>
        <Icon name="chevron" size={11} />
      </button>
      {open && (
        <div className="editable-pop">
          {options.map((o) => (
            <button
              type="button"
              key={o}
              className={'editable-opt ' + (o === value ? 'active' : '')}
              onClick={(e) => {
                e.stopPropagation();
                onChange(o);
                setOpen(false);
              }}
            >
              <span>{o}</span>
              {o === value && <Icon name="check" size={12} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
