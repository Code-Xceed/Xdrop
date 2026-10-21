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
      icon: <ArrowDownToLine size={12} strokeWidth={2.2} />,
    },
    {
      id: 'queue',
      label: 'Queue',
      icon: <ListTree size={12} strokeWidth={2.2} />,
      badge: activeQueueCount > 0 ? activeQueueCount : undefined,
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: <Settings size={12} strokeWidth={2.2} />,
    },
  ];

  return (
    <nav
      style={{
        padding: '4px 10px',
        backgroundColor: 'var(--bg-void)',
        userSelect: 'none',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'var(--bg-primary)',
          borderRadius: '6px',
          border: '1px solid var(--border-default)',
          padding: '2px',
          gap: '2px',
        }}
      >
        {tabs.map((tab) => {
          const isActive = currentTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onSelectTab(tab.id)}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '5px',
                height: '25px',
                padding: '0 8px',
                borderRadius: '4px',
                backgroundColor: isActive ? 'var(--bg-elevated)' : 'transparent',
                border: isActive ? '1px solid var(--border-strong)' : '1px solid transparent',
                color: isActive ? '#ffffff' : 'var(--text-muted)',
                fontWeight: isActive ? 600 : 500,
                fontSize: '11px',
                letterSpacing: '0.01em',
                cursor: 'pointer',
                boxShadow: isActive ? '0 1px 2px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08)' : 'none',
                transition: 'all 120ms var(--ease-out)',
                whiteSpace: 'nowrap',
                outline: 'none',
              }}
            >
              <span
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  color: isActive ? '#ffffff' : 'var(--text-muted)',
                  transition: 'color 120ms var(--ease-out)',
                }}
              >
                {tab.icon}
              </span>
              <span>{tab.label}</span>

              {tab.badge !== undefined && (
                <span
                  style={{
                    backgroundColor: isActive ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                    color: '#ffffff',
                    fontSize: '9px',
                    fontWeight: 600,
                    fontFamily: 'var(--font-mono)',
                    borderRadius: '10px',
                    padding: '0 5px',
                    height: '14px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginLeft: '2px',
                  }}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
};
