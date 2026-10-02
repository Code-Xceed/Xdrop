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
              padding: '11px 16px',
              backgroundColor: 'var(--bg-secondary)',
              border: '2px solid #000000',
              borderLeft: `5px solid ${
                isSuccess
                  ? 'var(--success)'
                  : isError
                  ? 'var(--danger)'
                  : 'var(--accent-primary)'
              }`,
              borderRadius: 'var(--radius-sm)',
              boxShadow: '3.5px 3.5px 0px #000000',
              fontSize: '12px',
              fontWeight: 700,
              color: '#ffffff',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {isSuccess && <CheckCircle2 size={16} color="var(--success)" />}
              {isError && <AlertCircle size={16} color="var(--danger)" />}
              {!isSuccess && !isError && <Info size={16} color="var(--accent-primary)" />}
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
              }}
            >
              <X size={12} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
