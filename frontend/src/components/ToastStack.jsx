import { XIcon } from "./icons.jsx";

export function ToastStack({ toasts, onDismiss }) {
  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div className={`toast toast-${toast.type}`} key={toast.id}>
          <span>{toast.message}</span>
          <button
            aria-label="Dismiss notification"
            className="toast-close"
            onClick={() => onDismiss(toast.id)}
            type="button"
          >
            <XIcon />
          </button>
        </div>
      ))}
    </div>
  );
}
