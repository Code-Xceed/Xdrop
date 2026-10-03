import React from 'react';
import { ArrowDownToLine, ListTree, Settings } from 'lucide-react';

export type TabId = 'import' | 'queue' | 'settings';

interface NavigationProps {
  currentTab: TabId;
  onSelectTab: (tab: TabId) => void;
  activeQueueCount: number;
}

export const Navigation: React.FC<NavigationProps> = ({
  currentTab,
  onSelectTab,
  activeQueueCount,
}) => {
  const tabs: Array<{ id: TabId; label: string; icon: React.ReactNode; badge?: number }> = [
    {
      id: 'import',
      label: 'Import',
      icon: <ArrowDownToLine size={13} strokeWidth={2} />,
    },
    {
      id: 'queue',
      label: 'Queue',
      icon: <ListTree size={13} strokeWidth={2} />,
      badge: activeQueueCount > 0 ? activeQueueCount : undefined,
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: <Settings size={13} strokeWidth={2} />,
    },
  ];

  return (
    <nav
      style={{
        display: 'flex',
        alignItems: 'stretch',
        backgroundColor: 'var(--bg-void)',
        borderBottom: '1px solid var(--border-default)',
        padding: '0 8px',
        gap: '2px',
        userSelect: 'none',
        width: '100%',
      }}
    >
      {tabs.map((tab) => {
        const isActive = currentTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onSelectTab(tab.id)}
            style={{
              position: 'relative',
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '7px 4px',
              backgroundColor: isActive ? 'var(--bg-secondary)' : 'transparent',
              border: isActive ? '1px solid var(--border-default)' : '1px solid transparent',
              borderBottom: 'none',
              borderRadius: 'var(--radius-xs) var(--radius-xs) 0 0',
              color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
              fontWeight: isActive ? 600 : 500,
              fontSize: '11px',
              letterSpacing: '0.01em',
              cursor: 'pointer',
              transition: 'all 0.12s ease',
              marginBottom: isActive ? '-1px' : '0',
              whiteSpace: 'nowrap',
            }}
          >
            <span style={{ color: isActive ? '#ffffff' : 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>
              {tab.icon}
            </span>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{tab.label}</span>

            {tab.badge !== undefined && (
              <span
                style={{
                  backgroundColor: 'rgba(255, 255, 255, 0.15)',
                  color: '#ffffff',
                  fontSize: '9px',
                  fontWeight: 600,
                  borderRadius: '3px',
                  padding: '1px 5px',
                  lineHeight: 1.1,
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                }}
              >
                {tab.badge}
              </span>
            )}

            {/* Minimalist active indicator line */}
            {isActive && (
              <span
                style={{
                  position: 'absolute',
                  top: '-1px',
                  left: '-1px',
                  right: '-1px',
                  height: '2px',
                  backgroundColor: 'var(--accent-primary)',
                  borderRadius: '2px 2px 0 0',
                }}
              />
            )}
          </button>
        );
      })}
    </nav>
  );
};
