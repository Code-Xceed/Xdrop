import React from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  text: string;
  type: 'success' | 'error' | 'info';
}

interface ToastContainerProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: '12px',
      right: '12px',
      left: '12px',
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
      zIndex: 9999,
      maxWidth: '360px',
      marginLeft: 'auto',
      pointerEvents: 'none',
    }}>
      {toasts.map((toast) => {
        const isSuccess = toast.type === 'success';
        const isError = toast.type === 'error';

        return (
          <div
            key={toast.id}
            style={{
              pointerEvents: 'auto',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '10px',
              padding: '10px 14px',
              backgroundColor: 'var(--bg-elevated)',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--radius-sm)',
              boxShadow: 'var(--shadow-md)',
              fontSize: '11.5px',
              fontWeight: 500,
              color: 'var(--text-primary)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {isSuccess && <CheckCircle2 size={15} color="var(--success)" strokeWidth={2} />}
              {isError && <AlertCircle size={15} color="var(--danger)" strokeWidth={2} />}
              {!isSuccess && !isError && <Info size={15} color="var(--text-secondary)" strokeWidth={2} />}
              <span>{typeof toast.text === 'string' ? toast.text : String(toast.text || '')}</span>
            </div>

            <button
              onClick={() => onDismiss(toast.id)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '2px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <X size={13} strokeWidth={2} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
