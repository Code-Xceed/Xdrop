import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[Xdrop ErrorBoundary] Caught runtime error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  private handleFullReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            padding: '20px',
            backgroundColor: 'var(--bg-void)',
            color: '#ffffff',
            userSelect: 'none',
          }}
        >
          <div
            className="panel"
            style={{
              maxWidth: '460px',
              width: '100%',
              padding: '24px',
              backgroundColor: 'var(--bg-secondary)',
              border: '2px solid var(--color-resolve)',
              boxShadow: '4px 4px 0px var(--color-resolve)',
              borderRadius: 'var(--radius-sm)',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                margin: '0 auto 14px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1.5px solid #000000',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-resolve)',
              }}
            >
              <AlertTriangle size={24} strokeWidth={2.5} />
            </div>

            <h3 style={{ fontSize: '15px', fontWeight: 900, marginBottom: '8px', color: '#ffffff' }}>
              Interface Interrupted
            </h3>

            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px', lineHeight: 1.4 }}>
              An unexpected render issue occurred. Your downloaded files and background service remain intact.
            </p>

            {this.state.error && (
              <div
                style={{
                  padding: '8px 10px',
                  backgroundColor: 'var(--bg-primary)',
                  border: '1px solid #000000',
                  borderRadius: 'var(--radius-xs)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '10.5px',
                  color: 'var(--color-resolve)',
                  textAlign: 'left',
                  maxHeight: '80px',
                  overflowY: 'auto',
                  marginBottom: '16px',
                  wordBreak: 'break-word',
                }}
              >
                {this.state.error.message || String(this.state.error)}
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
              <button
                onClick={this.handleReset}
                className="btn btn-secondary"
                style={{ padding: '6px 14px', fontSize: '11px' }}
              >
                <RotateCcw size={12} strokeWidth={2.5} />
                <span>Recover State</span>
              </button>

              <button
                onClick={this.handleFullReload}
                className="btn btn-primary"
                style={{ padding: '6px 14px', fontSize: '11px' }}
              >
                <span>Reload Panel</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
