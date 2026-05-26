type Props = {
  open: boolean;
  onClose: () => void;
};

export function NotificationsPopover({ open, onClose }: Props) {
  if (!open) return null;
  return (
    <div className="notif-pop">
      <div className="notif-head">
        <h4>Notifications</h4>
      </div>
      <div className="notif-list">
        <div className="empty" style={{ padding: '24px 12px' }}>
          <div className="empty-title">All caught up</div>
          <div className="empty-sub">
            Notifications will surface here when wired to a real feed.
          </div>
        </div>
      </div>
      <div style={{ padding: '8px 12px', borderTop: '1px solid var(--border)' }}>
        <button type="button" className="btn btn-outline" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
