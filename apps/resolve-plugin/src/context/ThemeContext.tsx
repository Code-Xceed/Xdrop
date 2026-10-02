import React, { createContext, useContext } from 'react';

export interface ThemeContextValue {
  accentColor: string;
  glowColor: string;
}

const ThemeContext = createContext<ThemeContextValue>({
  accentColor: 'var(--accent-primary)',
  glowColor: 'rgba(0, 210, 255, 0.25)',
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <ThemeContext.Provider
      value={{
        accentColor: 'var(--accent-primary)',
        glowColor: 'rgba(0, 210, 255, 0.25)',
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextValue => {
  return useContext(ThemeContext);
};

