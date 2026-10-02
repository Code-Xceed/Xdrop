import React from 'react';
import { ArrowDownToLine, ListTree, FolderArchive, Settings } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export type TabId = 'import' | 'queue' | 'library' | 'settings';

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
  const { accentColor } = useTheme();

  const tabs: Array<{ id: TabId; label: string; icon: React.ReactNode; badge?: number }> = [
    {
      id: 'import',
      label: 'Import',
      icon: <ArrowDownToLine size={14} strokeWidth={2.5} />,
    },
    {
      id: 'queue',
      label: 'Queue',
      icon: <ListTree size={14} strokeWidth={2.5} />,
      badge: activeQueueCount > 0 ? activeQueueCount : undefined,
    },
    {
      id: 'library',
      label: 'Library',
      icon: <FolderArchive size={14} strokeWidth={2.5} />,
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: <Settings size={14} strokeWidth={2.5} />,
    },
  ];

  return (
    <nav
      style={{
        display: 'flex',
        alignItems: 'stretch',
        backgroundColor: 'var(--bg-void)',
        borderBottom: '1.5px solid #000000',
        padding: '0 8px',
        gap: '4px',
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
              padding: '8px 4px',
              backgroundColor: isActive ? 'var(--bg-secondary)' : 'transparent',
              border: isActive ? '1.5px solid #000000' : '1.5px solid transparent',
              borderBottom: 'none',
              borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
              color: isActive ? '#ffffff' : 'var(--text-muted)',
              fontWeight: 800,
              fontSize: '11px',
              letterSpacing: '0.02em',
              cursor: 'pointer',
              transition: 'all 0.1s ease',
              marginBottom: isActive ? '-1.5px' : '0',
              whiteSpace: 'nowrap',
            }}
          >
            <span style={{ color: isActive ? accentColor : 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>
              {tab.icon}
            </span>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{tab.label}</span>

            {tab.badge !== undefined && (
              <span
                style={{
                  backgroundColor: accentColor,
                  color: '#000000',
                  fontSize: '9px',
                  fontWeight: 900,
                  borderRadius: '2px',
                  padding: '1px 4px',
                  lineHeight: 1.1,
                  border: '1px solid #000000',
                }}
              >
                {tab.badge}
              </span>
            )}

            {/* Neo active indicator line */}
            {isActive && (
              <span
                style={{
                  position: 'absolute',
                  top: '-1.5px',
                  left: '-1.5px',
                  right: '-1.5px',
                  height: '2.5px',
                  backgroundColor: accentColor,
                }}
              />
            )}
          </button>
        );
      })}
    </nav>
  );
};
